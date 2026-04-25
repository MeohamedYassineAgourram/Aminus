"use client";

import { useState, useCallback, useMemo } from "react";
import DragDropZone from "../components/DragDropZone";

// ─────────────────────────────────────────────────────────────
// Types
// ─────────────────────────────────────────────────────────────
type InvoiceStatus = "to_be_checked" | "danger" | "not_yet_paid" | "checked";
type FilterType = "all" | InvoiceStatus;
type AuditTag = "INGEST" | "EXTRACT" | "MATCH" | "FLAG" | "DECISION";
type StepVariant = "default" | "success" | "warning" | "danger";

interface AuditStep {
  id: string;
  title: string;
  description: string;
  timestamp: string;
  durationMs: number;
  tag: AuditTag;
  variant: StepVariant;
}

interface Invoice {
  id: string;
  subId: string;
  vendor: string;
  vendorInitials: string;
  vendorColor: string;
  receivedDate: string;
  status: InvoiceStatus;
  amount: string;
  currency: string;
  dueDate: string;
  confidence: number;
  auditSteps: AuditStep[];
}

// ─────────────────────────────────────────────────────────────
// Demo data (matches reference UI)
// ─────────────────────────────────────────────────────────────
const DEMO: Invoice[] = [
  {
    id: "INV-2048", subId: "NW-88421", vendor: "Northwind Logistics", vendorInitials: "NL",
    vendorColor: "#3b82f6", receivedDate: "Apr 24", status: "danger",
    amount: "$48,230.50", currency: "USD 2025", dueDate: "May 02", confidence: 62,
    auditSteps: [
      { id: "s1", title: "Document ingested", description: "Parsed PDF for INV-2048 · 3 pages · OCR confidence 99.1%", timestamp: "14:02:11", durationMs: 412, tag: "INGEST", variant: "default" },
      { id: "s2", title: "Line items extracted", description: "Identified vendor \"Northwind Logistics\", 12 line items, tax block resolved (VAT 8.25%).", timestamp: "14:02:13", durationMs: 1840, tag: "EXTRACT", variant: "default" },
      { id: "s3", title: "PO match attempted", description: "Partial match against PO-44218. 2 line discrepancies on freight surcharge.", timestamp: "14:02:14", durationMs: 920, tag: "MATCH", variant: "warning" },
      { id: "s4", title: "Anomaly detected", description: "Amount exceeds vendor 90-day average by 312%. Bank account differs from prior remittance on file.", timestamp: "14:02:15", durationMs: 280, tag: "FLAG", variant: "danger" },
      { id: "s5", title: "Routed to controller review", description: "Policy P-08 triggered: invoices over $25k with new banking instructions require human approval.", timestamp: "14:02:16", durationMs: 90, tag: "DECISION", variant: "danger" },
    ],
  },
  {
    id: "INV-2047", subId: "HX-Q2-1142", vendor: "Helix Cloud Services", vendorInitials: "HC",
    vendorColor: "#8b5cf6", receivedDate: "Apr 24", status: "to_be_checked",
    amount: "$12,480.00", currency: "USD 2025", dueDate: "May 14", confidence: 94,
    auditSteps: [
      { id: "s1", title: "Document ingested", description: "Parsed PDF for INV-2047 · 2 pages · OCR confidence 98.7%", timestamp: "14:01:44", durationMs: 380, tag: "INGEST", variant: "default" },
      { id: "s2", title: "Line items extracted", description: "Identified vendor \"Helix Cloud Services\", 4 line items, SaaS subscription fees.", timestamp: "14:01:46", durationMs: 1200, tag: "EXTRACT", variant: "default" },
      { id: "s3", title: "PO match successful", description: "100% match against PO-44199. All line items verified.", timestamp: "14:01:47", durationMs: 760, tag: "MATCH", variant: "success" },
      { id: "s4", title: "No anomalies found", description: "Amount within historical range. Banking details match records on file.", timestamp: "14:01:48", durationMs: 210, tag: "FLAG", variant: "success" },
      { id: "s5", title: "Queued for payment", description: "Invoice approved for standard Net-30 payment cycle.", timestamp: "14:01:49", durationMs: 80, tag: "DECISION", variant: "success" },
    ],
  },
  {
    id: "INV-2046", subId: "9D-2025-099", vendor: "Atelier Design Co.", vendorInitials: "AD",
    vendorColor: "#ec4899", receivedDate: "Apr 23", status: "not_yet_paid",
    amount: "€6,420.75", currency: "EUR 2025", dueDate: "Apr 30", confidence: 88,
    auditSteps: [
      { id: "s1", title: "Document ingested", description: "Parsed PDF for INV-2046 · 1 page · OCR confidence 97.3%", timestamp: "11:34:02", durationMs: 290, tag: "INGEST", variant: "default" },
      { id: "s2", title: "Line items extracted", description: "Identified vendor \"Atelier Design Co.\", 6 line items, EUR currency detected.", timestamp: "11:34:04", durationMs: 980, tag: "EXTRACT", variant: "default" },
      { id: "s3", title: "PO match partial", description: "Partial match against PO-43887. FX conversion rate pending approval.", timestamp: "11:34:05", durationMs: 840, tag: "MATCH", variant: "warning" },
      { id: "s4", title: "Payment pending", description: "Invoice verified but awaiting FX rate confirmation for EUR settlement.", timestamp: "11:34:06", durationMs: 190, tag: "FLAG", variant: "warning" },
      { id: "s5", title: "Flagged for payment run", description: "Scheduled for next EUR payment batch on May 05.", timestamp: "11:34:07", durationMs: 70, tag: "DECISION", variant: "warning" },
    ],
  },
  {
    id: "INV-2045", subId: "ML-INV-7732", vendor: "Meridian Legal LLP", vendorInitials: "ML",
    vendorColor: "#0891b2", receivedDate: "Apr 23", status: "checked",
    amount: "$22,150.00", currency: "USD 2025", dueDate: "May 21", confidence: 97,
    auditSteps: [
      { id: "s1", title: "Document ingested", description: "Parsed PDF for INV-2045 · 4 pages · OCR confidence 99.8%", timestamp: "10:15:33", durationMs: 445, tag: "INGEST", variant: "default" },
      { id: "s2", title: "Line items extracted", description: "Identified vendor \"Meridian Legal LLP\", 8 line items, retainer fees.", timestamp: "10:15:35", durationMs: 1640, tag: "EXTRACT", variant: "default" },
      { id: "s3", title: "PO match successful", description: "Exact match against PO-43776. All retainer items reconciled.", timestamp: "10:15:37", durationMs: 880, tag: "MATCH", variant: "success" },
      { id: "s4", title: "No anomalies found", description: "All checks passed. Within budget and historical norms.", timestamp: "10:15:38", durationMs: 170, tag: "FLAG", variant: "success" },
      { id: "s5", title: "Auto-approved", description: "Payment scheduled for May 21. ACH transfer initiated.", timestamp: "10:15:39", durationMs: 95, tag: "DECISION", variant: "success" },
    ],
  },
  {
    id: "INV-2044", subId: "FS-9921-A", vendor: "Foundry Steel Ltd.", vendorInitials: "FS",
    vendorColor: "#dc2626", receivedDate: "Apr 22", status: "danger",
    amount: "£91,200.00", currency: "GBP 2025", dueDate: "Apr 28", confidence: 71,
    auditSteps: [
      { id: "s1", title: "Document ingested", description: "Parsed PDF for INV-2044 · 5 pages · OCR confidence 94.2%", timestamp: "09:44:18", durationMs: 621, tag: "INGEST", variant: "default" },
      { id: "s2", title: "Line items extracted", description: "Identified vendor \"Foundry Steel Ltd.\", 22 line items, GBP currency.", timestamp: "09:44:21", durationMs: 2100, tag: "EXTRACT", variant: "default" },
      { id: "s3", title: "PO match failed", description: "No matching PO found for this amount. Vendor ID mismatch on 4 items.", timestamp: "09:44:23", durationMs: 1040, tag: "MATCH", variant: "danger" },
      { id: "s4", title: "Critical anomaly detected", description: "Invoice amount £91,200 has no corresponding approved PO. New IBAN not on whitelist.", timestamp: "09:44:24", durationMs: 310, tag: "FLAG", variant: "danger" },
      { id: "s5", title: "Blocked — fraud review", description: "Escalated to CFO and security team. Payment frozen pending investigation.", timestamp: "09:44:25", durationMs: 85, tag: "DECISION", variant: "danger" },
    ],
  },
  {
    id: "INV-2043", subId: "PF-INV-3340", vendor: "Pacific Freight Co.", vendorInitials: "PF",
    vendorColor: "#16a34a", receivedDate: "Apr 22", status: "checked",
    amount: "$18,450.25", currency: "USD 2025", dueDate: "May 09", confidence: 99,
    auditSteps: [
      { id: "s1", title: "Document ingested", description: "Parsed PDF for INV-2043 · 2 pages · OCR confidence 99.9%", timestamp: "08:55:01", durationMs: 310, tag: "INGEST", variant: "default" },
      { id: "s2", title: "Line items extracted", description: "Identified vendor \"Pacific Freight Co.\", 3 line items, standard freight rates.", timestamp: "08:55:03", durationMs: 980, tag: "EXTRACT", variant: "default" },
      { id: "s3", title: "PO match successful", description: "100% match against PO-43541. All line items verified.", timestamp: "08:55:04", durationMs: 690, tag: "MATCH", variant: "success" },
      { id: "s4", title: "No anomalies found", description: "Perfect compliance. Regular vendor with consistent invoicing history.", timestamp: "08:55:05", durationMs: 140, tag: "FLAG", variant: "success" },
      { id: "s5", title: "Auto-approved", description: "Straight-through processing. Payment queued for May 09.", timestamp: "08:55:06", durationMs: 60, tag: "DECISION", variant: "success" },
    ],
  },
  {
    id: "INV-2042", subId: "QO-7782", vendor: "Quantum Office Supply", vendorInitials: "QO",
    vendorColor: "#7c3aed", receivedDate: "Apr 21", status: "to_be_checked",
    amount: "$1,240.40", currency: "USD 2025", dueDate: "May 16", confidence: 91,
    auditSteps: [
      { id: "s1", title: "Document ingested", description: "Parsed PDF for INV-2042 · 1 page · OCR confidence 98.4%", timestamp: "16:22:07", durationMs: 285, tag: "INGEST", variant: "default" },
      { id: "s2", title: "Line items extracted", description: "Identified vendor \"Quantum Office Supply\", 7 line items, office supplies.", timestamp: "16:22:09", durationMs: 820, tag: "EXTRACT", variant: "default" },
      { id: "s3", title: "PO match successful", description: "Matched PO-43488. Minor quantity variance on item 4 (within tolerance).", timestamp: "16:22:10", durationMs: 710, tag: "MATCH", variant: "success" },
      { id: "s4", title: "No anomalies found", description: "Low-value invoice within auto-approval threshold.", timestamp: "16:22:11", durationMs: 155, tag: "FLAG", variant: "success" },
      { id: "s5", title: "Queued for manager approval", description: "Under $5k threshold — routed to department manager for sign-off.", timestamp: "16:22:12", durationMs: 75, tag: "DECISION", variant: "default" },
    ],
  },
  {
    id: "INV-2041", subId: "LM-2025-Q2", vendor: "Lumen Marketing", vendorInitials: "LM",
    vendorColor: "#d97706", receivedDate: "Apr 20", status: "not_yet_paid",
    amount: "$34,900.00", currency: "USD 2025", dueDate: "Apr 27", confidence: 85,
    auditSteps: [
      { id: "s1", title: "Document ingested", description: "Parsed PDF for INV-2041 · 2 pages · OCR confidence 96.1%", timestamp: "14:10:55", durationMs: 405, tag: "INGEST", variant: "default" },
      { id: "s2", title: "Line items extracted", description: "Identified vendor \"Lumen Marketing\", 5 line items, Q2 retainer + campaign fees.", timestamp: "14:10:57", durationMs: 1380, tag: "EXTRACT", variant: "default" },
      { id: "s3", title: "PO match partial", description: "Retainer fees matched. Campaign overage of $4,200 not in approved PO scope.", timestamp: "14:10:58", durationMs: 900, tag: "MATCH", variant: "warning" },
      { id: "s4", title: "Budget variance flagged", description: "Campaign line exceeds approved budget by 14%. Awaiting marketing VP approval.", timestamp: "14:10:59", durationMs: 240, tag: "FLAG", variant: "warning" },
      { id: "s5", title: "On hold — budget review", description: "Payment withheld pending budget exception approval from CMO.", timestamp: "14:11:00", durationMs: 88, tag: "DECISION", variant: "warning" },
    ],
  },
  {
    id: "INV-2040", subId: "SIG-AR-5582", vendor: "Sigma Insurance Group", vendorInitials: "SI",
    vendorColor: "#0369a1", receivedDate: "Apr 20", status: "checked",
    amount: "$14,820.00", currency: "USD 2025", dueDate: "May 30", confidence: 96,
    auditSteps: [
      { id: "s1", title: "Document ingested", description: "Parsed PDF for INV-2040 · 3 pages · OCR confidence 99.5%", timestamp: "11:05:14", durationMs: 380, tag: "INGEST", variant: "default" },
      { id: "s2", title: "Line items extracted", description: "Identified vendor \"Sigma Insurance Group\", annual premium renewal.", timestamp: "11:05:16", durationMs: 1090, tag: "EXTRACT", variant: "default" },
      { id: "s3", title: "PO match successful", description: "Matched annual contract CN-2025-SIGMA. Renewal premium as expected.", timestamp: "11:05:17", durationMs: 720, tag: "MATCH", variant: "success" },
      { id: "s4", title: "No anomalies found", description: "Premium increase of 2.1% is within annual CPI adjustment clause.", timestamp: "11:05:18", durationMs: 185, tag: "FLAG", variant: "success" },
      { id: "s5", title: "Auto-approved", description: "Annual insurance renewal auto-approved per standing policy. Payment scheduled.", timestamp: "11:05:19", durationMs: 78, tag: "DECISION", variant: "success" },
    ],
  },
];

