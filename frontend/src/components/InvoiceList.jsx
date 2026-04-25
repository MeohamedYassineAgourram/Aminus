export default function InvoiceList({ files, selectedFileName, onSelect }) {
  return (
    <div style={{ border: "1px solid #eee", borderRadius: 12, padding: 16 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
        <h2 style={{ margin: 0, fontSize: 16 }}>Invoices</h2>
        <div style={{ color: "#666", fontSize: 12 }}>{files?.length || 0} files</div>
      </div>

      <div style={{ marginTop: 12, display: "grid", gap: 8 }}>
        {(files || []).map((f) => {
          const active = f.name === selectedFileName;
          return (
            <button
              key={f.name}
              type="button"
              onClick={() => onSelect?.(f.name)}
              style={{
                textAlign: "left",
                borderRadius: 10,
                border: `1px solid ${active ? "#111" : "#ddd"}`,
                padding: "10px 12px",
                background: active ? "#111" : "white",
                color: active ? "white" : "#111",
                cursor: "pointer",
              }}
            >
              <div style={{ fontWeight: 600 }}>{f.name}</div>
              <div style={{ opacity: 0.8, fontSize: 12 }}>{Math.round((f.size || 0) / 1024)} KB</div>
            </button>
          );
        })}

        {(!files || files.length === 0) && (
          <div style={{ color: "#666", fontSize: 13 }}>No files yet.</div>
        )}
      </div>
    </div>
  );
}

