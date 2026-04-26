import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .extractor import extract_facturx_json
from .vision_agent import extract_vision_json


@dataclass
class SecurityCheckResult:
    status: str           # "ok" | "danger" | "error"
    match: bool
    diffs: List[str]
    facturx: Optional[Dict[str, Any]]
    vision: Optional[Dict[str, Any]]
    # The best structured data to pass downstream (facturx preferred, else vision)
    best: Optional[Dict[str, Any]] = field(default=None)


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
        diffs.append(f"{path}: type mismatch ({type(a).__name__} vs {type(b).__name__})")
        return diffs
    if isinstance(a, dict):
        for k in sorted(set(a) | set(b)):
            pa, pb = a.get(k, "__missing__"), b.get(k, "__missing__")
            p = f"{path}.{k}" if path else k
            if pa == "__missing__":
                diffs.append(f"{p}: present in vision only")
            elif pb == "__missing__":
                diffs.append(f"{p}: present in XML only")
            else:
                diffs.extend(_diff(pa, pb, p))
        return diffs
    if isinstance(a, list):
        if len(a) != len(b):
            diffs.append(f"{path}: list length {len(a)} vs {len(b)}")
        for i, (xa, xb) in enumerate(zip(a, b)):
            diffs.extend(_diff(xa, xb, f"{path}[{i}]"))
        return diffs
    if a != b:
        diffs.append(f"{path}: XML={json.dumps(a, ensure_ascii=False)} vs Vision={json.dumps(b, ensure_ascii=False)}")
    return diffs


_COMPARE_FIELDS = {"supplier_name", "invoice_number", "invoice_date", "currency", "total_amount", "iban"}


def run_security_check(pdf_bytes: bytes) -> SecurityCheckResult:
    """
    Stage 1 security check.

    Case A — PDF has embedded Factur-X XML AND Claude vision extracts data:
        Compare key fields. Any mismatch → status="danger" (fraud signal).

    Case B — No embedded XML, but Claude vision extracts data:
        Cannot do XML/visual comparison. Pass through with a note, use vision
        data for Stage 2. (Non-Factur-X invoices are allowed but noted.)

    Case C — Neither extraction works:
        status="error", flag for manual review.
    """
    try:
        facturx = extract_facturx_json(pdf_bytes)
        vision  = extract_vision_json(pdf_bytes)

        # ── Case C: nothing extracted ─────────────────────────────────────
        if facturx is None and vision is None:
            return SecurityCheckResult(
                status="error",
                match=False,
                diffs=["Could not extract any data from the PDF (no XML, vision failed)."],
                facturx=None,
                vision=None,
                best=None,
            )

        # ── Case B: no embedded XML — skip XML/visual comparison ──────────
        if facturx is None:
            return SecurityCheckResult(
                status="ok",
                match=True,
                diffs=["No embedded Factur-X XML found — security comparison skipped; using visual extraction only."],
                facturx=None,
                vision=vision,
                best=vision,
            )

        # ── Case A: both present — compare key business fields ────────────
        if vision is None:
            # XML present but vision failed — treat as error, not danger
            return SecurityCheckResult(
                status="error",
                match=False,
                diffs=["Visual extraction failed; cannot verify XML content."],
                facturx=facturx,
                vision=None,
                best=facturx,
            )

        fx_cmp = {k: v for k, v in facturx.items() if k in _COMPARE_FIELDS}
        vi_cmp = {k: v for k, v in vision.items()  if k in _COMPARE_FIELDS}

        diffs = _diff(_normalize(fx_cmp), _normalize(vi_cmp))
        # Ignore null-vs-null non-diffs and fields where one side is simply null
        meaningful = [d for d in diffs if "null" not in d.lower() or ("null" in d.lower() and "null" not in d.split("=")[0])]

        match = len(meaningful) == 0
        return SecurityCheckResult(
            status="ok" if match else "danger",
            match=match,
            diffs=meaningful[:50],
            facturx=facturx,
            vision=vision,
            best=facturx if match else None,
        )

    except Exception as exc:
        return SecurityCheckResult(
            status="error",
            match=False,
            diffs=[f"security_check_error: {type(exc).__name__}: {exc}"],
            facturx=None,
            vision=None,
            best=None,
        )