// ─────────────────────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────────────────────
function nowTime() {
  return new Date().toLocaleTimeString("en-US", { hour12: false });
}

function sleep(ms: number) {
  return new Promise<void>((r) => setTimeout(r, ms));
}

function confidenceClass(n: number) {
  if (n >= 90) return "high";
  if (n >= 70) return "mid";
  return "low";
}

const STATUS_LABELS: Record<InvoiceStatus, string> = {
  to_be_checked: "To Be Checked",
  danger: "Danger",
  not_yet_paid: "Not Yet Paid",
  checked: "Checked",
};

// ─────────────────────────────────────────────────────────────
// SVG icons
// ─────────────────────────────────────────────────────────────
const Icon = {
  Shield: () => (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
    </svg>
  ),
  Dashboard: () => (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="3" width="7" height="7" /><rect x="14" y="3" width="7" height="7" />
      <rect x="14" y="14" width="7" height="7" /><rect x="3" y="14" width="7" height="7" />
    </svg>
  ),
  File: () => (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
      <polyline points="14 2 14 8 20 8" />
    </svg>
  ),
  CreditCard: () => (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="1" y="4" width="22" height="16" rx="2" ry="2" /><line x1="1" y1="10" x2="23" y2="10" />
    </svg>
  ),
  Settings: () => (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="3" />
      <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" />
    </svg>
  ),
  Search: () => (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="11" cy="11" r="8" /><line x1="21" y1="21" x2="16.65" y2="16.65" />
    </svg>
  ),
  Bell: () => (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" /><path d="M13.73 21a2 2 0 0 1-3.46 0" />
    </svg>
  ),
  Help: () => (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="10" />
      <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3" /><line x1="12" y1="17" x2="12.01" y2="17" />
    </svg>
  ),
  ChevronDown: () => (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="6 9 12 15 18 9" />
    </svg>
  ),
  TrendUp: () => (
    <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="23 6 13.5 15.5 8.5 10.5 1 18" /><polyline points="17 6 23 6 23 12" />
    </svg>
  ),
  TrendDown: () => (
    <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="23 18 13.5 8.5 8.5 13.5 1 6" /><polyline points="17 18 23 18 23 12" />
    </svg>
  ),
  Dollar: () => (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <line x1="12" y1="1" x2="12" y2="23" /><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" />
    </svg>
  ),
  Check: () => (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="20 6 9 17 4 12" />
    </svg>
  ),
  AlertTriangle: () => (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
      <line x1="12" y1="9" x2="12" y2="13" /><line x1="12" y1="17" x2="12.01" y2="17" />
    </svg>
  ),
  Clock: () => (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="10" /><polyline points="12 6 12 12 16 14" />
    </svg>
  ),
  Filter: () => (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3" />
    </svg>
  ),
  SortAsc: () => (
    <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
      <line x1="12" y1="20" x2="12" y2="4" /><polyline points="6 10 12 4 18 10" />
    </svg>
  ),
  // Audit step icons
  IngestIcon: () => (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" /><polyline points="14 2 14 8 20 8" />
    </svg>
  ),
  ExtractIcon: () => (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="10" /><line x1="12" y1="8" x2="12" y2="12" /><line x1="12" y1="16" x2="12.01" y2="16" />
    </svg>
  ),
  MatchIcon: () => (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M4 6h16M4 12h10M4 18h7" />
    </svg>
  ),
  FlagIcon: () => (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
    </svg>
  ),
  DecisionIcon: () => (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="3" /><path d="M12 1v4M12 19v4M4.22 4.22l2.83 2.83M16.95 16.95l2.83 2.83M1 12h4M19 12h4M4.22 19.78l2.83-2.83M16.95 7.05l2.83-2.83" />
    </svg>
  ),
  LogIcon: () => (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 22s-8-4.5-8-11.8A8 8 0 0 1 12 2a8 8 0 0 1 8 8.2c0 7.3-8 11.8-8 11.8z" />
      <circle cx="12" cy="10" r="3" />
    </svg>
  ),
};

