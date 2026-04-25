export default function DragDropZone({ onFiles }) {
  const onDrop = (e) => {
    e.preventDefault();
    const dropped = Array.from(e.dataTransfer.files || []);
    onFiles?.(dropped);
  };

  return (
    <div
      onDragOver={(e) => e.preventDefault()}
      onDrop={onDrop}
      style={{
        border: "2px dashed #bbb",
        borderRadius: 12,
        padding: 24,
        background: "#fafafa",
      }}
    >
      <div style={{ fontWeight: 600 }}>Drop invoices here</div>
      <div style={{ color: "#666", marginTop: 6 }}>
        (UI scaffold only — wire this to the backend next)
      </div>
    </div>
  );
}

