import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from .extractor import extract_facturx_json
from .vision_agent import extract_gemini_json


@dataclass
class SecurityCheckResult:
    status: str  # "ok" | "danger" | "error"
    match: bool
    diffs: List[str]
    facturx: Optional[Dict[str, Any]]
    vision: Optional[Dict[str, Any]]


def _normalize(obj: Any) -> Any:
    if obj is None:
        return None
    if isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, list):
        return [_normalize(x) for x in obj]
    if isinstance(obj, dict):
        return {str(k).strip(): _normalize(v) for k, v in sorted(obj.items(), key=lambda kv: str(kv[0]))}
    return str(obj)


def _diff(a: Any, b: Any, path: str = "") -> List[str]:
    diffs: List[str] = []
    if type(a) != type(b):
        diffs.append(f"{path}: type mismatch ({type(a).__name__} != {type(b).__name__})")
        return diffs

    if isinstance(a, dict):
        keys = set(a.keys()) | set(b.keys())
        for k in sorted(keys):
            pa = a.get(k, "__missing__")
            pb = b.get(k, "__missing__")
            p = f"{path}.{k}" if path else str(k)
            if pa == "__missing__":
                diffs.append(f"{p}: missing in facturx")
            elif pb == "__missing__":
                diffs.append(f"{p}: missing in vision")
            else:
                diffs.extend(_diff(pa, pb, p))
        return diffs

    if isinstance(a, list):
        if len(a) != len(b):
            diffs.append(f"{path}: length mismatch ({len(a)} != {len(b)})")
        for i, (xa, xb) in enumerate(zip(a, b)):
            diffs.extend(_diff(xa, xb, f"{path}[{i}]"))
        return diffs

    if a != b:
        diffs.append(f"{path}: {json.dumps(a, ensure_ascii=False)} != {json.dumps(b, ensure_ascii=False)}")
    return diffs


def run_security_check(pdf_bytes: bytes) -> SecurityCheckResult:
    """
    Stage 1:
    - Extract structured data from embedded Factur-X XML (backend truth)
    - Extract "what the human sees" with Gemini Vision
    - Normalize + compare; if mismatch => danger
    """

    try:
        facturx = extract_facturx_json(pdf_bytes)
        vision = extract_gemini_json(pdf_bytes)

        if facturx is None or vision is None:
            return SecurityCheckResult(
                status="error",
                match=False,
                diffs=["missing extraction output (facturx or vision)"],
                facturx=facturx,
                vision=vision,
            )

        # Compare business fields only (ignore provenance/type metadata).
        facturx_cmp = dict(facturx)
        vision_cmp = dict(vision)
        facturx_cmp.pop("type", None)
        vision_cmp.pop("type", None)

        na = _normalize(facturx_cmp)
        nb = _normalize(vision_cmp)
        diffs = _diff(na, nb)
        match = len(diffs) == 0
        return SecurityCheckResult(
            status="ok" if match else "danger",
            match=match,
            diffs=diffs[:50],
            facturx=facturx,
            vision=vision,
        )
    except Exception as e:
        return SecurityCheckResult(
            status="error",
            match=False,
            diffs=[f"security_check_error: {type(e).__name__}: {e}"],
            facturx=None,
            vision=None,
        )

