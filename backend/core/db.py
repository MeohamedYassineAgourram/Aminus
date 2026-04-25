import os
from typing import Any, Dict, Optional


def get_database_url() -> Optional[str]:
    return os.getenv("DATABASE_URL")


def get_invoices_table() -> str:
    return os.getenv("INVOICES_TABLE", "invoices")


def insert_invoice_row(
    *,
    status: Optional[str],
    filename: Optional[str],
    pdf_path: Optional[str],
    pdf_url: Optional[str],
    security: Dict[str, Any],
    reconciliation: Dict[str, Any],
    extracted: Dict[str, Any],
) -> Dict[str, Any]:
    import psycopg

    url = get_database_url()
    if not url:
        return {"status": "stub", "reason": "DATABASE_URL not configured"}

    # Pull structured fields out of extracted data when available.
    fx = (extracted or {}).get("facturx") or {}
    vendor_name    = fx.get("supplier_name")
    invoice_number = fx.get("invoice_number")
    invoice_date   = fx.get("invoice_date") or None
    amount_raw     = fx.get("total_amount")
    currency       = fx.get("currency") or "EUR"
    iban           = fx.get("iban")

    # Coerce amount to numeric or None
    amount: Optional[float] = None
    try:
        if amount_raw is not None:
            amount = float(str(amount_raw).replace(",", ".").replace(" ", ""))
    except (ValueError, TypeError):
        amount = None

    # Normalise invoice_date to ISO string or None
    invoice_date_str: Optional[str] = None
    if invoice_date:
        try:
            from datetime import datetime
            for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d.%m.%Y", "%m/%d/%Y"):
                try:
                    invoice_date_str = datetime.strptime(str(invoice_date), fmt).date().isoformat()
                    break
                except ValueError:
                    continue
        except Exception:
            pass

    table = get_invoices_table()

    with psycopg.connect(url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                INSERT INTO {table} (
                    filename, vendor_name, invoice_number, invoice_date,
                    amount, currency, iban,
                    status, pdf_path, pdf_url,
                    security, reconciliation, extracted
                )
                VALUES (
                    %s, %s, %s, %s::date,
                    %s, %s, %s,
                    %s, %s, %s,
                    %s::jsonb, %s::jsonb, %s::jsonb
                )
                RETURNING id
                """,
                (
                    filename, vendor_name, invoice_number, invoice_date_str,
                    amount, currency, iban,
                    status, pdf_path, pdf_url,
                    psycopg.types.json.Jsonb(security),
                    psycopg.types.json.Jsonb(reconciliation),
                    psycopg.types.json.Jsonb(extracted),
                ),
            )
            row_id = cur.fetchone()[0]
            conn.commit()
            return {"status": "ok", "id": row_id}
