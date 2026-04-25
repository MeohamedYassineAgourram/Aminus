"use client";

import { useMemo, useState } from "react";
import DragDropZone from "../components/DragDropZone";

type ScreeningResponse =
  | {
      status: "danger" | "error";
      stage: "security";
      security: { status: string; match: boolean; diffs: string[] };
    }
  | {
      status: string;
      stage: "done";
      security: { status: string; match: boolean; diffs: string[] };
      reconciliation: any;
      persistence: any;
      filename?: string;
      bytes?: number;
    };

export default function Dashboard() {
  const [busy, setBusy] = useState(false);
  const [items, setItems] = useState<Array<{ name: string; result: ScreeningResponse }>>([]);
  const [error, setError] = useState<string | null>(null);

  const backendUrl = useMemo(() => {
    if (process.env.NEXT_PUBLIC_BACKEND_URL) return process.env.NEXT_PUBLIC_BACKEND_URL;
    if (typeof window !== "undefined") {
      return `${window.location.protocol}//${window.location.hostname}:8000`;
    }
    return "http://127.0.0.1:8000";
  }, []);

  async function upload(file: File) {
    setError(null);
    setBusy(true);
    try {
      const form = new FormData();
      form.append("file", file);
      const res = await fetch(`${backendUrl}/invoices/screen`, {
        method: "POST",
        body: form,
      });
      if (!res.ok) {
        const body = await res.text();
        throw new Error(`Backend error (${res.status}): ${body || res.statusText}`);
      }
      const json = (await res.json()) as ScreeningResponse;
      setItems((prev) => [{ name: file.name, result: json }, ...prev]);
    } catch (e: any) {
      setError(e?.message || String(e));
    } finally {
      setBusy(false);
    }
  }

  const stats = useMemo(() => {
    const total = items.length;
    const checked = items.filter((x) => x.result.status === "checked").length;
    const danger = items.filter((x) => x.result.status === "danger").length;
    const toReview = items.filter((x) => x.result.status === "to_be_checked").length;
    return { total, checked, danger, toReview };
  }, [items]);

  function getBadge(status: string) {
    if (status === "danger") return { cls: "badge badge--danger", label: "Danger" };
    if (status === "error") return { cls: "badge badge--warning", label: "Error" };
    if (status === "checked") return { cls: "badge badge--ok", label: "Checked" };
    return { cls: "badge badge--info", label: "To be checked" };
  }

  return (
    <div className="dashboard">
      <section className="hero">
        <p className="hero__eyebrow">Aminus AI Plugin</p>
        <h1 className="hero__title">Smart Invoice Screening Dashboard</h1>
        <p className="hero__subtitle">
          Real-time fraud detection with Factur-X XML integrity check and AI-assisted reconciliation.
        </p>
        <div className="hero__meta">
          <span className="chip">Backend: {backendUrl}</span>
          <span className={`chip ${busy ? "chip--live" : ""}`}>{busy ? "Screening in progress" : "System ready"}</span>
        </div>
      </section>

      <section className="stats">
        <article className="stat">
          <div className="stat__label">Invoices screened</div>
          <div className="stat__value">{stats.total}</div>
        </article>
        <article className="stat">
          <div className="stat__label">Checked</div>
          <div className="stat__value stat__value--ok">{stats.checked}</div>
        </article>
        <article className="stat">
          <div className="stat__label">To be checked</div>
          <div className="stat__value stat__value--info">{stats.toReview}</div>
        </article>
        <article className="stat">
          <div className="stat__label">Danger flagged</div>
          <div className="stat__value stat__value--danger">{stats.danger}</div>
        </article>
      </section>

      <section className="pipeline">
        <div className="pipeline__step">
          <div className="pipeline__stepIndex">1</div>
          <div className="pipeline__stepBody">
            <h3>Security Check</h3>
            <p>Factur-X XML extraction is compared with Gemini visual extraction.</p>
          </div>
        </div>
        <div className="pipeline__connector" />
        <div className="pipeline__step">
          <div className="pipeline__stepIndex">2</div>
          <div className="pipeline__stepBody">
            <h3>Reconciliation</h3>
            <p>Claude reviews ERP context and decides paid, unpaid, or needs review.</p>
          </div>
        </div>
        <div className="pipeline__connector" />
        <div className="pipeline__step">
          <div className="pipeline__stepIndex">3</div>
          <div className="pipeline__stepBody">
            <h3>Storage & Traceability</h3>
            <p>Invoice metadata and decision are persisted for finance audit trails.</p>
          </div>
        </div>
      </section>

      <section className="panel">
        <h2>Upload an invoice</h2>
        <p>Drop your PDF to trigger automated screening and status scoring.</p>
        <DragDropZone onFile={upload} disabled={busy} />
        {error && <div className="errorBanner">{error}</div>}
      </section>

      <section className="results">
        <h2>Screening results</h2>
        <p>Latest results appear first, with complete reconciliation and persistence traces.</p>
        <div className="resultList">
          {items.map((it, idx) => {
            const r = it.result;
            const badge = getBadge(r.status);
            return (
              <article key={`${it.name}-${idx}`} className="resultCard">
                <header className="resultCard__head">
                  <div>
                    <h3>{it.name}</h3>
                    <p>{r.stage === "security" ? "Stopped at security stage" : "Pipeline completed"}</p>
                  </div>
                  <span className={badge.cls}>{badge.label}</span>
                </header>

                <div className="resultCard__section">
                  <strong>Security:</strong> {r.security?.match ? "XML and visual data match." : "Mismatch detected."} (
                  {r.security?.status})
                </div>

                {r.security?.diffs?.length ? (
                  <details className="resultCard__details">
                    <summary>Security diffs ({r.security.diffs.length})</summary>
                    <pre>{r.security.diffs.join("\n")}</pre>
                  </details>
                ) : null}

                {"reconciliation" in r ? (
                  <details className="resultCard__details">
                    <summary>Reconciliation details</summary>
                    <pre>{JSON.stringify(r.reconciliation, null, 2)}</pre>
                  </details>
                ) : null}

                {"persistence" in r ? (
                  <details className="resultCard__details">
                    <summary>Persistence details</summary>
                    <pre>{JSON.stringify(r.persistence, null, 2)}</pre>
                  </details>
                ) : null}
              </article>
            );
          })}

          {items.length === 0 && (
            <div className="emptyState">
              <div className="emptyState__title">No invoices screened yet.</div>
              <div className="emptyState__text">
                Upload your first invoice to see live AI screening, risk status, and reconciliation output.
              </div>
            </div>
          )}
        </div>
      </section>
    </div>
  );
}

