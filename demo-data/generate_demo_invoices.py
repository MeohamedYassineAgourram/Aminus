#!/usr/bin/env python3
"""
Generate 10 demo Factur-X invoices in the TechSolutions visual style.
Each invoice is engineered to produce a specific screening outcome:
  - not_yet_paid  (3): XML matches visual, PO is open in ERP
  - checked       (2): XML matches visual, PO already paid in ERP
  - to_be_checked (2): XML matches visual, no matching PO in ERP
  - danger        (3): embedded XML ≠ visual content (tampered invoice)

Run from the Aminus project root:
    python3 demo-data/generate_demo_invoices.py
"""
from __future__ import annotations

import io
import sys
import textwrap
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas as rl_canvas
    from reportlab.lib import colors as rl_colors
except ImportError:
    sys.exit("ERROR: pip3 install reportlab")

try:
    import facturx
except ImportError:
    sys.exit("ERROR: pip3 install factur-x")

# ── Output dir ─────────────────────────────────────────────────────────────────
OUT_DIR = Path(__file__).parent / "invoices"
OUT_DIR.mkdir(exist_ok=True)

# ── Page geometry ──────────────────────────────────────────────────────────────
W, H = A4          # 595.28 × 841.89 pts
LM, RM = 45, 45
CW = W - LM - RM   # ≈ 505 pts

# ── Colour palette ─────────────────────────────────────────────────────────────
RED      = rl_colors.HexColor("#DC2626")
NAVY     = rl_colors.HexColor("#0F172A")
GRAY_LT  = rl_colors.HexColor("#F8FAFC")
GRAY_BD  = rl_colors.HexColor("#CBD5E1")
GRAY_TXT = rl_colors.HexColor("#64748B")
WHITE    = rl_colors.white
BLACK    = rl_colors.black

# ── Buyer (constant across all invoices) ──────────────────────────────────────
BUYER = {
    "name":    "Innovate Corp SARL",
    "address": "45 Avenue des Champs-Élysées",
    "city":    "75008 Paris",
    "country": "France",
    "vat":     "FR98765432109",
}

def _eur(v: float) -> str:
    return f"{v:,.2f}"


