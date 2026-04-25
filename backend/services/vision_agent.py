import os
from typing import Any, Dict, Optional


def extract_gemini_json(pdf_bytes: bytes) -> Optional[Dict[str, Any]]:
    """
    Ask Gemini to read the invoice visually and return a JSON summary.
    If GOOGLE_API_KEY isn't set, returns a stub so the pipeline is testable locally.
    """

    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        return {
            "type": "gemini_stub",
            "supplier_name": None,
            "invoice_number": None,
            "invoice_date": None,
            "currency": None,
            "total_amount": None,
            "iban": None,
        }

    from google import genai

    client = genai.Client(api_key=api_key)

    prompt = (
        "You are a vision model reading an invoice PDF.\n"
        "Extract the key fields as STRICT JSON with keys:\n"
        "{supplier_name, invoice_number, invoice_date, currency, total_amount, iban}\n"
        "If a field is unknown, use null.\n"
        "Return JSON only, no markdown."
    )

    # NOTE: google-genai supports file bytes; for PDFs we send as inline data.
    result = client.models.generate_content(
        model="gemini-1.5-pro",
        contents=[
            {"role": "user", "parts": [{"text": prompt}]},
            {
                "role": "user",
                "parts": [
                    {
                        "inline_data": {
                            "mime_type": "application/pdf",
                            "data": pdf_bytes,
                        }
                    }
                ],
            },
        ],
    )

    text = (getattr(result, "text", None) or "").strip()
    if not text:
        return None

    import json

    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            parsed["type"] = "gemini"
        return parsed if isinstance(parsed, dict) else {"type": "gemini", "value": parsed}
    except Exception:
        return {"type": "gemini", "raw": text[:4000]}

