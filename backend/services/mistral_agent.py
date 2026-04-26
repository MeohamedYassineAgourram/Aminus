import os
from typing import Any, Dict, List, Optional
import json


def reconcile_with_erp(context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Stage 2 — ERP reconciliation with Claude.
    Fetches vendor profile, POs, payment history, and email threads,
    then asks Claude to decide: not_yet_paid | already_paid | needs_review
    """
    from backend.erp.context import get_erp_context

    anthropic_key = os.getenv("ANTHROPIC_API_KEY")

    vendor_name = context.get("supplier_name")
    amount_raw  = context.get("total_amount")
    amount: Optional[float] = None
    try:
        if amount_raw is not None:
            amount = float(str(amount_raw).replace(",", ".").replace(" ", ""))
    except (ValueError, TypeError):
        pass

    erp = get_erp_context(vendor_name, amount)

    if not anthropic_key:
        return {
            "status": "stub",
            "decision": "to_be_checked",
            "reason": "ANTHROPIC_API_KEY not configured",
            "erp_context": erp,
        }

    from anthropic import Anthropic
    client = Anthropic(api_key=anthropic_key)

    prompt = (
        "You are an accounts-payable reconciliation agent for a French company.\n"
        "Your job: match the incoming invoice against the company's ERP data and decide the payment status.\n\n"
        "MATCHING RULES:\n"
        "  1. PO amounts in the ERP are always HT (before tax, excluding TVA).\n"
        "     Invoice amounts are TTC (including TVA, typically 20% in France).\n"
        "     A difference of ~20% between invoice TTC and PO HT is NORMAL and expected.\n"
        "     Example: PO HT = 10,300 EUR → Invoice TTC = 12,360 EUR (+20% TVA) → confirmed match.\n"
        "  2. Match on: vendor name (fuzzy OK) + IBAN + amount (within TVA tolerance ±25%).\n"
        "  3. A partial IBAN match or slight name variation is acceptable.\n"
        "  4. Check payment_history — if the same invoice_ref already appears there, the invoice is a duplicate.\n"
        "  5. Use email_threads for extra context: payment confirmations, duplicate warnings, disputes.\n"
        "  6. Check vendor_profile trust_score and notes for known fraud patterns.\n\n"
        "DECISION RULES (strict):\n"
        "  - 'already_paid'  : PO status is 'paid' OR the invoice_ref appears in payment_history → duplicate, do NOT pay again.\n"
        "  - 'not_yet_paid'  : vendor name + IBAN + amount match an open or partially-paid PO → legitimate outstanding invoice.\n"
        "                      Use 'not_yet_paid' even if the invoice does not explicitly list the PO number.\n"
        "                      This is the EXPECTED outcome for a valid new invoice from a known vendor.\n"
        "  - 'danger'        : the invoice IBAN does NOT match the vendor's known IBAN in the ERP vendor profile.\n"
        "                      An IBAN change on an invoice is a classic fraud signal (BEC attack). Flag immediately.\n"
        "                      Also use 'danger' if the vendor trust_score is 1 or 2 AND the amount is unusually high.\n"
        "  - 'needs_review'  : use ONLY when there is truly NO plausible PO match (completely different vendor,\n"
        "                      amount off by >25% beyond TVA, or critical data entirely missing) AND no fraud signal.\n"
        "                      Do NOT use 'needs_review' if a reasonable match exists.\n\n"
        "INVOICE:\n"
        f"{json.dumps(context, ensure_ascii=False, indent=2)}\n\n"
        "ERP CONTEXT:\n"
        f"{json.dumps(erp, ensure_ascii=False, indent=2)}\n\n"
        "IMPORTANT: Output EXACTLY one JSON object and nothing else — no prose, no markdown, no self-correction.\n"
        "If you are unsure, still output a single JSON with your best decision.\n"
        "{\"decision\": \"...\", \"reason\": \"...\", \"matched_po\": \"PO-number or null\"}"
    )

    models: List[str] = []
    configured = os.getenv("ANTHROPIC_MODEL", "").strip()
    if configured:
        models.append(configured)
    models.extend([
        "claude-sonnet-4-6",
        "claude-sonnet-4-5-20250929",
        "claude-haiku-4-5-20251001",
    ])
    seen: set = set()
    deduped = [m for m in models if m and not (m in seen or seen.add(m))]  # type: ignore[func-returns-value]

    text = ""
    last_error: Optional[str] = None
    for model_id in deduped:
        try:
            out = client.messages.create(
                model=model_id,
                max_tokens=600,
                messages=[{"role": "user", "content": prompt}],
            )
            text = "".join(getattr(b, "text", "") for b in out.content).strip()
            if text:
                break
        except Exception as exc:
            last_error = f"{type(exc).__name__}: {exc}"

    if not text:
        return {
            "status": "stub",
            "decision": "to_be_checked",
            "reason": f"Claude call failed ({last_error or 'unknown'})",
            "erp_context": erp,
        }

    # Try direct parse first
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return {"status": "ok", **parsed, "erp_context": erp}
        return {"status": "ok", "value": parsed, "erp_context": erp}
    except Exception:
        pass

    # Claude sometimes outputs prose + multiple JSON blocks (self-correction).
    # Scan all {...} spans and return the LAST one with a "decision" key.
    import re as _re
    candidates = list(_re.finditer(r'\{', text))
    for m in reversed(candidates):
        start = m.start()
        # find matching closing brace
        depth = 0
        for i, ch in enumerate(text[start:]):
            if ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0:
                    span = text[start: start + i + 1]
                    try:
                        parsed = json.loads(span)
                        if isinstance(parsed, dict) and "decision" in parsed:
                            return {"status": "ok", **parsed, "erp_context": erp}
                    except Exception:
                        pass
                    break

    return {"status": "ok", "raw": text[:2000], "erp_context": erp}
