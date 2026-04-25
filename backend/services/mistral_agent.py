import os
from typing import Any, Dict, Optional
import json

from backend.core.supabase_client import get_supabase_client


def reconcile_with_erp(context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Stage 2:
    - Use Supabase ERP tables as ground truth
    - Optionally use Claude API to reason over matches / payment state

    For hackathon/dev, this returns a deterministic stub when not configured.
    """

    supabase = get_supabase_client()
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")

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

    if not anthropic_key:
        return {
            "status": "stub",
            "decision": "to_be_checked",
            "reason": "ANTHROPIC_API_KEY not configured",
            "erp_hint": erp_hint,
        }

    from anthropic import Anthropic

    client = Anthropic(api_key=anthropic_key)
    prompt = (
        "You are an accounting reconciliation agent.\n"
        "Given the invoice JSON, decide one of: not_yet_paid | already_paid | needs_review.\n"
        "Return STRICT JSON only: {\"decision\":\"...\",\"reason\":\"...\"}.\n"
        f"invoice={context}\n"
        f"erp_hint={erp_hint}\n"
    )

    models = []
    configured_model = os.getenv("ANTHROPIC_MODEL", "").strip()
    if configured_model:
        models.append(configured_model)

    try:
        listed = client.models.list(limit=20)
        listed_ids = [getattr(m, "id", "") for m in getattr(listed, "data", [])]
        preferred = [m for m in listed_ids if "sonnet" in m]
        models.extend(preferred or listed_ids)
    except Exception:
        pass

    models.extend(
        [
            "claude-sonnet-4-20250514",
            "claude-3-7-sonnet-20250219",
            "claude-3-5-sonnet-20241022",
        ]
    )
    # Preserve order while removing duplicates/empties.
    deduped = []
    for m in models:
        if m and m not in deduped:
            deduped.append(m)
    models = deduped

    text = ""
    last_error: Optional[str] = None
    for model_name in models:
        try:
            out = client.messages.create(
                model=model_name,
                max_tokens=400,
                temperature=0.2,
                messages=[{"role": "user", "content": prompt}],
            )
            text_chunks = []
            for block in out.content:
                block_text = getattr(block, "text", None)
                if block_text:
                    text_chunks.append(block_text)
            text = "\n".join(text_chunks).strip()
            if text:
                break
        except Exception as exc:
            last_error = f"{type(exc).__name__}: {exc}"
            continue

    if not text:
        return {
            "status": "stub",
            "decision": "to_be_checked",
            "reason": f"Claude call failed ({last_error or 'unknown error'})",
            "erp_hint": erp_hint,
        }

    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return {"status": "ok", **parsed, "erp_hint": erp_hint}
        return {"status": "ok", "value": parsed, "erp_hint": erp_hint}
    except Exception:
        # Graceful fallback when model wraps JSON in prose/markdown.
        if "{" in text and "}" in text:
            try:
                json_blob = text[text.find("{") : text.rfind("}") + 1]
                parsed = json.loads(json_blob)
                if isinstance(parsed, dict):
                    return {"status": "ok", **parsed, "erp_hint": erp_hint}
            except Exception:
                pass
        return {"status": "ok", "raw": text[:4000], "erp_hint": erp_hint}