# ══════════════════════════════════════════════════════════════════════════════
#  INVOICE DATA
#  Each entry:
#    filename      – output PDF name
#    expected      – human label (not used by code, just documentation)
#    seller        – visible seller block
#    meta          – invoice header fields
#    items         – list of (description, qty, unit, unit_price_ht)
#    visual_ht     – override total HT shown in the visual (danger cases)
#    visual_iban   – override IBAN shown in the visual (danger cases)
#    xml_ht        – amount that goes into the embedded XML (if different from visual)
#    xml_iban      – IBAN that goes into the embedded XML (if different from visual)
# ══════════════════════════════════════════════════════════════════════════════
INVOICES: List[Dict] = [

    # ── 1 · not_yet_paid ──────────────────────────────────────────────────────
    # CloudStack SARL, PO-2025-006, €9 900 HT open
    {
        "filename": "01_cloudstack_not_yet_paid.pdf",
        "expected": "not_yet_paid",
        "seller": {
            "name":   "CloudStack SARL",
            "address":"1 Place de la Bourse",
            "city":   "75009 Paris",
            "vat":    "FR33221100998",
            "siret":  "789 123 456 00078",
            "email":  "afontaine@cloudstack.fr",
            "iban":   "FR7614508959032913461111",
            "bic":    "CMCIFRPPXXX",
        },
        "meta": {
            "invoice_number": "INV-2025-CLK-001",
            "issue_date":     "2025-03-01",
            "due_date":       "2025-03-31",
            "po_ref":         "PO-2025-006",
            "payment_terms":  "Net 30 days",
        },
        "items": [
            ("Cloud Infrastructure – Annual License",    1,  "unit", 7500.00),
            ("DevOps Support & Monitoring",             12,  "hour",  200.00),
        ],
    },

    # ── 2 · not_yet_paid ──────────────────────────────────────────────────────
    # Acme Supplies SAS, PO-2025-001, €12 500 HT open
    {
        "filename": "02_acme_supplies_not_yet_paid.pdf",
        "expected": "not_yet_paid",
        "seller": {
            "name":   "Acme Supplies SAS",
            "address":"3 Avenue Hoche",
            "city":   "69002 Lyon",
            "vat":    "FR98765432101",
            "siret":  "456 789 123 00045",
            "email":  "jbernard@acme-supplies.fr",
            "iban":   "FR7614508959032913463358",
            "bic":    "BNPAFRPPXXX",
        },
        "meta": {
            "invoice_number": "FAC-2025-AS-0447",
            "issue_date":     "2025-04-02",
            "due_date":       "2025-05-17",
            "po_ref":         "PO-2025-001",
            "payment_terms":  "Net 45 days",
        },
        "items": [
            ("Office Furniture – Executive Desk Set",   5, "unit", 1200.00),
            ("Office Supplies – Quarterly Pack",       50, "unit",   80.00),
            ("HP 950XL Printer Cartridges (box ×25)",   1, "unit", 2500.00),
        ],
    },

    # ── 3 · not_yet_paid ──────────────────────────────────────────────────────
    # Logistics Express, PO-2025-004, €7 650 HT open
    {
        "filename": "03_logistics_express_not_yet_paid.pdf",
        "expected": "not_yet_paid",
        "seller": {
            "name":   "Logistics Express",
            "address":"8 Quai de la Rapée",
            "city":   "13002 Marseille",
            "vat":    "FR44556677889",
            "siret":  "567 891 234 00056",
            "email":  "slegrand@logisticsexpress.fr",
            "iban":   "FR7614508959032913463399",
            "bic":    "CEPAFRPP",
        },
        "meta": {
            "invoice_number": "LX-2025-0981",
            "issue_date":     "2025-03-18",
            "due_date":       "2025-04-02",
            "po_ref":         "PO-2025-004",
            "payment_terms":  "Net 15 days",
        },
        "items": [
            ("Express Freight Paris – Marseille (route A7)",  1, "unit", 5250.00),
            ("Handling & Packaging",                          1, "unit",  950.00),
            ("Fuel Surcharge",                                1, "unit", 1450.00),
        ],
    },

    # ── 4 · checked (already_paid) ────────────────────────────────────────────
    # Bureau Martin & Fils, PO-2025-003, paid 2025-02-10
    {
        "filename": "04_bureau_martin_already_paid.pdf",
        "expected": "checked",
        "seller": {
            "name":   "Bureau Martin & Fils",
            "address":"55 Boulevard Voltaire",
            "city":   "33000 Bordeaux",
            "vat":    "FR11223344556",
            "siret":  "234 567 891 00023",
            "email":  "pmartin@bureau-martin.fr",
            "iban":   "FR7630006000011234567890",
            "bic":    "BPCEFRPPXXX",
        },
        "meta": {
            "invoice_number": "FAC-2025-0312",
            "issue_date":     "2025-01-20",
            "due_date":       "2025-02-19",
            "po_ref":         "PO-2025-003",
            "payment_terms":  "Net 30 days",
        },
        "items": [
            ("Office Furniture – Standing Desk (sit-stand)", 2, "unit", 1200.00),
            ("Ergonomic Chair Premium",                      3, "unit",  800.00),
        ],
    },

    # ── 5 · checked (already_paid) ────────────────────────────────────────────
    # Imprimerie Dubois, PO-2025-007, paid 2025-03-05  (re-sent duplicate)
    {
        "filename": "05_imprimerie_dubois_duplicate.pdf",
        "expected": "checked",
        "seller": {
            "name":   "Imprimerie Dubois",
            "address":"12 Rue Gutenberg",
            "city":   "67000 Strasbourg",
            "vat":    "FR22334455667",
            "siret":  "891 234 567 00089",
            "email":  "rdubois@imprimerie-dubois.fr",
            "iban":   "FR7630004000031234567812",
            "bic":    "SOGEFRPP",
        },
        "meta": {
            "invoice_number": "FAC-2025-0789",
            "issue_date":     "2025-04-01",
            "due_date":       "2025-05-01",
            "po_ref":         "PO-2025-007",
            "payment_terms":  "Net 30 days",
        },
        "items": [
            ("Business Cards – Premium 400gsm (1 000 pcs)", 1, "unit",  350.00),
            ("Company Brochures A4 glossy (500 pcs)",       1, "unit",  600.00),
            ("Letterhead Paper – Laid 90g (ream 500 fls)",  1, "unit",  400.00),
        ],
    },

    # ── 6 · to_be_checked (unknown vendor, no PO) ─────────────────────────────
    {
        "filename": "06_horizon_digital_unknown_vendor.pdf",
        "expected": "to_be_checked",
        "seller": {
            "name":   "Horizon Digital Services",
            "address":"22 Rue du Faubourg Saint-Honoré",
            "city":   "75008 Paris",
            "vat":    "FR55443322110",
            "siret":  "999 888 777 00001",
            "email":  "contact@horizon-digital.fr",
            "iban":   "FR7612739000305000999888",
            "bic":    "BNPAFRPPXXX",
        },
        "meta": {
            "invoice_number": "HDS-2025-0042",
            "issue_date":     "2025-04-10",
            "due_date":       "2025-05-10",
            "po_ref":         "N/A",
            "payment_terms":  "Net 30 days",
        },
        "items": [
            ("SEO & Content Marketing Strategy",         1, "unit", 4500.00),
            ("Social Media Management – April 2025",     1, "month", 2000.00),
            ("Paid Advertising Campaign Setup",          1, "unit", 1900.00),
        ],
    },

    # ── 7 · to_be_checked (PO exists but amount is way off) ───────────────────
    # Conseil & Stratégie, PO-2025-009 = €22 000 HT, but invoice claims €30 000 HT
    {
        "filename": "07_conseil_strategie_amount_mismatch.pdf",
        "expected": "to_be_checked",
        "seller": {
            "name":   "Conseil & Stratégie",
            "address":"7 Avenue de l'Opéra",
            "city":   "75001 Paris",
            "vat":    "FR66778899001",
            "siret":  "123 456 789 01234",
            "email":  "cvidal@conseil-strategie.fr",
            "iban":   "FR7614208009012345678901",
            "bic":    "AGRIFRPPXXX",
        },
        "meta": {
            "invoice_number": "CS-2025-0198",
            "issue_date":     "2025-04-15",
            "due_date":       "2025-06-14",
            "po_ref":         "PO-2025-009",
            "payment_terms":  "Net 60 days",
        },
        "items": [
            ("Strategic Advisory Mission – Q2 2025", 20, "day", 1500.00),
        ],
    },

    # ── 8 · danger (amount tampered in visual) ────────────────────────────────
    # TechNord SARL: XML = €38 200 HT / €45 840 TTC (correct PO amount)
    #                visual = €51 600 HT / €61 920 TTC (inflated by attacker)
    {
        "filename": "08_technord_danger_amount_tampered.pdf",
        "expected": "danger",
        "seller": {
            "name":   "TechNord SARL",
            "address":"Musterstraße 12",
            "city":   "10115 Berlin",
            "vat":    "DE123456789",
            "siret":  "N/A",
            "email":  "hmuller@technord.de",
            "iban":   "DE89370400440532013000",
            "bic":    "DEUTDEDBXXX",
        },
        "meta": {
            "invoice_number": "TN-2025-INV-0088",
            "issue_date":     "2025-04-01",
            "due_date":       "2025-05-01",
            "po_ref":         "PO-2025-002",
            "payment_terms":  "Net 30 days",
        },
        # Visual: 3 items totalling 51 600 HT (inflated)
        "items": [
            ("Server Hardware – Dell PowerEdge R740 (×3)", 3, "unit", 12000.00),
            ("Network Switches – Cisco 48-port (×2)",      2, "unit",  5400.00),
            ("Installation & On-site Configuration",       3, "day",   1600.00),
        ],
        # What the EMBEDDED XML will say (original correct amounts)
        "xml_ht":   38200.00,
        "xml_iban": "DE89370400440532013000",
    },

    # ── 9 · danger (IBAN swapped in visual) ───────────────────────────────────
    # Maintenance Pro: XML = correct IBAN FR7614508959032913462222
    #                  visual = fraudulent IBAN FR7612739000305001234567
    {
        "filename": "09_maintenance_pro_danger_iban_fraud.pdf",
        "expected": "danger",
        "seller": {
            "name":   "Maintenance Pro",
            "address":"44 Rue du Faubourg Saint-Antoine",
            "city":   "75011 Paris",
            "vat":    "FR55443322110",
            "siret":  "912 345 678 00091",
            "email":  "mlefevre@maintenancepro.fr",
            # Visual shows fraudulent IBAN (attacker swapped payment destination)
            "iban":   "FR7612739000305001234567",
            "bic":    "BNPAFRPPXXX",
        },
        "meta": {
            "invoice_number": "MP-2025-0334",
            "issue_date":     "2025-04-05",
            "due_date":       "2025-05-05",
            "po_ref":         "PO-2025-008",
            "payment_terms":  "Net 30 days",
        },
        "items": [
            ("HVAC System Maintenance – Q1 2025",    1, "unit", 2800.00),
            ("Electrical Inspection & Repairs",      1, "unit", 1500.00),
            ("Plumbing Works – Building B",          1, "unit", 1200.00),
        ],
        # Embedded XML has the CORRECT (original) IBAN
        "xml_iban": "FR7614508959032913462222",
    },

    # ── 10 · danger (total amount tampered in visual) ─────────────────────────
    # Securitas France: XML = €2 100 HT / €2 520 TTC (partial PO amount)
    #                   visual = €3 500 HT / €4 200 TTC (inflated)
    {
        "filename": "10_securitas_danger_total_tampered.pdf",
        "expected": "danger",
        "seller": {
            "name":   "Securitas France",
            "address":"20 Rue de Rivoli",
            "city":   "75001 Paris",
            "vat":    "FR99887766554",
            "siret":  "678 912 345 00067",
            "email":  "lmoreau@securitas.fr",
            "iban":   "FR7610107001011234567890",
            "bic":    "BNPAFRPPXXX",
        },
        "meta": {
            "invoice_number": "SEC-2025-B2",
            "issue_date":     "2025-04-01",
            "due_date":       "2025-05-01",
            "po_ref":         "PO-2025-005",
            "payment_terms":  "Net 30 days",
        },
        # Visual items total 3 500 HT (inflated)
        "items": [
            ("Security Personnel Service – Zone A+B April 2025", 1, "month", 2800.00),
            ("Control Room Access & Remote Monitoring",          1, "unit",   700.00),
        ],
        # Embedded XML says the real original amount
        "xml_ht": 2100.00,
    },
]


