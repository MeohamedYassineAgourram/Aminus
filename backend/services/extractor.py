import io
import json
import re
from typing import Any, Dict, Optional


# XML namespace prefixes used by Factur-X / ZUGFeRD / EN 16931
_NS = {
    "ram": "urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100",
    "rsm": "urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100",
    "udt": "urn:un:unece:uncefact:data:standard:UnqualifiedDataType:100",
    "qdt": "urn:un:unece:uncefact:data:standard:QualifiedDataType:100",
}


def _text(root: Any, *xpaths: str) -> Optional[str]:
    """Try multiple XPaths and return first non-empty text found."""
    import xml.etree.ElementTree as ET
    for path in xpaths:
        try:
            el = root.find(path, _NS)
            if el is not None and el.text and el.text.strip():
                return el.text.strip()
        except Exception:
            continue
    return None


def extract_facturx_json(pdf_bytes: bytes) -> Optional[Dict[str, Any]]:
    """
    1. Try to extract the embedded Factur-X XML from the PDF.
    2. Parse the XML into a flat invoice dict.
    3. If no XML is present, fall back to None (signals: no embedded data).
    """
    try:
        from facturx import get_facturx_xml_from_pdf  # type: ignore

        # The library returns (xml_bytes, xml_filename) or (False, False)
        result = get_facturx_xml_from_pdf(io.BytesIO(pdf_bytes))
        xml_bytes_raw, _ = result
        if not xml_bytes_raw:
            return None  # PDF has no embedded Factur-X XML

        import xml.etree.ElementTree as ET

        root = ET.fromstring(xml_bytes_raw)

        # ── Supplier ─────────────────────────────────────────────────────
        supplier_name = _text(
            root,
            ".//ram:SellerTradeParty/ram:Name",
            ".//ram:SellerTradeParty/ram:SpecifiedLegalOrganization/ram:TradingBusinessName",
        )

        # ── Invoice number ────────────────────────────────────────────────
        invoice_number = _text(root, ".//rsm:ExchangedDocument/ram:ID")

        # ── Invoice date  (format: YYYYMMDD in XML) ───────────────────────
        raw_date = _text(
            root,
            ".//rsm:ExchangedDocument/ram:IssueDateTime/udt:DateTimeString",
        )
        invoice_date: Optional[str] = None
        if raw_date:
            raw_date = raw_date.strip()
            if re.match(r"^\d{8}$", raw_date):
                invoice_date = f"{raw_date[:4]}-{raw_date[4:6]}-{raw_date[6:]}"
            else:
                invoice_date = raw_date

        # ── Currency ──────────────────────────────────────────────────────
        currency = _text(
            root,
            ".//ram:InvoiceCurrencyCode",
            ".//ram:TaxBasisTotalAmount",  # has currencyID attr fallback below
        )
        if not currency:
            # Try reading currencyID attribute from monetary totals
            el = root.find(".//ram:GrandTotalAmount", _NS)
            if el is not None:
                currency = el.attrib.get("currencyID")

        # ── Total amount (TTC / GrandTotal) ───────────────────────────────
        total_amount: Optional[float] = None
        for path in [
            ".//ram:GrandTotalAmount",
            ".//ram:DuePayableAmount",
            ".//ram:TaxInclusiveBasisAmount",
        ]:
            raw = _text(root, path)
            if raw:
                try:
                    total_amount = float(raw.replace(",", ".").replace(" ", ""))
                    break
                except ValueError:
                    continue

        # ── IBAN ──────────────────────────────────────────────────────────
        iban = _text(
            root,
            ".//ram:SellerSpecifiedTaxRegistration/ram:ID",  # fallback
            ".//ram:PayeeSpecifiedCreditorFinancialAccount/ram:IBANID",
            ".//ram:SpecifiedCreditorFinancialAccount/ram:IBANID",
        )

        return {
            "type": "facturx",
            "supplier_name": supplier_name,
            "invoice_number": invoice_number,
            "invoice_date": invoice_date,
            "currency": currency or "EUR",
            "total_amount": total_amount,
            "iban": iban,
        }

    except ImportError:
        # Library not installed — return None so vision becomes the only source
        return None
    except Exception as exc:
        # XML parse or mapping error — return None, don't silently swallow data
        return None
