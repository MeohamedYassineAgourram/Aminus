export default function AuditTrail({ selectedFileName }) {
  return (
    <aside style={{ border: "1px solid #eee", borderRadius: 12, padding: 16 }}>
      <h2 style={{ margin: 0, fontSize: 16 }}>Audit trail</h2>
      <div style={{ color: "#666", marginTop: 10, fontSize: 13 }}>
        {selectedFileName
          ? `Select actions for: ${selectedFileName}`
          : "Select an invoice to see the explanation panel."}
      </div>
    </aside>
  );
}