# ══════════════════════════════════════════════════════════════════════════════
#  DRAW INVOICE (reportlab canvas)
# ══════════════════════════════════════════════════════════════════════════════
def draw_invoice(buf: io.BytesIO, inv: Dict) -> None:
    seller = inv["seller"]
    meta   = inv["meta"]
    items  = inv["items"]

    # Visual amounts (what Claude will see)
    vis_ht   = inv.get("visual_ht") or round(sum(q * p for _, q, _, p in items), 2)
    vis_vat  = round(vis_ht * 0.20, 2)
    vis_ttc  = round(vis_ht * 1.20, 2)
    vis_iban = inv.get("visual_iban", seller["iban"])

    c = rl_canvas.Canvas(buf, pagesize=A4)

    # ── HEADER ────────────────────────────────────────────────────────────────
    # "INVOICE" title
    c.setFillColor(RED)
    c.setFont("Helvetica-Bold", 52)
    c.drawString(LM, 762, "INVOICE")

    # Seller info block (top-right)
    c.setFont("Helvetica-Bold", 9.5)
    c.setFillColor(BLACK)
    c.drawRightString(W - RM, 802, seller["name"])

    c.setFont("Helvetica", 8.5)
    c.setFillColor(GRAY_TXT)
    ry = 788
    for line in [seller["address"], seller["city"],
                 f"VAT: {seller['vat']}", f"SIRET: {seller['siret']}"]:
        c.drawRightString(W - RM, ry, line)
        ry -= 12
    c.setFillColor(RED)
    c.drawRightString(W - RM, ry, seller["email"])

    # ── HORIZONTAL RULE ───────────────────────────────────────────────────────
    c.setStrokeColor(GRAY_BD)
    c.setLineWidth(0.5)
    c.line(LM, 738, W - RM, 738)

    # ── INFO CELLS ────────────────────────────────────────────────────────────
    cells = [
        ("Invoice No.",  meta["invoice_number"]),
        ("Issue Date",   meta["issue_date"]),
        ("Due Date",     meta["due_date"]),
        ("Currency",     "EUR"),
        ("Order Ref.",   meta["po_ref"]),
    ]
    cell_w = CW / 5
    cx = LM
    for label, value in cells:
        c.setFont("Helvetica", 7.5)
        c.setFillColor(GRAY_TXT)
        c.drawString(cx + 4, 722, label)
        c.setFont("Helvetica-Bold", 9)
        c.setFillColor(BLACK)
        c.drawString(cx + 4, 708, value)
        cx += cell_w

    # ── SEPARATOR ─────────────────────────────────────────────────────────────
    c.setStrokeColor(GRAY_BD)
    c.line(LM, 694, W - RM, 694)

    # ── FROM / TO ─────────────────────────────────────────────────────────────
    half = CW / 2

    c.setFont("Helvetica-Bold", 8)
    c.setFillColor(RED)
    c.drawString(LM, 678, "FROM")
    c.drawString(LM + half + 15, 678, "TO")

    # FROM block
    fy = 663
    c.setFont("Helvetica-Bold", 10)
    c.setFillColor(BLACK)
    c.drawString(LM, fy, seller["name"])

    c.setFont("Helvetica", 9)
    c.setFillColor(GRAY_TXT)
    for line in [seller["address"], seller["city"], "France"]:
        fy -= 13
        c.drawString(LM, fy, line)

    fy -= 16
    c.setFont("Helvetica", 9)
    c.setFillColor(BLACK)
    c.drawString(LM, fy, f"IBAN: {vis_iban}")
    fy -= 13
    c.drawString(LM, fy, f"BIC: {seller['bic']}")

    # TO block
    bx = LM + half + 15
    by = 663
    c.setFont("Helvetica-Bold", 10)
    c.setFillColor(BLACK)
    c.drawString(bx, by, BUYER["name"])

    c.setFont("Helvetica", 9)
    c.setFillColor(GRAY_TXT)
    for line in [BUYER["address"], BUYER["city"], BUYER["country"]]:
        by -= 13
        c.drawString(bx, by, line)

    c.setFont("Helvetica", 9)
    c.setFillColor(BLACK)
    by -= 16
    c.drawString(bx, by, f"VAT: {BUYER['vat']}")

    # ── LINE ITEMS TABLE ──────────────────────────────────────────────────────
    table_top = 576

    # Header background
    c.setFillColor(NAVY)
    c.rect(LM, table_top - 20, CW, 22, fill=1, stroke=0)

    # Column x-positions and widths
    COL = {
        "#":             (LM + 4,    24),
        "Description":   (LM + 30,  242),
        "Qty":           (LM + 275,  38),
        "Unit":          (LM + 316,  38),
        "Unit Price":    (LM + 357,  70),
        "VAT %":         (LM + 430,  30),
        "Amount HT":     (LM + 463,  CW - (463 - LM + 2)),
    }

    # Header labels
    c.setFont("Helvetica-Bold", 8)
    c.setFillColor(WHITE)
    hdrs = [
        (COL["#"][0],           "# "),
        (COL["Description"][0], "Description"),
        (COL["Qty"][0],         "Qty"),
        (COL["Unit"][0],        "Unit"),
        (COL["Unit Price"][0],  "Unit Price (€)"),
        (COL["VAT %"][0],       "VAT %"),
        (COL["Amount HT"][0],   "Amount HT (€)"),
    ]
    for hx, htxt in hdrs:
        c.drawString(hx, table_top - 13, htxt)

    # Rows
    row_y = table_top - 20
    for idx, (desc, qty, unit, unit_price) in enumerate(items):
        amount = qty * unit_price
        row_y -= 22

        if idx % 2 == 1:
            c.setFillColor(GRAY_LT)
            c.rect(LM, row_y, CW, 22, fill=1, stroke=0)

        c.setFont("Helvetica", 9)
        c.setFillColor(BLACK)
        c.drawString(COL["#"][0],           row_y + 7, str(idx + 1))
        # Truncate long descriptions
        d = desc if len(desc) <= 48 else desc[:45] + "..."
        c.drawString(COL["Description"][0], row_y + 7, d)
        c.drawCentredString(COL["Qty"][0] + 16,  row_y + 7, str(qty))
        c.drawCentredString(COL["Unit"][0] + 16, row_y + 7, unit)
        c.drawRightString(COL["Unit Price"][0] + COL["Unit Price"][1], row_y + 7, _eur(unit_price))
        c.drawCentredString(COL["VAT %"][0] + 14, row_y + 7, "20%")
        c.drawRightString(W - RM - 2, row_y + 7, _eur(amount))

    table_bottom = row_y

    # Table bottom border
    c.setStrokeColor(GRAY_BD)
    c.setLineWidth(0.5)
    c.line(LM, table_bottom, W - RM, table_bottom)

    # ── TOTALS ────────────────────────────────────────────────────────────────
    tot_y = table_bottom - 22
    label_x = W - RM - 165
    value_x = W - RM

    c.setFont("Helvetica", 9)
    c.setFillColor(GRAY_TXT)
    c.drawString(label_x, tot_y, "Subtotal HT:")
    c.setFillColor(BLACK)
    c.drawRightString(value_x, tot_y, f"€ {_eur(vis_ht)}")

    tot_y -= 17
    c.setFillColor(GRAY_TXT)
    c.drawString(label_x, tot_y, "TVA (20%):")
    c.setFillColor(BLACK)
    c.drawRightString(value_x, tot_y, f"€ {_eur(vis_vat)}")

    tot_y -= 10
    c.setFillColor(NAVY)
    c.rect(label_x - 8, tot_y - 18, value_x - label_x + 18, 24, fill=1, stroke=0)
    c.setFont("Helvetica-Bold", 10)
    c.setFillColor(WHITE)
    c.drawString(label_x, tot_y - 11, "TOTAL TTC:")
    c.drawRightString(value_x, tot_y - 11, f"€ {_eur(vis_ttc)}")

    # ── SEPARATOR ─────────────────────────────────────────────────────────────
    sep_y = tot_y - 35
    c.setStrokeColor(GRAY_BD)
    c.setLineWidth(0.5)
    c.line(LM, sep_y, W - RM, sep_y)

    # ── PAYMENT TERMS LINE ────────────────────────────────────────────────────
    pt_y = sep_y - 14
    terms  = meta.get("payment_terms", "Net 30 days")
    pt_line = f"Payment Terms: {terms}  |  IBAN: {vis_iban}  |  BIC: {seller['bic']}"
    c.setFont("Helvetica-Bold", 8)
    c.setFillColor(BLACK)
    c.drawString(LM, pt_y, pt_line)

    c.setFont("Helvetica", 8)
    c.setFillColor(GRAY_TXT)
    c.drawString(LM, pt_y - 14, "Thank you for your business. Payment due within the agreed terms from invoice date.")

    # ── FOOTER BANNER ─────────────────────────────────────────────────────────
    footer_text = (
        "Factur-X EN 16931 — This document is a structured electronic invoice compliant "
        "with the European standard EN 16931. Machine-readable XML data is embedded within this PDF."
    )
    lines = textwrap.wrap(footer_text, width=108)
    banner_h = 14 + len(lines) * 11
    c.setFillColor(RED)
    c.rect(LM - 5, 30, W - LM - RM + 10, banner_h, fill=1, stroke=0)
    c.setFont("Helvetica", 7.5)
    c.setFillColor(WHITE)
    fy = 30 + banner_h - 11
    for ln in lines:
        c.drawString(LM, fy, ln)
        fy -= 11

    c.save()


