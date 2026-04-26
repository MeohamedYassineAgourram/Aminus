import os
from typing import Any, Dict

from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from backend.services.mistral_agent import reconcile_with_erp
from backend.services.persistence import store_invoice
from backend.services.security_check import run_security_check

# Load backend/.env for local dev (gitignored)
try:
    from dotenv import load_dotenv

    load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))
except Exception:
    pass

app = FastAPI(title="Aminus Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/invoices/screen")
async def screen_invoice(file: UploadFile = File(...)) -> Dict[str, Any]:
    """
    Upload PDF -> Stage 1 security check -> Stage 2 reconciliation -> persist -> return result
    """

    pdf_bytes = await file.read()

    security = run_security_check(pdf_bytes)

    # Stage 1 result:
    #   security.match == False + status "danger"  → XML vs visual mismatch → fraud signal
    #   security.status == "error"                 → extraction failed → needs manual review
    if security.status != "ok" or not security.match:
        out_status = "danger" if security.status == "danger" else "to_be_checked"
        return {
            "status": out_status,
            "stage": "security",
            "security": {
                "status": security.status,
                "match": security.match,
                "diffs": security.diffs,
            },
        }

    # Stage 2 — use best available structured data (XML preferred, else vision)
    reconciliation = reconcile_with_erp(security.best or security.facturx or security.vision or {})
    decision = reconciliation.get("decision", "")

    if decision == "already_paid":
        final_status = "checked"       # invoice verified and already settled
    elif decision == "not_yet_paid":
        final_status = "not_yet_paid"  # valid invoice, payment still outstanding
    else:
        final_status = "to_be_checked" # needs_review or ambiguous → manual review

    try:
        persist = store_invoice(
            pdf_bytes,
            metadata={
                "status": final_status,
                "filename": file.filename,
                "security": {
                    "status": security.status,
                    "match": security.match,
                    "diffs": security.diffs,
                },
                "reconciliation": reconciliation,
                "extracted": {
                    "facturx": security.facturx,
                    "vision": security.vision,
                },
            },
        )
    except Exception as exc:
        # Keep screening usable locally even if external persistence is unavailable.
        persist = {
            "ok": False,
            "error": f"Persistence unavailable: {exc}",
        }

    return {
        "status": final_status,
        "stage": "done",
        "security": {
            "status": security.status,
            "match": security.match,
            "diffs": security.diffs,
        },
        "reconciliation": reconciliation,
        "persistence": persist,
        "backend_public_url": os.getenv("BACKEND_PUBLIC_URL", "http://localhost:8000"),
        "filename": file.filename,
        "content_type": file.content_type,
        "bytes": len(pdf_bytes),
    }