function AuditStepIcon({ tag }: { tag: AuditTag }) {
  if (tag === "INGEST") return <Icon.IngestIcon />;
  if (tag === "EXTRACT") return <Icon.ExtractIcon />;
  if (tag === "MATCH") return <Icon.MatchIcon />;
  if (tag === "FLAG") return <Icon.FlagIcon />;
  return <Icon.DecisionIcon />;
}

// ─────────────────────────────────────────────────────────────
// Audit Trail Panel
// ─────────────────────────────────────────────────────────────
function AuditPanel({
  invoice,
  liveSteps,
  isLive,
  processingName,
}: {
  invoice: Invoice | null;
  liveSteps: AuditStep[];
  isLive: boolean;
  processingName: string;
}) {
  const steps = isLive ? liveSteps : invoice?.auditSteps ?? [];
  const displayId = isLive ? "PROCESSING" : invoice?.id ?? "—";
  const totalMs = steps.reduce((s, x) => s + x.durationMs, 0);

  return (
    <aside className="auditPanel">
      <div className="auditPanel__header">
        <div className="auditPanel__titleGroup">
          <div className="auditPanel__logoIcon">
            <Icon.Shield />
          </div>
          <div>
            <p className="auditPanel__name">Agent Audit Trail</p>
            <p className="auditPanel__sub">AI reasoning · immutable log</p>
          </div>
        </div>
        <div className="livePill">
          <span className="livePill__dot" />
          Live
        </div>
      </div>

      {(invoice || isLive) && (
        <div className="auditPanel__meta">
          <div>
            <div className="auditMeta__label">Invoice</div>
            <div className="auditMeta__value">{displayId}</div>
          </div>
          <div>
            <div className="auditMeta__label">Steps</div>
            <div className="auditMeta__value">{steps.length}</div>
          </div>
          <div>
            <div className="auditMeta__label">Total</div>
            <div className="auditMeta__value">
              {totalMs > 0 ? `${(totalMs / 1000).toFixed(2)}s` : "—"}
            </div>
          </div>
        </div>
      )}

      <div className="auditSteps">
        {steps.length === 0 && !isLive && (
          <div className="auditEmpty">
            <div className="auditEmpty__icon">
              <Icon.Shield />
            </div>
            <p className="auditEmpty__title">No invoice selected</p>
            <p className="auditEmpty__text">
              Click any invoice row to see the full AI reasoning trail.
            </p>
          </div>
        )}

        {isLive && steps.length === 0 && (
          <div className="auditEmpty">
            <div className="auditSpinner" style={{ margin: "0 auto 12px" }} />
            <p className="auditEmpty__title">Processing…</p>
            <p className="auditEmpty__text">{processingName}</p>
          </div>
        )}

        {steps.map((step, i) => (
          <div className="auditStep" key={step.id}>
            <div className="auditStep__connector" />
            <div className={`auditStep__icon auditStep__icon--${step.variant}`}>
              {isLive && i === steps.length - 1 && step.durationMs === 0 ? (
                <div className="auditSpinner" />
              ) : (
                <AuditStepIcon tag={step.tag} />
              )}
            </div>
            <div className="auditStep__body">
              <div className="auditStep__head">
                <p className="auditStep__title">{step.title}</p>
                <span className="auditStep__time">{step.timestamp}</span>
              </div>
              <p className="auditStep__desc">{step.description}</p>
              <div className="auditStep__foot">
                <span className="auditStep__tag">{step.tag}</span>
                {step.durationMs > 0 && (
                  <span className="auditStep__ms">{step.durationMs}ms</span>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="auditPanel__footer">
        <Icon.LogIcon />
        <span className="auditPanel__footerText">
          Logs are signed and retained for 7 years (SOC 2 Type II)
        </span>
      </div>
    </aside>
  );
}

// ─────────────────────────────────────────────────────────────
// Main Dashboard
// ─────────────────────────────────────────────────────────────
export default function Dashboard() {
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [selectedId, setSelectedId] = useState<string>("INV-2048");
  const [filter, setFilter] = useState<FilterType>("all");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [liveSteps, setLiveSteps] = useState<AuditStep[]>([]);
  const [isLive, setIsLive] = useState(false);
  const [processingName, setProcessingName] = useState("");

  const LIVE_ID = "__live__";

  const backendUrl = useMemo(() => {
    if (typeof process !== "undefined" && process.env?.NEXT_PUBLIC_BACKEND_URL)
      return process.env.NEXT_PUBLIC_BACKEND_URL;
    if (typeof window !== "undefined")
      return `${window.location.protocol}//${window.location.hostname}:8000`;
    return "http://127.0.0.1:8000";
  }, []);

  const upload = useCallback(
    async (file: File) => {
      setBusy(true);
      setError(null);
      setIsLive(true);
      setLiveSteps([]);
      setSelectedId(LIVE_ID);
      setProcessingName(file.name);

      const steps: AuditStep[] = [];

      function pushStep(s: AuditStep) {
        steps.push(s);
        setLiveSteps([...steps]);
      }

      pushStep({
        id: "l1", title: "Document ingested",
        description: `Parsing ${file.name} · ${(file.size / 1024).toFixed(0)} KB`,
        timestamp: nowTime(), durationMs: 0, tag: "INGEST", variant: "default",
      });

      await sleep(550);

      pushStep({
        id: "l2", title: "Security check running",
        description: "Extracting Factur-X XML and invoking Gemini 1.5 Pro for visual comparison…",
        timestamp: nowTime(), durationMs: 0, tag: "EXTRACT", variant: "default",
      });

      try {
        const form = new FormData();
        form.append("file", file);
        const t0 = Date.now();
        const res = await fetch(`${backendUrl}/invoices/screen`, { method: "POST", body: form });
        if (!res.ok) throw new Error(`Backend error (${res.status}): ${await res.text()}`);
        const data = await res.json();
        const elapsed = Date.now() - t0;

        // Update step 2 with real outcome
        steps[1] = {
          ...steps[1],
          description: data.security?.match
            ? "XML and visual extraction match. No tampering detected."
            : `Security mismatch: ${(data.security?.diffs?.[0] ?? "unknown diff").slice(0, 80)}`,
          durationMs: Math.round(elapsed * 0.45),
          variant: data.security?.match ? "success" : "danger",
        };
        setLiveSteps([...steps]);

        await sleep(300);

        // Step 3 — reconciliation
        const reconciled = data.reconciliation?.decision;
        const step3Variant: StepVariant =
          !data.security?.match ? "danger"
          : reconciled === "already_paid" ? "success"
          : reconciled === "needs_review" ? "warning"
          : "default";

        pushStep({
          id: "l3",
          title: data.security?.match ? "ERP reconciliation complete" : "Reconciliation skipped",
          description: data.security?.match
            ? `Decision: ${reconciled ?? "pending"} — ${(data.reconciliation?.reason ?? "").slice(0, 100)}`
            : "Skipped — invoice blocked at security stage.",
          timestamp: nowTime(),
          durationMs: Math.round(elapsed * 0.45),
          tag: "MATCH",
          variant: step3Variant,
        });

        await sleep(250);

        // Step 4 — final decision
        const finalStatus: InvoiceStatus =
          data.status === "danger" ? "danger"
          : data.status === "checked" ? "checked"
          : data.status === "not_yet_paid" ? "not_yet_paid"
          : "to_be_checked";

        const decisionVariant: StepVariant =
          finalStatus === "danger" ? "danger"
          : finalStatus === "checked" ? "success"
          : finalStatus === "not_yet_paid" ? "warning"
          : "default";

        const decisionTitles: Record<InvoiceStatus, string> = {
          danger: "Flagged — manual review required",
          checked: "Auto-approved",
          not_yet_paid: "Queued — awaiting payment",
          to_be_checked: "Queued for review",
        };

        pushStep({
          id: "l4",
          title: decisionTitles[finalStatus],
          description: (data.reconciliation?.reason ?? "Pipeline complete.").slice(0, 120),
          timestamp: nowTime(),
          durationMs: Math.round(elapsed * 0.1),
          tag: "DECISION",
          variant: decisionVariant,
        });

        // Derive confidence from result
        const confidence = data.security?.match
          ? reconciled === "already_paid" ? 96
            : reconciled === "needs_review" ? 74
            : 85
          : 38;

        // Next invoice ID
        const maxId = invoices.reduce((m, inv) => {
          const n = parseInt(inv.id.replace("INV-", ""), 10);
          return isNaN(n) ? m : Math.max(m, n);
        }, 2048);
        const newId = `INV-${maxId + 1}`;

        const newInvoice: Invoice = {
          id: newId,
          subId: file.name.replace(/\.pdf$/i, "").slice(0, 14).toUpperCase().replace(/\s+/g, "-"),
          vendor: file.name.replace(/\.pdf$/i, ""),
          vendorInitials: file.name.slice(0, 2).toUpperCase(),
          vendorColor: finalStatus === "danger" ? "#dc2626" : finalStatus === "checked" ? "#16a34a" : "#2563eb",
          receivedDate: new Date().toLocaleDateString("en-US", { month: "short", day: "numeric" }),
          status: finalStatus,
          amount: "—",
          currency: "USD",
          dueDate: "—",
          confidence,
          auditSteps: [...steps],
        };

        setInvoices((prev) => [newInvoice, ...prev]);
        setSelectedId(newId);
        setIsLive(false);
      } catch (err: any) {
        const msg = err?.message ?? String(err);
        steps[1] = {
          ...steps[1],
          description: `Error: ${msg.slice(0, 120)}`,
          variant: "danger",
        };
        setLiveSteps([...steps]);
        setError(msg);
        setIsLive(false);
      } finally {
        setBusy(false);
      }
    },
    [backendUrl, invoices],
  );

  // ── Derived state ──────────────────────────────────────────
  const filtered = useMemo(
    () => (filter === "all" ? invoices : invoices.filter((i) => i.status === filter)),
    [invoices, filter],
  );

  const counts = useMemo(() => ({
    all: invoices.length,
    to_be_checked: invoices.filter((i) => i.status === "to_be_checked").length,
    danger: invoices.filter((i) => i.status === "danger").length,
    not_yet_paid: invoices.filter((i) => i.status === "not_yet_paid").length,
    checked: invoices.filter((i) => i.status === "checked").length,
  }), [invoices]);

  const selectedInvoice = useMemo(
    () => (selectedId === LIVE_ID ? null : invoices.find((i) => i.id === selectedId) ?? null),
    [invoices, selectedId],
  );

  // ── Render ─────────────────────────────────────────────────
  return (
    <div className="app">
      {/* ── Navbar ── */}
      <nav className="navbar">
        <a className="nav__brand" href="#">
          <div className="nav__logo">
            <Icon.Shield />
          </div>
          <div className="nav__brandText">
            <span className="nav__brandName">Aminus</span>
            <span className="nav__brandSub">CFO Suite</span>
          </div>
        </a>

        <div className="nav__tabs">
          <button className="nav__tab nav__tab--active">
            <Icon.Dashboard /> Dashboard
          </button>
          <button className="nav__tab">
            <Icon.File /> Invoices
          </button>
          <button className="nav__tab">
            <Icon.CreditCard /> Payments
          </button>
          <button className="nav__tab">
            <Icon.Settings /> Settings
          </button>
        </div>

        <div className="nav__right">
          <div className="nav__search">
            <Icon.Search />
            <span>Search invoices, vendors…</span>
            <span className="nav__searchKbd">⌘K</span>
          </div>
          <button className="nav__iconBtn"><Icon.Help /></button>
          <button className="nav__iconBtn"><Icon.Bell /></button>
          <div className="nav__user">
            <div className="nav__avatar">EM</div>
            <div className="nav__userInfo">
              <span className="nav__userName">Elena Marsh</span>
              <span className="nav__userRole">CFO · Acme Corp</span>
            </div>
            <Icon.ChevronDown />
          </div>
        </div>
      </nav>

      {/* ── Page ── */}
      <main className="page">
        {/* Page header */}
        <div className="pageHeader">
          <div>
            <p className="pageHeader__eyebrow">Accounts Payable · Q2 2025</p>
            <h1 className="pageHeader__title">Invoice Intelligence</h1>
          </div>
          <div className="pageHeader__right">
            <p>
              Drop invoices below — agents will extract, match, and route them.
              Every decision is fully auditable.
            </p>
          </div>
        </div>

        {/* Stats */}
        <div className="statsGrid">
          <div className="statCard">
            <div className="statCard__top">
              <div className="statCard__icon"><Icon.Dollar /></div>
            </div>
            <div>
              <p className="statCard__label">Invoices Screened</p>
              <div className="statCard__value">{counts.all}</div>
            </div>
          </div>
          <div className="statCard">
            <div className="statCard__top">
              <div className="statCard__icon"><Icon.Check /></div>
            </div>
            <div>
              <p className="statCard__label">Checked</p>
              <div className="statCard__value">{counts.checked}</div>
            </div>
          </div>
          <div className="statCard">
            <div className="statCard__top">
              <div className="statCard__icon"><Icon.AlertTriangle /></div>
            </div>
            <div>
              <p className="statCard__label">Flagged for Review</p>
              <div className="statCard__value">{counts.danger}</div>
            </div>
          </div>
          <div className="statCard">
            <div className="statCard__top">
              <div className="statCard__icon"><Icon.Clock /></div>
            </div>
            <div>
              <p className="statCard__label">Not Yet Paid</p>
              <div className="statCard__value">{counts.not_yet_paid}</div>
            </div>
          </div>
        </div>

        {/* Upload zone */}
        <div className="uploadZone">
          <DragDropZone onFile={upload} disabled={busy} />
          {error && (
            <div className="errorBanner">
              <Icon.AlertTriangle />
              {error}
            </div>
          )}
        </div>

        {/* Invoice queue + Audit trail */}
        <div className="contentGrid">
          {/* Queue */}
          <div className="queuePanel">
            <div className="queuePanel__header">
              <div className="queuePanel__titleRow">
                <div className="queuePanel__titleGroup">
                  <h2 className="queuePanel__title">Invoice Queue</h2>
                  <p className="queuePanel__subtitle">
                    {invoices.length} of {invoices.length} invoices · auto-refreshed 2s ago
                  </p>
                </div>
                <div className="queuePanel__actions">
                  <div className="queuePanel__searchBox">
                    <Icon.Search />
                    <span>Search vendor, ID, ref…</span>
                  </div>
                  <button className="queuePanel__filterBtn">
                    <Icon.Filter /> Filters
                  </button>
                </div>
              </div>

              <div className="filterTabs">
                {(["all", "to_be_checked", "danger", "not_yet_paid", "checked"] as const).map((f) => (
                  <button
                    key={f}
                    className={`filterTab ${filter === f ? "filterTab--active" : ""}`}
                    onClick={() => setFilter(f)}
                  >
                    {f === "all" ? "All" : STATUS_LABELS[f as InvoiceStatus]}
                    <span className="filterTab__count">
                      {f === "all" ? counts.all : counts[f as keyof typeof counts]}
                    </span>
                  </button>
                ))}
              </div>
            </div>

            <div className="invoiceTable">
              <div className="invoiceTable__head">
                <div className="th"><Icon.SortAsc /> Invoice</div>
                <div className="th">Vendor</div>
                <div className="th">Status</div>
                <div className="th">Amount Due</div>
                <div className="th">AI Confidence</div>
              </div>

              <div>
                {filtered.length === 0 && (
                  <div style={{ padding: "32px 20px", textAlign: "center", color: "#94a3b8" }}>
                    <div style={{ fontSize: 14, fontWeight: 600, color: "#475569", marginBottom: 6 }}>
                      No invoices yet
                    </div>
                    <div style={{ fontSize: 13 }}>
                      Drop a PDF above to run the first screening.
                    </div>
                  </div>
                )}

                {filtered.map((inv) => {
                  const isSelected = selectedId === inv.id;
                  const cf = confidenceClass(inv.confidence);
                  return (
                    <div
                      key={inv.id}
                      className={`invoiceRow ${isSelected ? "invoiceRow--selected" : ""}`}
                      onClick={() => { setSelectedId(inv.id); setIsLive(false); }}
                    >
                      {/* ID */}
                      <div>
                        <div className="invoiceRow__id">{inv.id}</div>
                        <div className="invoiceRow__subId">{inv.subId}</div>
                      </div>

                      {/* Vendor */}
                      <div className="invoiceRow__vendor">
                        <div className="vendorAvatar" style={{ background: inv.vendorColor }}>
                          {inv.vendorInitials}
                        </div>
                        <div>
                          <div className="invoiceRow__vendorName">{inv.vendor}</div>
                          <div className="invoiceRow__vendorDate">Received {inv.receivedDate}</div>
                        </div>
                      </div>

                      {/* Status */}
                      <div>
                        <span className={`badge badge--${inv.status}`}>
                          {inv.status === "danger" && "⚠ "}
                          {inv.status === "to_be_checked" && "○ "}
                          {inv.status === "checked" && "✓ "}
                          {STATUS_LABELS[inv.status]}
                        </span>
                      </div>

                      {/* Amount */}
                      <div>
                        <div className="invoiceRow__amount">
                          {inv.amount} <span style={{ fontWeight: 500, fontSize: 11, color: "#94a3b8" }}>{inv.dueDate}</span>
                        </div>
                        <div className="invoiceRow__currency">{inv.currency}</div>
                      </div>

                      {/* Confidence */}
                      <div>
                        <div className="confidence__bar">
                          <div
                            className={`confidence__fill confidence__fill--${cf}`}
                            style={{ width: `${inv.confidence}%` }}
                          />
                        </div>
                        <div className="confidence__pct">{inv.confidence}%</div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>

          {/* Audit trail */}
          <AuditPanel
            invoice={selectedInvoice}
            liveSteps={liveSteps}
            isLive={isLive || selectedId === LIVE_ID}
            processingName={processingName}
          />
        </div>
      </main>
    </div>
  );
}
