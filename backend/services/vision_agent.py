import base64
import json
import os
import re
from typing import Any, Dict, Optional


_PROMPT = (
    "You are reading an invoice PDF. Extract the following fields exactly as they appear.\n"
    "Return ONLY a valid JSON object — no markdown, no prose, no explanation.\n\n"
    "Fields to extract:\n"
    "  supplier_name   — company name of the invoice issuer\n"
    "  invoice_number  — invoice reference / number\n"
    "  invoice_date    — issue date in YYYY-MM-DD format\n"
    "  currency        — 3-letter ISO currency code (e.g. EUR, USD)\n"
    "  total_amount    — total amount due INCLUDING tax (numeric, no symbols)\n"
    "  iban            — IBAN of the payee if present, else null\n\n"
    "If a field is not visible or not applicable, set it to null.\n"
    'Example: {"supplier_name":"Acme SAS","invoice_number":"INV-001",'
    '"invoice_date":"2024-11-15","currency":"EUR","total_amount":12360.00,"iban":"FR76..."}'
)


def extract_vision_json(pdf_bytes: bytes) -> Optional[Dict[str, Any]]:
    """
    Send the PDF to Claude and extract invoice fields visually.
    Falls back to Google Gemini if GOOGLE_API_KEY is set and Anthropic is not.
    Returns None on hard failure.
    """

    # ── Try Claude first (preferred — key is always present) ─────────────
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    if anthropic_key:
        result = _extract_with_claude(pdf_bytes, anthropic_key)
        if result is not None:
            return result

    # ── Gemini fallback ───────────────────────────────────────────────────
    google_key = os.getenv("GOOGLE_API_KEY")
    if google_key:
        result = _extract_with_gemini(pdf_bytes, google_key)
        if result is not None:
            return result

    return None


def _parse_json_response(text: str) -> Optional[Dict[str, Any]]:
    """Strip markdown fences and parse JSON."""
    text = text.strip()
    # Remove ```json ... ``` or ``` ... ```
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    text = text.strip()
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            parsed["type"] = "vision_claude"
            return parsed
    except Exception:
        # Try extracting the first {...} block
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if m:
            try:
                parsed = json.loads(m.group())
                if isinstance(parsed, dict):
                    parsed["type"] = "vision_claude"
                    return parsed
            except Exception:
                pass
    return None


def _extract_with_claude(pdf_bytes: bytes, api_key: str) -> Optional[Dict[str, Any]]:
    try:
        from anthropic import Anthropic

        client = Anthropic(api_key=api_key)
        pdf_b64 = base64.standard_b64encode(pdf_bytes).decode("utf-8")

        models = ["claude-sonnet-4-6", "claude-sonnet-4-5-20250929", "claude-haiku-4-5-20251001"]
        configured = os.getenv("ANTHROPIC_MODEL", "").strip()
        if configured:
            models.insert(0, configured)

        for model_id in models:
            try:
                response = client.messages.create(
                    model=model_id,
                    max_tokens=512,
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "document",
                                    "source": {
                                        "type": "base64",
                                        "media_type": "application/pdf",
                                        "data": pdf_b64,
                                    },
                                },
                                {"type": "text", "text": _PROMPT},
                            ],
                        }
                    ],
                )
                text = "".join(
                    getattr(b, "text", "") for b in response.content
                ).strip()
                if text:
                    return _parse_json_response(text)
            except Exception:
                continue
    except Exception:
        pass
    return None


def _extract_with_gemini(pdf_bytes: bytes, api_key: str) -> Optional[Dict[str, Any]]:
    try:
        from google import genai  # type: ignore

        client = genai.Client(api_key=api_key)
        result = client.models.generate_content(
            model="gemini-1.5-pro",
            contents=[
                {"role": "user", "parts": [{"text": _PROMPT}]},
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
        if text:
            parsed = _parse_json_response(text)
            if parsed:
                parsed["type"] = "vision_gemini"
                return parsed
    except Exception:
        pass
    return None


# ── Public alias kept for backward compat with security_check.py ─────────
def extract_gemini_json(pdf_bytes: bytes) -> Optional[Dict[str, Any]]:
    return extract_vision_json(pdf_bytes)
