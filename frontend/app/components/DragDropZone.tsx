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
    <label
      className={[
        "dropzone",
        isOver ? "dropzone--over" : "",
        disabled ? "dropzone--disabled" : "",
      ]
        .filter(Boolean)
        .join(" ")}
    >
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
        <div className="dropzone__iconWrap">
          <svg
            width="22"
            height="22"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
            <polyline points="14 2 14 8 20 8" />
            <line x1="16" y1="13" x2="8" y2="13" />
            <line x1="16" y1="17" x2="8" y2="17" />
          </svg>
        </div>

        <div className="dropzone__title">
          Drag & drop invoice PDFs{" "}
          {!disabled && (
            <span
              onClick={(e) => e.stopPropagation()}
              style={{ pointerEvents: "none" }}
            >
              or browse files
            </span>
          )}
        </div>

        <div className="dropzone__meta">
          {disabled ? "Processing…" : "PDF only · up to 25 MB each"}
        </div>

        <div className="dropzone__chips">
          <span className="dropzone__chip">OCR ENABLED</span>
          <span className="dropzone__chip">AUTO-CLASSIFY</span>
          <span className="dropzone__chip">SOC 2</span>
        </div>
      </div>
    </label>
  );
}
