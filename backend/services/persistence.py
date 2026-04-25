import os
import time
from typing import Any, Dict, Optional

from backend.core.supabase_client import get_supabase_client
from backend.core.db import insert_invoice_row


def store_invoice(pdf_bytes: bytes, metadata: Dict[str, Any]) -> Dict[str, Any]:
    """
    Final stage: persist PDF to Supabase Storage and a row to `invoices`.
    If Supabase isn't configured, returns a stub response.
    """

    supabase = get_supabase_client()
    if supabase is None:
        # Fallback: store extracted results in Postgres directly (no PDF storage).
        return {
            "status": "fallback_db",
            "db": insert_invoice_row(
                status=metadata.get("status"),
                filename=metadata.get("filename"),
                pdf_path=None,
                pdf_url=None,
                security=metadata.get("security") or {},
                reconciliation=metadata.get("reconciliation") or {},
                extracted=metadata.get("extracted") or {},
            ),
        }

    bucket = os.getenv("SUPABASE_BUCKET", "invoices")
    ts = int(time.time())
    path = f"{ts}.pdf"

    # Storage upload
    upload = supabase.storage.from_(bucket).upload(
        path,
        pdf_bytes,
        {"content-type": "application/pdf", "x-upsert": "true"},
    )

    public_url: Optional[str] = None
    try:
        public_url = supabase.storage.from_(bucket).get_public_url(path)
    except Exception:
        public_url = None

    # DB row
    row = {
        "pdf_path": path,
        "pdf_url": public_url,
        "status": metadata.get("status"),
        "security": metadata.get("security"),
        "reconciliation": metadata.get("reconciliation"),
        "extracted": metadata.get("extracted"),
    }

    insert = supabase.table("invoices").insert(row).execute()

    return {
        "status": "ok",
        "storage": {"bucket": bucket, "path": path, "upload": getattr(upload, "data", None)},
        "db": {"inserted": getattr(insert, "data", None)},
    }

