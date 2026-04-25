import io
from typing import Any, Dict, Optional


def extract_facturx_json(pdf_bytes: bytes) -> Optional[Dict[str, Any]]:
    """
    Extract embedded Factur-X XML and convert to JSON-like dict.

    If the Factur-X library is unavailable or the PDF has no embedded XML,
    returns a minimal stub (so the pipeline still runs during early dev).
    """

    try:
        # Prefer real extraction if the library is available.
        from facturx import get_facturx_xml_from_pdf  # type: ignore

        xml_bytes = get_facturx_xml_from_pdf(io.BytesIO(pdf_bytes))
        if not xml_bytes:
            return None

        # Minimal XML->dict to keep dependencies light; you can replace with a proper mapper.
        import xml.etree.ElementTree as ET

        root = ET.fromstring(xml_bytes)
        return {
            "type": "facturx",
            "root_tag": root.tag,
            "text": " ".join((root.itertext() or []))[:2000],
        }
    except Exception:
        # Dev-mode fallback: return the same schema as vision stub,
        # so the pipeline can reach stage 2 without external APIs.
        return {
            "type": "facturx_stub",
            "supplier_name": None,
            "invoice_number": None,
            "invoice_date": None,
            "currency": None,
            "total_amount": None,
            "iban": None,
        }

