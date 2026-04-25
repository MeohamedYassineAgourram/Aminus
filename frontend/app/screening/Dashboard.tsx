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

  const backendUrl = useMemo(
    () => process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000",
    [],
  );

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
      const json = (await res.json()) as ScreeningResponse;
      setItems((prev) => [{ name: file.name, result: json }, ...prev]);
    } catch (e: any) {
      setError(e?.message || String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div style={{ padding: 24 }}>
      <h1 style={{ margin: 0 }}>Invoice Screening</h1>
      <div style={{ color: "#666", marginTop: 6 }}>
        Stage 1: Factur-X XML vs Gemini Vision. Stage 2: Supabase ERP + Mistral reconciliation.
      </div>

      <div style={{ height: 16 }} />
      <DragDropZone onFile={upload} disabled={busy} />
      {error && <div style={{ marginTop: 12, color: "#b00020" }}>{error}</div>}

      <div style={{ height: 16 }} />
      <div style={{ display: "grid", gap: 10 }}>
        {items.map((it, idx) => {
          const r = it.result;
          const badge =
            r.status === "danger"
              ? { bg: "#fff0f0", fg: "#b00020", label: "Danger" }
              : r.status === "error"
                ? { bg: "#fff7e6", fg: "#8a5a00", label: "Error" }
                : r.status === "checked"
                  ? { bg: "#e9f7ef", fg: "#0b6b2f", label: "Checked" }
                  : { bg: "#e8f0fe", fg: "#174ea6", label: "To be checked" };

          return (
            <div
              key={`${it.name}-${idx}`}
              style={{
                border: "1px solid #eee",
                borderRadius: 12,
                padding: 14,
                background: "white",
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", gap: 12 }}>
                <div style={{ fontWeight: 700 }}>{it.name}</div>
                <div
                  style={{
                    padding: "4px 10px",
                    borderRadius: 999,
                    background: badge.bg,
                    color: badge.fg,
                    fontWeight: 700,
                    fontSize: 12,
                    alignSelf: "flex-start",
                  }}
                >
                  {badge.label}
                </div>
              </div>

              <div style={{ marginTop: 10, color: "#444", fontSize: 13 }}>
                <div>
                  <b>Security:</b> {r.security?.match ? "match" : "mismatch"} ({r.security?.status})
                </div>
                {r.security?.diffs?.length ? (
                  <details style={{ marginTop: 8 }}>
                    <summary>Diffs ({r.security.diffs.length})</summary>
                    <pre style={{ whiteSpace: "pre-wrap" }}>{r.security.diffs.join("\n")}</pre>
                  </details>
                ) : null}

                {"reconciliation" in r ? (
                  <details style={{ marginTop: 8 }}>
                    <summary>Reconciliation</summary>
                    <pre style={{ whiteSpace: "pre-wrap" }}>
                      {JSON.stringify(r.reconciliation, null, 2)}
                    </pre>
                  </details>
                ) : null}

                {"persistence" in r ? (
                  <details style={{ marginTop: 8 }}>
                    <summary>Persistence</summary>
                    <pre style={{ whiteSpace: "pre-wrap" }}>
                      {JSON.stringify(r.persistence, null, 2)}
                    </pre>
                  </details>
                ) : null}
              </div>
            </div>
          );
        })}

        {items.length === 0 && (
          <div style={{ color: "#666", fontSize: 13 }}>No invoices screened yet.</div>
        )}
      </div>
    </div>
  );
}

