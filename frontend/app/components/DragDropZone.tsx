"use client";

import { useCallback, useState } from "react";

type Props = {
  onFile: (file: File) => void;
  disabled?: boolean;
};

export default function DragDropZone({ onFile, disabled }: Props) {
  const [isOver, setIsOver] = useState(false);

  const onDrop = useCallback(
    (e: React.DragEvent<HTMLDivElement>) => {
      e.preventDefault();
      if (disabled) return;
      const f = e.dataTransfer.files?.[0];
      if (f) onFile(f);
      setIsOver(false);
    },
    [disabled, onFile],
  );

  return (
    <div
      onDragOver={(e) => {
        e.preventDefault();
        if (!disabled) setIsOver(true);
      }}
      onDragLeave={() => setIsOver(false)}
      onDrop={onDrop}
      style={{
        border: "2px dashed #bbb",
        borderRadius: 12,
        padding: 24,
        background: isOver ? "#f2f2f2" : "#fafafa",
        opacity: disabled ? 0.6 : 1,
      }}
    >
      <div style={{ fontWeight: 700 }}>Drag & drop an invoice PDF</div>
      <div style={{ color: "#666", marginTop: 6, fontSize: 13 }}>
        It will be uploaded to the Python API for security + reconciliation screening.
      </div>
    </div>
  );
}

