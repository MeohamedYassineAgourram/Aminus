"""
Fetch rich ERP context for a given invoice (vendor name + amount).
Returns a dict with: vendor profile, open POs, payment history, email threads.
"""

from typing import Any, Dict, List, Optional


def get_erp_context(vendor_name: Optional[str], amount: Optional[float]) -> Dict[str, Any]:
    from backend.core.db import get_database_url
    import psycopg

    url = get_database_url()
    if not url:
        return {"error": "DATABASE_URL not configured"}

    try:
        with psycopg.connect(url) as conn:
            vendor   = _fetch_vendor(conn, vendor_name)
            pos      = _fetch_pos(conn, vendor_name)
            payments = _fetch_payments(conn, vendor_name)
            emails   = _fetch_emails(conn, vendor_name)

        return {
            "vendor_profile": vendor,
            "purchase_orders": pos,
            "payment_history": payments,
            "email_threads": emails,
        }
    except Exception as exc:
        return {"error": f"{type(exc).__name__}: {exc}"}


def _fetch_vendor(conn, vendor_name: Optional[str]) -> Optional[Dict]:
    if not vendor_name:
        return None
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT vendor_name, vendor_iban, vat_number, siret,
                   address, city, postal_code, country,
                   contact_name, contact_email,
                   payment_terms, category, status, trust_score, notes
            FROM erp_vendors
            WHERE lower(vendor_name) LIKE lower(%s)
            LIMIT 1
            """,
            (f"%{vendor_name}%",),
        )
        row = cur.fetchone()
        if not row:
            return None
        cols = ["vendor_name", "vendor_iban", "vat_number", "siret",
                "address", "city", "postal_code", "country",
                "contact_name", "contact_email",
                "payment_terms", "category", "status", "trust_score", "notes"]
        return dict(zip(cols, (str(v) if v is not None else None for v in row)))


def _fetch_pos(conn, vendor_name: Optional[str]) -> List[Dict]:
    cols = ["po_number", "vendor_name", "vendor_iban", "amount", "currency",
            "status", "invoice_ref", "due_date", "description"]
    with conn.cursor() as cur:
        if vendor_name:
            cur.execute(
                """
                SELECT po_number, vendor_name, vendor_iban, amount, currency,
                       status, invoice_ref, due_date, description
                FROM erp_purchase_orders
                WHERE lower(vendor_name) LIKE lower(%s)
                ORDER BY due_date
                LIMIT 10
                """,
                (f"%{vendor_name}%",),
            )
            rows = cur.fetchall()
            if not rows:
                # Fallback: all open POs so agent has context
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
    return [dict(zip(cols, (str(v) if v is not None else None for v in row))) for row in rows]


def _fetch_payments(conn, vendor_name: Optional[str]) -> List[Dict]:
    cols = ["po_number", "vendor_name", "invoice_ref", "amount_paid", "currency",
            "payment_date", "bank_ref", "payment_method", "notes"]
    with conn.cursor() as cur:
        if vendor_name:
            cur.execute(
                """
                SELECT po_number, vendor_name, invoice_ref, amount_paid, currency,
                       payment_date, bank_ref, payment_method, notes
                FROM erp_payments
                WHERE lower(vendor_name) LIKE lower(%s)
                ORDER BY payment_date DESC
                LIMIT 10
                """,
                (f"%{vendor_name}%",),
            )
        else:
            cur.execute(
                """
                SELECT po_number, vendor_name, invoice_ref, amount_paid, currency,
                       payment_date, bank_ref, payment_method, notes
                FROM erp_payments
                ORDER BY payment_date DESC
                LIMIT 10
                """
            )
        rows = cur.fetchall()
    return [dict(zip(cols, (str(v) if v is not None else None for v in row))) for row in rows]


def _fetch_emails(conn, vendor_name: Optional[str]) -> List[Dict]:
    cols = ["thread_id", "subject", "vendor_name", "from_email", "to_email",
            "sent_at", "po_ref", "invoice_ref", "thread_type", "body"]
    with conn.cursor() as cur:
        if vendor_name:
            cur.execute(
                """
                SELECT thread_id, subject, vendor_name, from_email, to_email,
                       sent_at, po_ref, invoice_ref, thread_type, body
                FROM erp_emails
                WHERE lower(vendor_name) LIKE lower(%s)
                ORDER BY sent_at DESC
                LIMIT 10
                """,
                (f"%{vendor_name}%",),
            )
        else:
            cur.execute(
                """
                SELECT thread_id, subject, vendor_name, from_email, to_email,
                       sent_at, po_ref, invoice_ref, thread_type, body
                FROM erp_emails
                ORDER BY sent_at DESC
                LIMIT 10
                """
            )
        rows = cur.fetchall()
    return [dict(zip(cols, (str(v) if v is not None else None for v in row))) for row in rows]