# ══════════════════════════════════════════════════════════════════════════════
#  BUILD FACTUR-X XML
# ══════════════════════════════════════════════════════════════════════════════
def _xe(s: str) -> str:
    """Escape special characters for XML text content."""
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;").replace("'", "&apos;")


def build_xml(inv: Dict) -> bytes:
    seller = inv["seller"]
    meta   = inv["meta"]
    items  = inv["items"]

    # XML amounts — may differ from visual for danger cases
    xml_ht   = inv.get("xml_ht") or round(sum(q * p for _, q, _, p in items), 2)
    xml_vat  = round(xml_ht * 0.20, 2)
    xml_ttc  = round(xml_ht * 1.20, 2)
    xml_iban = inv.get("xml_iban", seller["iban"])

    # Date to YYYYMMDD
    d = meta["issue_date"].replace("-", "")

    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<rsm:CrossIndustryInvoice
    xmlns:rsm="urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100"
    xmlns:ram="urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100"
    xmlns:udt="urn:un:unece:uncefact:data:standard:UnqualifiedDataType:100">
  <rsm:ExchangedDocumentContext>
    <ram:GuidelineSpecifiedDocumentContextParameter>
      <ram:ID>urn:factur-x:pdfa:CrossIndustryDocument:invoice:1p0:minimum</ram:ID>
    </ram:GuidelineSpecifiedDocumentContextParameter>
  </rsm:ExchangedDocumentContext>
  <rsm:ExchangedDocument>
    <ram:ID>{_xe(meta["invoice_number"])}</ram:ID>
    <ram:TypeCode>380</ram:TypeCode>
    <ram:IssueDateTime>
      <udt:DateTimeString format="102">{d}</udt:DateTimeString>
    </ram:IssueDateTime>
  </rsm:ExchangedDocument>
  <rsm:SupplyChainTradeTransaction>
    <ram:ApplicableHeaderTradeAgreement>
      <ram:SellerTradeParty>
        <ram:Name>{_xe(seller["name"])}</ram:Name>
        <ram:SpecifiedLegalOrganization>
          <ram:ID schemeID="0002">{_xe(seller["siret"].replace(" ", "").replace(" ", ""))}</ram:ID>
        </ram:SpecifiedLegalOrganization>
      </ram:SellerTradeParty>
      <ram:BuyerTradeParty>
        <ram:Name>{_xe(BUYER["name"])}</ram:Name>
      </ram:BuyerTradeParty>
    </ram:ApplicableHeaderTradeAgreement>
    <ram:ApplicableHeaderTradeDelivery/>
    <ram:ApplicableHeaderTradeSettlement>
      <ram:CreditorFinancialAccount>
        <ram:IBANID>{xml_iban}</ram:IBANID>
      </ram:CreditorFinancialAccount>
      <ram:InvoiceCurrencyCode>EUR</ram:InvoiceCurrencyCode>
      <ram:SpecifiedTradeSettlementHeaderMonetarySummation>
        <ram:TaxBasisTotalAmount>{xml_ht:.2f}</ram:TaxBasisTotalAmount>
        <ram:TaxTotalAmount>{xml_vat:.2f}</ram:TaxTotalAmount>
        <ram:GrandTotalAmount>{xml_ttc:.2f}</ram:GrandTotalAmount>
        <ram:DuePayableAmount>{xml_ttc:.2f}</ram:DuePayableAmount>
      </ram:SpecifiedTradeSettlementHeaderMonetarySummation>
    </ram:ApplicableHeaderTradeSettlement>
  </rsm:SupplyChainTradeTransaction>
