import { useCallback, useRef, useState } from "react";

const ALLOWED = [".mp4", ".mov", ".avi", ".mkv"];

export default function DropZone({ onFile }: { onFile: (f: File) => void }) {
  const [dragActive, setDragActive] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFiles = useCallback(
    (files: FileList | null) => {
      if (!files || !files.length) return;
      const file = files[0];
      const ext = "." + file.name.split(".").pop()?.toLowerCase();
      if (!ALLOWED.includes(ext)) {
        alert(`Unsupported file type ${ext}. Allowed: ${ALLOWED.join(", ")}`);
        return;
      }
      onFile(file);
    },
    [onFile]
  );

  return (
    <div
      onDragOver={(e) => {
        e.preventDefault();
        setDragActive(true);
      }}
      onDragLeave={() => setDragActive(false)}
      onDrop={(e) => {
        e.preventDefault();
        setDragActive(false);
        handleFiles(e.dataTransfer.files);
      }}
      onClick={() => inputRef.current?.click()}
      className={`cursor-pointer rounded-2xl border-2 border-dashed transition-colors px-8 py-16 text-center
        ${dragActive ? "border-accent bg-accent/5" : "border-surface-border hover:border-slate-600"}`}
    >
      <input
        ref={inputRef}
        type="file"
        accept={ALLOWED.join(",")}
        className="hidden"
        onChange={(e) => handleFiles(e.target.files)}
      />
      <div className="mx-auto w-14 h-14 rounded-full bg-accent/10 border border-accent/30 flex items-center justify-center mb-4">
        <svg className="w-7 h-7 text-accent" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
            d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5M16.5 12L12 16.5m0 0L7.5 12m4.5 4.5V3" />
        </svg>
      </div>
      <p className="text-base font-medium text-white">Upload 4K Drone Video</p>
      <p className="text-sm text-slate-400 mt-1">Drag and drop, or click to browse</p>
      <p className="text-xs text-slate-500 mt-3">Supported: MP4 · MOV · AVI · MKV</p>
    </div>
  );
}
