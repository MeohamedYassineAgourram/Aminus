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
    <label className={`dropzone ${isOver ? "dropzone--over" : ""} ${disabled ? "dropzone--disabled" : ""}`}>
      <input
        type="file"
        accept="application/pdf"
        disabled={disabled}
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) onFile(file);
          e.currentTarget.value = "";
        }}
        className="dropzone__input"
      />
      <div
        onDragOver={(e) => {
          e.preventDefault();
          if (!disabled) setIsOver(true);
        }}
        onDragLeave={() => setIsOver(false)}
        onDrop={onDrop}
        className="dropzone__surface"
      >
        <div className="dropzone__icon">PDF</div>
        <div className="dropzone__title">Drag & drop invoice PDF</div>
        <div className="dropzone__subtitle">
          Stage 1: XML vs Vision security check, then Stage 2 reconciliation.
        </div>
        <div className="dropzone__cta">{disabled ? "Processing..." : "or click to choose a file"}</div>
      </div>
    </label>
  );
}

