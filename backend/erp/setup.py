"""
Run once to create and seed the simulated ERP tables:
  erp_vendors, erp_payments, erp_emails

Usage:
    python3 -m backend.erp.setup
"""

import os
import sys

try:
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))
except Exception:
    pass

DDL = """
-- ── Vendor master ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS erp_vendors (
    id              SERIAL PRIMARY KEY,
    vendor_name     TEXT NOT NULL,
    vendor_iban     TEXT,
    vat_number      TEXT,
    siret           TEXT,
    address         TEXT,
    city            TEXT,
    postal_code     TEXT,
    country         TEXT DEFAULT 'FR',
    contact_name    TEXT,
    contact_email   TEXT,
    payment_terms   TEXT DEFAULT 'NET30',
    category        TEXT,
    status          TEXT DEFAULT 'active',  -- active | suspended | blocked
    trust_score     INTEGER DEFAULT 3,       -- 1 (low) .. 5 (high)
    notes           TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ── Payment history ───────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS erp_payments (
    id              SERIAL PRIMARY KEY,
    po_number       TEXT REFERENCES erp_purchase_orders(po_number) ON DELETE SET NULL,
    vendor_name     TEXT NOT NULL,
    invoice_ref     TEXT,
    amount_paid     NUMERIC(12,2) NOT NULL,
    currency        TEXT DEFAULT 'EUR',
    payment_date    DATE NOT NULL,
    bank_ref        TEXT,
    payment_method  TEXT DEFAULT 'virement',  -- virement | cheque | prelevement
    notes           TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ── Email threads ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS erp_emails (
    id              SERIAL PRIMARY KEY,
    thread_id       TEXT NOT NULL,
    subject         TEXT NOT NULL,
    vendor_name     TEXT,
    from_email      TEXT NOT NULL,
    to_email        TEXT NOT NULL,
    sent_at         TIMESTAMPTZ NOT NULL,
    body            TEXT NOT NULL,
    po_ref          TEXT,
    invoice_ref     TEXT,
    thread_type     TEXT DEFAULT 'general',  -- invoice | dispute | reminder | onboarding | general
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
"""

