#!/usr/bin/env python3
"""Generate PDF fixtures from Factur-X XML fixtures.

Behavior:
- If python package `facturx` is available, generate real Factur-X hybrid PDFs.
- If unavailable, generate deterministic placeholder PDFs and a report explaining
  the fallback, so test pipelines can still run with explicit visibility.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import tempfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Optional, Tuple


@dataclass
class BuildResult:
    xml_file: str
    pdf_file: str
    mode: str
    ok: bool
    reason: str


def _extract_fields(xml_path: Path) -> Tuple[str, str, str, str]:
    ns = {
        "rsm": "urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100",
        "ram": "urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100",
    }
    tree = ET.parse(xml_path)
    root = tree.getroot()

    invoice_id = root.findtext(".//ram:ID", default="UNKNOWN", namespaces=ns)
    seller = root.findtext(".//ram:SellerTradeParty/ram:Name", default="UNKNOWN SELLER", namespaces=ns)
    total = root.findtext(
        ".//ram:SpecifiedTradeSettlementHeaderMonetarySummation/ram:GrandTotalAmount",
        default="0.00",
        namespaces=ns,
    )
    due = root.findtext(
        ".//ram:SpecifiedTradeSettlementHeaderMonetarySummation/ram:DuePayableAmount",
        default=total,
        namespaces=ns,
    )
    return invoice_id.strip(), seller.strip(), total.strip(), due.strip()


def _escape_pdf_text(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _build_simple_pdf(lines: List[str], out_path: Path) -> None:
    content_lines = ["BT", "/F1 12 Tf", "50 770 Td"]
    for idx, line in enumerate(lines):
        if idx > 0:
            content_lines.append("0 -18 Td")
        content_lines.append(f"({_escape_pdf_text(line)}) Tj")
    content_lines.append("ET")
    stream = "\n".join(content_lines).encode("latin-1", errors="replace")

    objects: List[bytes] = []
    objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    objects.append(b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>")
    objects.append(
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
        b"/Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>"
    )
    objects.append(b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n" + stream + b"\nendstream")
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")

    out = bytearray()
    out.extend(b"%PDF-1.4\n")
    offsets = [0]
    for i, obj in enumerate(objects, start=1):
        offsets.append(len(out))
        out.extend(f"{i} 0 obj\n".encode("ascii"))
        out.extend(obj)
        out.extend(b"\nendobj\n")

    xref_pos = len(out)
    out.extend(f"xref\n0 {len(objects)+1}\n".encode("ascii"))
    out.extend(b"0000000000 65535 f \n")
    for off in offsets[1:]:
        out.extend(f"{off:010d} 00000 n \n".encode("ascii"))
    out.extend(
        (
            "trailer\n"
            f"<< /Size {len(objects)+1} /Root 1 0 R >>\n"
            "startxref\n"
            f"{xref_pos}\n"
            "%%EOF\n"
        ).encode("ascii")
    )
    out_path.write_bytes(out)


def _try_generate_with_facturx(base_pdf: Path, xml_file: Path, out_pdf: Path) -> Tuple[bool, str]:
    try:
        import facturx  # type: ignore
    except Exception as exc:
        return False, f"facturx import unavailable: {type(exc).__name__}: {exc}"

    candidates = [
        {"kwargs": {"output_pdf_file": str(out_pdf)}},
        {"kwargs": {"output_pdf_file": out_pdf}},
        {"kwargs": {}},
    ]

    fn = getattr(facturx, "generate_facturx_from_file", None)
    if fn is None:
        return False, "facturx.generate_facturx_from_file not found"

    last_err = "unknown error"
    for candidate in candidates:
        try:
            kwargs = candidate["kwargs"]
            result = fn(str(base_pdf), str(xml_file), **kwargs)
            if not out_pdf.exists():
                if isinstance(result, (bytes, bytearray)):
                    out_pdf.write_bytes(bytes(result))
                elif result is None and not kwargs:
                    # Some versions may overwrite the input PDF in place.
                    shutil.copy2(base_pdf, out_pdf)
                elif isinstance(result, str) and Path(result).exists():
                    shutil.copy2(result, out_pdf)
            if out_pdf.exists() and out_pdf.stat().st_size > 0:
                return True, "generated with facturx"
        except Exception as exc:
            last_err = f"{type(exc).__name__}: {exc}"
    return False, f"facturx generation failed: {last_err}"


def build(xml_dir: Path, out_dir: Path) -> List[BuildResult]:
    out_dir.mkdir(parents=True, exist_ok=True)
    results: List[BuildResult] = []

    xml_files = sorted(xml_dir.glob("*.xml"))
    for xml_file in xml_files:
        invoice_id, seller, total, due = _extract_fields(xml_file)
        out_pdf = out_dir / f"{xml_file.stem}.pdf"

        with tempfile.TemporaryDirectory(prefix="facturx_build_") as tmp:
            base_pdf = Path(tmp) / "base.pdf"
            lines = [
                "Aegis Orchestrator Test Invoice",
                f"Source XML: {xml_file.name}",
                f"Invoice ID: {invoice_id}",
                f"Seller: {seller}",
                f"Grand Total: {total}",
                f"Due Amount: {due}",
            ]
            _build_simple_pdf(lines, base_pdf)

            ok, reason = _try_generate_with_facturx(base_pdf, xml_file, out_pdf)
            if ok:
                results.append(
                    BuildResult(
                        xml_file=str(xml_file),
                        pdf_file=str(out_pdf),
                        mode="real_facturx",
                        ok=True,
                        reason=reason,
                    )
                )
            else:
                # Deterministic fallback for environments without facturx package.
                shutil.copy2(base_pdf, out_pdf)
                results.append(
                    BuildResult(
                        xml_file=str(xml_file),
                        pdf_file=str(out_pdf),
                        mode="fallback_pdf",
                        ok=False,
                        reason=reason,
                    )
                )

    return results


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate Factur-X PDFs from XML fixtures")
    parser.add_argument(
        "--xml-dir",
        default="demo-data/facturx-tests/invoices",
        help="Directory containing .xml fixtures",
    )
    parser.add_argument(
        "--output-dir",
        default="demo-data/facturx-tests/generated-pdfs",
        help="Output directory for generated PDFs",
    )
    parser.add_argument(
        "--report",
        default="demo-data/facturx-tests/generated-pdfs/build-report.json",
        help="Path to JSON build report",
    )

    args = parser.parse_args()
    xml_dir = Path(args.xml_dir)
    out_dir = Path(args.output_dir)
    report_path = Path(args.report)

    if not xml_dir.exists():
        raise SystemExit(f"XML directory not found: {xml_dir}")

    results = build(xml_dir, out_dir)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps([asdict(r) for r in results], indent=2), encoding="utf-8")

    real_count = sum(1 for r in results if r.mode == "real_facturx" and r.ok)
    fallback_count = sum(1 for r in results if r.mode == "fallback_pdf")
    print(f"Generated {len(results)} files: real_facturx={real_count}, fallback_pdf={fallback_count}")
    print(f"Report: {report_path}")

    # Exit with 0 to keep CI/dev flow usable even in fallback mode.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
