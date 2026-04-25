# Aegis Orchestrator - Factur-X Test Fixtures

This folder contains deterministic fixtures for the test cases you listed.

## Important

- Files in `invoices/` are Factur-X XML payloads (CII profile), not hybrid PDF/A-3 files.
- For end-to-end upload tests, embed each XML as `factur-x.xml` inside a PDF/A-3 invoice.
- `non-facturx/` and `malware/` contain negative security inputs.

## Build Hybrid PDFs

Use the generator script:

```bash
python3 demo-data/facturx-tests/scripts/generate_facturx_pdfs.py
```

Outputs are written to:

- `generated-pdfs/*.pdf`
- `generated-pdfs/build-report.json`

Generation modes:

- `real_facturx`: true hybrid Factur-X PDF generated with python package `facturx`.
- `fallback_pdf`: deterministic placeholder PDF used when `facturx` is unavailable.

If your environment has `pip`, install dependencies then re-run:

```bash
python3 -m pip install factur-x reportlab
python3 demo-data/facturx-tests/scripts/generate_facturx_pdfs.py
```

## Mapping to Test Cases

- TC-SEC-01 -> `invoices/TC-SEC-01_valid_facturx.xml`
- TC-SEC-02 -> `invoices/TC-SEC-02_mismatch_xml_100_visual_1000.xml`
- TC-SEC-03 -> `non-facturx/TC-SEC-03_standard_pdf_placeholder.pdf`
- TC-SEC-04 -> `malware/TC-SEC-04_EICAR.txt`
- TC-SEC-05 -> `invoices/TC-SEC-05_xml_script_injection.xml`
- TC-REC-01 -> `invoices/TC-REC-01_po_match_500.xml`
- TC-REC-02 -> `invoices/TC-REC-02_duplicate_A_original.xml` and `invoices/TC-REC-02_duplicate_A_copy.xml`
- TC-REC-03 -> `invoices/TC-REC-03_amount_discrepancy_600.xml`
- TC-REC-04 -> `invoices/TC-REC-04_unknown_vendor.xml`
- TC-REC-05 -> `invoices/TC-REC-05_partial_payment_1000.xml`
- TC-AGT-01 -> `invoices/TC-AGT-01_inconsistent_data.xml`
- TC-LEG-02 -> `invoices/TC-LEG-02_vat_error.xml`

## Email Edge Cases

See `email-fixtures/` for JSON manifests covering:

- Noise filtering with mixed attachments
- Multiple separate invoices in one email
- Email without invoice attachment

## Recommended behavior for noise filtering

Aegis should not analyze every attachment. Use a strict staged filter:

1. Accept only PDF and XML MIME types.
2. Detect Factur-X signature (`factur-x.xml` embedded in PDF/A-3 or CII XML context).
3. Ignore unrelated attachments (PNG, logo, terms, ads) without marking Danger.
4. Mark Danger only when a candidate invoice file fails validation or has tampering signals.