SEED_VENDORS = """
INSERT INTO erp_vendors
    (vendor_name, vendor_iban, vat_number, siret, address, city, postal_code,
     contact_name, contact_email, payment_terms, category, status, trust_score, notes)
VALUES
-- TechSolutions SAS (matched PO-2024-8871)
('TechSolutions SAS',
 'FR7630004000031234567890143',
 'FR12345678901',
 '34587891200034',
 '14 rue de la Paix',
 'Paris', '75002',
 'Marie Dupont', 'mdupont@techsolutions.fr',
 'NET30', 'IT / Software',
 'active', 5,
 'Long-term IT partner since 2019. All invoices match POs. Reliable.'),

-- Acme Supplies SAS (PO-2025-001)
('Acme Supplies SAS',
 'FR7614508959032913463358',
 'FR98765432101',
 '45678912300045',
 '3 avenue Hoche',
 'Lyon', '69002',
 'Jean Bernard', 'jbernard@acme-supplies.fr',
 'NET45', 'Office Supplies',
 'active', 4,
 'Office supplies & consumables. Occasional invoice delays.'),

-- TechNord SARL (PO-2025-002)
('TechNord SARL',
 'DE89370400440532013000',
 'DE123456789',
 NULL,
 'Musterstraße 12',
 'Berlin', '10115',
 'Hans Müller', 'hmuller@technord.de',
 'NET30', 'IT Hardware',
 'active', 4,
 'German hardware supplier. IBAN is German (DE). Invoices in EUR.'),

-- Bureau Martin & Fils (PO-2025-003 — already paid)
('Bureau Martin & Fils',
 'FR7630006000011234567890',
 'FR11223344556',
 '23456789100023',
 '55 boulevard Voltaire',
 'Bordeaux', '33000',
 'Pierre Martin', 'pmartin@bureau-martin.fr',
 'NET30', 'Office Furniture',
 'active', 3,
 'PO-2025-003 was paid in full on 2025-02-10. Any new invoice for this PO is a duplicate.'),

-- Logistics Express (PO-2025-004)
('Logistics Express',
 'FR7614508959032913463399',
 'FR44556677889',
 '56789123400056',
 '8 quai de la Rapée',
 'Marseille', '13002',
 'Sophie Legrand', 'slegrand@logisticsexpress.fr',
 'NET15', 'Transport / Logistics',
 'active', 3,
 'Transport partner. Occasional surcharges — verify line items carefully.'),

-- Securitas France (PO-2025-005 — partial)
('Securitas France',
 'FR7610107001011234567890',
 'FR99887766554',
 '67891234500067',
 '20 rue de Rivoli',
 'Paris', '75001',
 'Luc Moreau', 'lmoreau@securitas.fr',
 'NET30', 'Security Services',
 'active', 4,
 'Monthly security contract. PO-2025-005: €2,100 total, €1,050 already paid (1st instalment).'),

-- CloudStack SARL (PO-2025-006)
('CloudStack SARL',
 'FR7614508959032913461111',
 'FR33221100998',
 '78912345600078',
 '1 place de la Bourse',
 'Paris', '75009',
 'Alice Fontaine', 'afontaine@cloudstack.fr',
 'NET30', 'Cloud / SaaS',
 'active', 5,
 'Cloud infrastructure. SLA 99.9%. Trusted supplier.'),

-- Imprimerie Dubois (PO-2025-007 — already paid)
('Imprimerie Dubois',
 'FR7630004000031234567812',
 'FR22334455667',
 '89123456700089',
 '12 rue Gutenberg',
 'Strasbourg', '67000',
 'René Dubois', 'rdubois@imprimerie-dubois.fr',
 'NET30', 'Print / Marketing',
 'active', 3,
 'PO-2025-007 paid 2025-03-05. Beware — they re-sent the same invoice in April.'),

-- Maintenance Pro (PO-2025-008)
('Maintenance Pro',
 'FR7614508959032913462222',
 'FR55443322110',
 '91234567800091',
 '44 rue du Faubourg Saint-Antoine',
 'Paris', '75011',
 'Marc Lefevre', 'mlefevre@maintenancepro.fr',
 'NET30', 'Facilities / Maintenance',
 'active', 3,
 'Building maintenance. Invoices sometimes arrive late. Check PO ref on each invoice. Known IBAN: FR7614508959032913462222 — any invoice with a different IBAN is fraudulent.'),

-- Conseil & Stratégie (PO-2025-009)
('Conseil & Stratégie',
 'FR7614208009012345678901',
 'FR66778899001',
 '12345678901234',
 '7 avenue de l''Opéra',
 'Paris', '75001',
 'Claire Vidal', 'cvidal@conseil-strategie.fr',
 'NET60', 'Consulting',
 'active', 4,
 'Strategic consulting firm. Large invoices. Payment terms NET60 by contract.'),

-- DataVault Technologies (PO-2025-010 — partial)
('DataVault Technologies',
 'FR7614508959032913463333',
 'FR77889900112',
 '23456789012345',
 '3 allée de l''Innovation',
 'Sophia Antipolis', '06560',
 'Nicolas Petit', 'npetit@datavault.fr',
 'NET45', 'Data / Analytics',
 'active', 4,
 'Data platform supplier. PO-2025-010: €15,600 total, first tranche of €7,800 paid 2025-01-20.')
ON CONFLICT DO NOTHING;
"""

SEED_PAYMENTS = """
INSERT INTO erp_payments
    (po_number, vendor_name, invoice_ref, amount_paid, currency,
     payment_date, bank_ref, payment_method, notes)
VALUES
-- Bureau Martin & Fils — full payment of PO-2025-003
('PO-2025-003', 'Bureau Martin & Fils', 'FAC-2025-0312', 5760.00, 'EUR',
 '2025-02-10', 'VIR-20250210-0042', 'virement',
 'Full payment. PO HT=4800, TVA 20%=960, total TTC=5760.'),

-- Imprimerie Dubois — full payment of PO-2025-007
('PO-2025-007', 'Imprimerie Dubois', 'FAC-2025-0789', 1620.00, 'EUR',
 '2025-03-05', 'VIR-20250305-0117', 'virement',
 'Full payment. PO HT=1350, TVA 20%=270, total TTC=1620.'),

-- Securitas France — first instalment of PO-2025-005
('PO-2025-005', 'Securitas France', 'FAC-2025-0156', 1260.00, 'EUR',
 '2025-02-01', 'VIR-20250201-0028', 'virement',
 'First instalment (50%). PO HT=2100, TVA=420, TTC=2520. Paid half = 1260.'),

-- DataVault Technologies — first tranche of PO-2025-010
('PO-2025-010', 'DataVault Technologies', 'FAC-2025-0445', 9360.00, 'EUR',
 '2025-01-20', 'VIR-20250120-0009', 'virement',
 'First tranche (50%). PO HT=15600, TVA=3120, TTC=18720. Paid half = 9360.')
ON CONFLICT DO NOTHING;
"""

