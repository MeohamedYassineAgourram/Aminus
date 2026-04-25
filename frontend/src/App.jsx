import { useState } from "react";
import DragDropZone from "./components/DragDropZone.jsx";
import InvoiceList from "./components/InvoiceList.jsx";
import AuditTrail from "./components/AuditTrail.jsx";

export default function App() {
  const [files, setFiles] = useState([]);
  const [selectedFileName, setSelectedFileName] = useState(null);

  return (
    <div style={{ padding: 24, fontFamily: "system-ui, -apple-system, sans-serif" }}>
      <h1 style={{ marginTop: 0 }}>Aegis CFO Dashboard</h1>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 360px", gap: 16 }}>
        <div>
          <DragDropZone onFiles={(newFiles) => setFiles(newFiles)} />
          <div style={{ height: 12 }} />
          <InvoiceList
            files={files}
            selectedFileName={selectedFileName}
            onSelect={(name) => setSelectedFileName(name)}
          />
        </div>

        <AuditTrail selectedFileName={selectedFileName} />
      </div>
    </div>
  );
}

