import os
from typing import Any, Dict, Optional

from backend.core.supabase_client import get_supabase_client


def reconcile_with_erp(context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Stage 2:
    - Use Supabase ERP tables as ground truth
    - Optionally use Mistral Agent API to reason over matches / payment state

    For hackathon/dev, this returns a deterministic stub when not configured.
    """

    supabase = get_supabase_client()
    mistral_key = os.getenv("MISTRAL_API_KEY")

    # Minimal DB check (if configured)
    erp_hint: Optional[Dict[str, Any]] = None
    if supabase is not None:
        try:
            # Example table name from your spec
            resp = (
                supabase.table("erp_purchase_orders")
                .select("*")
                .limit(5)
                .execute()
            )
            erp_hint = {"rows": getattr(resp, "data", None)}
        except Exception as e:
            erp_hint = {"error": f"{type(e).__name__}: {e}"}

    if not mistral_key:
        return {
            "status": "stub",
            "decision": "to_be_checked",
            "reason": "MISTRAL_API_KEY not configured",
            "erp_hint": erp_hint,
        }

    from mistralai import Mistral

    client = Mistral(api_key=mistral_key)
    prompt = (
        "You are an accounting reconciliation agent.\n"
        "Given the invoice JSON, decide one of: not_yet_paid | already_paid | needs_review.\n"
        "Return STRICT JSON: {decision, reason}.\n"
        f"invoice={context}\n"
        f"erp_hint={erp_hint}\n"
    )

    out = client.chat.complete(
        model="mistral-large-latest",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
    )
    text = (out.choices[0].message.content or "").strip()
    import json

    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return {"status": "ok", **parsed, "erp_hint": erp_hint}
        return {"status": "ok", "value": parsed, "erp_hint": erp_hint}
    except Exception:
        return {"status": "ok", "raw": text[:4000], "erp_hint": erp_hint}