SEED_EMAILS = [
    # TechSolutions — normal invoice flow
    ("THR-001", "Facture INV-2024-00042 – TechSolutions SAS", "TechSolutions SAS",
     "mdupont@techsolutions.fr", "comptabilite@monentreprise.fr",
     "2024-11-28 09:15:00+01", "PO-2024-8871", "INV-2024-00042", "invoice",
     "Bonjour,\n\nVeuillez trouver ci-joint notre facture INV-2024-00042 d'un montant de 12 360,00 € TTC correspondant à la commande PO-2024-8871 (maintenance logicielle Q4 2024).\n\nMerci de procéder au règlement avant le 28 décembre 2024.\n\nCordialement,\nMarie Dupont\nTechSolutions SAS"),

    ("THR-001", "RE: Facture INV-2024-00042 – TechSolutions SAS", "TechSolutions SAS",
     "comptabilite@monentreprise.fr", "mdupont@techsolutions.fr",
     "2024-11-29 11:30:00+01", "PO-2024-8871", "INV-2024-00042", "invoice",
     "Bonjour Marie,\n\nBien reçu. Nous traitons votre facture. Le paiement interviendra avant la date d'échéance.\n\nCordialement,\nService Comptabilité"),

    # Imprimerie Dubois — duplicate invoice attempt
    ("THR-002", "Facture FAC-2025-0789 – Imprimerie Dubois (déjà réglée)", "Imprimerie Dubois",
     "rdubois@imprimerie-dubois.fr", "comptabilite@monentreprise.fr",
     "2025-04-03 10:05:00+02", "PO-2025-007", "FAC-2025-0789", "dispute",
     "Bonjour,\n\nNous n'avons pas encore reçu le règlement de notre facture FAC-2025-0789 (1 620 € TTC, PO-2025-007). Pourriez-vous vérifier ?\n\nCordialement,\nRené Dubois"),

    ("THR-002", "RE: Facture FAC-2025-0789 – déjà payée le 05/03/2025", "Imprimerie Dubois",
     "comptabilite@monentreprise.fr", "rdubois@imprimerie-dubois.fr",
     "2025-04-03 14:20:00+02", "PO-2025-007", "FAC-2025-0789", "dispute",
     "Bonjour René,\n\nNous avons bien réglé cette facture le 05/03/2025 par virement VIR-20250305-0117. Merci de vérifier votre relevé bancaire. Si vous ne retrouvez pas le virement, contactez-nous.\n\nCordialement,\nService Comptabilité"),

    # Securitas France — partial payment reminder
    ("THR-003", "Rappel acompte – PO-2025-005 Securitas France", "Securitas France",
     "lmoreau@securitas.fr", "comptabilite@monentreprise.fr",
     "2025-03-15 08:45:00+01", "PO-2025-005", None, "reminder",
     "Bonjour,\n\nNous vous rappelons que le deuxième acompte de 1 260 € TTC (solde du contrat PO-2025-005) est dû au 31 mars 2025.\n\nMerci de votre diligence.\n\nLuc Moreau\nSecuritas France"),

    # Conseil & Stratégie — onboarding / contract
    ("THR-004", "Contrat de prestation – Conseil & Stratégie", "Conseil & Stratégie",
     "cvidal@conseil-strategie.fr", "direction@monentreprise.fr",
     "2025-01-05 09:00:00+01", "PO-2025-009", None, "onboarding",
     "Bonjour,\n\nVeuillez trouver ci-joint notre contrat de prestation pour la mission de conseil stratégique Q1/Q2 2025, montant HT 22 000 €, TVA 20%, soit 26 400 € TTC. Règlement NET60.\n\nClaire Vidal\nConseil & Stratégie"),

    # DataVault — first tranche confirmation
    ("THR-005", "Confirmation règlement tranche 1 – DataVault Technologies", "DataVault Technologies",
     "comptabilite@monentreprise.fr", "npetit@datavault.fr",
     "2025-01-20 16:00:00+01", "PO-2025-010", "FAC-2025-0445", "invoice",
     "Bonjour Nicolas,\n\nNous confirmons le virement de 9 360 € TTC (tranche 1/2, réf. VIR-20250120-0009) pour la facture FAC-2025-0445. La tranche 2 sera réglée à réception de votre prochaine facture.\n\nCordialement,\nService Comptabilité"),

    # CloudStack — general account info
    ("THR-006", "Mise à jour IBAN – CloudStack SARL", "CloudStack SARL",
     "afontaine@cloudstack.fr", "comptabilite@monentreprise.fr",
     "2025-02-12 11:00:00+01", "PO-2025-006", None, "general",
     "Bonjour,\n\nNous vous informons que notre IBAN reste inchangé : FR7614508959032913461111. Aucune modification bancaire n'est intervenue. Merci de bien vérifier toute demande de changement de coordonnées bancaires reçue par email — nous ne procédons jamais à de tels changements par email sans confirmation écrite sur papier en-tête.\n\nAlice Fontaine\nCloudStack SARL"),

    # TechNord — dispute on amounts
    ("THR-007", "Litige montant – PO-2025-002 TechNord SARL", "TechNord SARL",
     "hmuller@technord.de", "achats@monentreprise.fr",
     "2025-03-22 14:30:00+01", "PO-2025-002", None, "dispute",
     "Hallo,\n\nWir beziehen uns auf Bestellung PO-2025-002 (38.200 € HT). Unsere Rechnung wird 45.840 € TTC betragen (inkl. 20% MwSt.). Bitte bestätigen Sie die Bestellung.\n\nMit freundlichen Grüßen,\nHans Müller\nTechNord SARL"),

    ("THR-007", "RE: Litige montant – PO-2025-002 TechNord SARL", "TechNord SARL",
     "achats@monentreprise.fr", "hmuller@technord.de",
     "2025-03-23 09:15:00+01", "PO-2025-002", None, "dispute",
     "Bonjour Hans,\n\nConfirmé. PO HT = 38 200 €, TVA 20% = 7 640 €, TTC = 45 840 €. Votre facture est attendue.\n\nCordialement,\nService Achats"),
]