</rsm:CrossIndustryInvoice>"""
    return xml.encode("utf-8")


# ══════════════════════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════════════════════
def main() -> None:
    ok = 0
    for inv in INVOICES:
        out_path = OUT_DIR / inv["filename"]
        try:
            # 1. Render visual PDF
            pdf_buf = io.BytesIO()
            draw_invoice(pdf_buf, inv)
            pdf_bytes = pdf_buf.getvalue()

            # 2. Build Factur-X XML
            xml_bytes = build_xml(inv)

            # 3. Embed XML into PDF
            result = facturx.generate_from_binary(
                pdf_bytes,
                xml_bytes,
                flavor="factur-x",
                level="autodetect",
                check_xsd=False,
                check_schematron=False,
            )

            out_path.write_bytes(result)
            vis_ht  = inv.get("visual_ht") or round(sum(q * p for _, q, _, p in inv["items"]), 2)
            xml_ht  = inv.get("xml_ht",  vis_ht)
            mismatch = " ⚠ XML≠visual" if (inv.get("xml_ht") or inv.get("xml_iban")) else ""
            print(f"  ✓  [{inv['expected']:14s}]  {inv['filename']}{mismatch}")
            ok += 1
        except Exception as exc:
            print(f"  ✗  [{inv.get('expected','?'):14s}]  {inv['filename']}  ERROR: {exc}")

    print(f"\nGenerated {ok}/{len(INVOICES)} invoices → {OUT_DIR}/")


if __name__ == "__main__":
    main()
