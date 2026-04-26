import os
from typing import Any, Dict, List, Optional
import json

from backend.core.db import get_database_url


def _fetch_erp_rows(vendor_name: Optional[str], amount: Optional[float]) -> List[Dict]:
    """
    Query erp_purchase_orders directly via DATABASE_URL.
    Returns relevant open/partial POs, filtered by vendor name when possible.
    """
    url = get_database_url()
    if not url:
        return []

    try:
        import psycopg
        with psycopg.connect(url) as conn:
            with conn.cursor() as cur:
                if vendor_name:
                    cur.execute(
                        """
                        SELECT po_number, vendor_name, vendor_iban, amount, currency,
                               status, invoice_ref, due_date, description
                        FROM erp_purchase_orders
                        WHERE status IN ('open', 'partially_paid')
                          AND lower(vendor_name) LIKE lower(%s)
                        ORDER BY due_date
                        LIMIT 10
                        """,
                        (f"%{vendor_name}%",),
                    )
                    rows = cur.fetchall()
                    if not rows:
                        # Fallback: return all open POs so agent has context
                        cur.execute(
                            """
                            SELECT po_number, vendor_name, vendor_iban, amount, currency,
                                   status, invoice_ref, due_date, description
                            FROM erp_purchase_orders
                            WHERE status IN ('open', 'partially_paid')
                            ORDER BY due_date
                            LIMIT 10
                            """
                        )
                        rows = cur.fetchall()
                else:
                    cur.execute(
                        """
                        SELECT po_number, vendor_name, vendor_iban, amount, currency,
                               status, invoice_ref, due_date, description
                        FROM erp_purchase_orders
                        WHERE status IN ('open', 'partially_paid')
                        ORDER BY due_date
                        LIMIT 10
                        """
                    )
                    rows = cur.fetchall()

                cols = ["po_number", "vendor_name", "vendor_iban", "amount", "currency",
                        "status", "invoice_ref", "due_date", "description"]
                return [dict(zip(cols, (str(v) if v is not None else None for v in row))) for row in rows]
    except Exception as e:
        return [{"error": f"{type(e).__name__}: {e}"}]


def reconcile_with_erp(context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Stage 2 — ERP reconciliation with Claude.
    Queries erp_purchase_orders for matching POs, then asks Claude to decide:
      not_yet_paid | already_paid | needs_review
    """
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")

    vendor_name = context.get("supplier_name")
    amount_raw  = context.get("total_amount")
    amount: Optional[float] = None
    try:
        if amount_raw is not None:
            amount = float(str(amount_raw).replace(",", ".").replace(" ", ""))
    except (ValueError, TypeError):
        pass

    erp_rows = _fetch_erp_rows(vendor_name, amount)

    if not anthropic_key:
        return {
            "status": "stub",
            "decision": "to_be_checked",
            "reason": "ANTHROPIC_API_KEY not configured",
            "erp_rows": erp_rows,
        }

    from anthropic import Anthropic
    client = Anthropic(api_key=anthropic_key)

    prompt = (
        "You are an accounts-payable reconciliation agent for a French company.\n"
        "Your job: match the invoice against the company's purchase orders and decide the payment status.\n\n"
        "IMPORTANT RULES:\n"
        "  1. PO amounts in the ERP are always HT (before tax, excluding TVA).\n"
        "     Invoice amounts are TTC (including TVA, typically 20% in France).\n"
        "     A difference of ~20% between the invoice TTC and the PO HT is NORMAL and expected.\n"
        "     Example: PO HT = 10,300 EUR → Invoice TTC = 12,360 EUR (+20% TVA) → this IS a match.\n"
        "  2. Match primarily on: vendor name (fuzzy OK) + IBAN + approximate amount (within TVA tolerance).\n"
        "  3. A partial IBAN match or slight name variation is acceptable.\n\n"
        "Decisions:\n"
        "  - 'already_paid'  : invoice matches a PO with status 'paid' — this is a duplicate payment attempt\n"
        "  - 'not_yet_paid'  : invoice matches an open or partially-paid PO — legitimate, payment is outstanding\n"
        "  - 'needs_review'  : no matching PO found at all, or critical data (vendor, amount) is missing/inconsistent\n\n"
        "INVOICE:\n"
        f"{json.dumps(context, ensure_ascii=False, indent=2)}\n\n"
        "PURCHASE ORDERS FROM ERP:\n"
        f"{json.dumps(erp_rows, ensure_ascii=False, indent=2)}\n\n"
        "Return ONLY valid JSON — no markdown, no prose:\n"
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
    # Deduplicate while preserving order
    seen: set = set()
    deduped = [m for m in models if m and not (m in seen or seen.add(m))]  # type: ignore[func-returns-value]

    text = ""
    last_error: Optional[str] = None
    for model_id in deduped:
        try:
            out = client.messages.create(
                model=model_id,
                max_tokens=400,
                messages=[{"role": "user", "content": prompt}],
            )
            text = "".join(
                getattr(b, "text", "") for b in out.content
            ).strip()
            if text:
                break
        except Exception as exc:
            last_error = f"{type(exc).__name__}: {exc}"

    if not text:
        return {
            "status": "stub",
            "decision": "to_be_checked",
            "reason": f"Claude call failed ({last_error or 'unknown'})",
            "erp_rows": erp_rows,
        }

    # Parse JSON response
    try:
        parsed = json.loads(text)
    except Exception:
        # Strip markdown fences if model wrapped the JSON
        if "{" in text and "}" in text:
            try:
                parsed = json.loads(text[text.find("{"):text.rfind("}") + 1])
            except Exception:
                return {"status": "ok", "raw": text[:2000], "erp_rows": erp_rows}
        else:
            return {"status": "ok", "raw": text[:2000], "erp_rows": erp_rows}

    if isinstance(parsed, dict):
        return {"status": "ok", **parsed, "erp_rows": erp_rows}
    return {"status": "ok", "value": parsed, "erp_rows": erp_rows}