def run():
    import psycopg
    url = os.getenv("DATABASE_URL")
    if not url:
        print("ERROR: DATABASE_URL not set")
        sys.exit(1)

    with psycopg.connect(url) as conn:
        with conn.cursor() as cur:
            print("Creating tables...")
            cur.execute(DDL)

            print("Seeding erp_vendors...")
            cur.execute(SEED_VENDORS)

            print("Seeding erp_payments...")
            cur.execute(SEED_PAYMENTS)

            print("Seeding erp_emails...")
            for (tid, subj, vend, frm, to_, sent, po, inv, ttype, body) in SEED_EMAILS:
                cur.execute(
                    """
                    INSERT INTO erp_emails
                        (thread_id, subject, vendor_name, from_email, to_email,
                         sent_at, body, po_ref, invoice_ref, thread_type)
                    VALUES (%s, %s, %s, %s, %s, %s::timestamptz, %s, %s, %s, %s)
                    ON CONFLICT DO NOTHING
                    """,
                    (tid, subj, vend, frm, to_, sent, body, po, inv, ttype),
                )

            conn.commit()
            print("Done.")

        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM erp_vendors")
            print(f"  erp_vendors  : {cur.fetchone()[0]} rows")
            cur.execute("SELECT COUNT(*) FROM erp_payments")
            print(f"  erp_payments : {cur.fetchone()[0]} rows")
            cur.execute("SELECT COUNT(*) FROM erp_emails")
            print(f"  erp_emails   : {cur.fetchone()[0]} rows")


if __name__ == "__main__":
    run()
