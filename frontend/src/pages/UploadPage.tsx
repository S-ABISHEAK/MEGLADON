import { useState } from "react";
import { useNavigate } from "react-router-dom";
import DropZone from "../components/DropZone";
import { api } from "../services/api";

function formatBytes(bytes: number) {
  if (bytes < 1024) return `${bytes} B`;
  const units = ["KB", "MB", "GB"];
  let val = bytes;
  let i = -1;
  do {
    val /= 1024;
    i++;
  } while (val >= 1024 && i < units.length - 1);
  return `${val.toFixed(1)} ${units[i]}`;
}

export default function UploadPage() {
  const navigate = useNavigate();
  const [file, setFile] = useState<File | null>(null);
  const [sensorFile, setSensorFile] = useState<File | null>(null);
  const [jobId, setJobId] = useState<string | null>(null);
  const [metadata, setMetadata] = useState<any>(null);
  const [uploadPct, setUploadPct] = useState(0);
  const [phase, setPhase] = useState<"idle" | "uploading" | "ready" | "starting" | "error">("idle");
  const [error, setError] = useState<string | null>(null);

  async function handleFile(f: File) {
    setFile(f);
    setError(null);
    setPhase("uploading");
    try {
      const { job_id } = await api.createJob();
      setJobId(job_id);
      const result = await api.uploadVideo(job_id, f, setUploadPct);
      setMetadata(result.metadata);
      setPhase("ready");
    } catch (e: any) {
      setError(e.message || "upload failed");
      setPhase("error");
    }
  }

  async function handleStart() {
    if (!jobId) return;
    setPhase("starting");
    try {
      if (sensorFile) await api.uploadSensorFile(jobId, sensorFile);
      await api.startJob(jobId);
      navigate(`/jobs/${jobId}`);
    } catch (e: any) {
      setError(e.message || "failed to start reconstruction");
      setPhase("ready");
    }
  }

  return (
    <div className="max-w-3xl mx-auto px-6 py-12">
      <div className="mb-8 text-center">
        <h2 className="text-2xl font-semibold text-white">Single-Pass 4K Drone Video → Metric Georeferenced 3D Model</h2>
        <p className="text-slate-400 mt-2 text-sm">
          Upload → Start Reconstruction → Monitor Pipeline → Inspect Results → Download Outputs
        </p>
      </div>

      {!file && <DropZone onFile={handleFile} />}

      {file && (
        <div className="rounded-2xl border border-surface-border bg-surface-panel p-6">
          <div className="flex items-start justify-between">
            <div>
              <p className="font-medium text-white">{file.name}</p>
              <p className="text-sm text-slate-400 mt-1">{formatBytes(file.size)}</p>
            </div>
            <button
              className="text-xs text-slate-400 hover:text-white"
              onClick={() => {
                setFile(null);
                setJobId(null);
                setMetadata(null);
                setPhase("idle");
              }}
            >
              Remove
            </button>
          </div>

          {phase === "uploading" && (
            <div className="mt-5">
              <div className="h-2 rounded-full bg-surface-border overflow-hidden">
                <div className="h-full bg-accent transition-all" style={{ width: `${uploadPct}%` }} />
              </div>
              <p className="text-xs text-slate-400 mt-2">Uploading… {uploadPct.toFixed(0)}%</p>
            </div>
          )}

          {metadata && (
            <div className="mt-5 grid grid-cols-2 sm:grid-cols-4 gap-3 text-sm">
              <Stat label="Resolution" value={`${metadata.width}×${metadata.height}`} />
              <Stat label="FPS" value={metadata.fps?.toFixed(1)} />
              <Stat label="Duration" value={`${metadata.duration?.toFixed(1)}s`} />
              <Stat label="Codec" value={metadata.codec?.toUpperCase()} />
              <Stat label="Bitrate" value={`${Math.round((metadata.bitrate || 0) / 1000)} kbps`} />
              <Stat label="GPS Metadata" value={metadata.has_gps_metadata === "yes" ? "Present" : "Not detected"} />
            </div>
          )}

          {phase === "ready" && (
            <div className="mt-6 border-t border-surface-border pt-5">
              <label className="text-sm text-slate-300 block mb-2">
                Optional: GPS / IMU / RTK sensor file (CSV, JSON, NMEA)
              </label>
              <input
                type="file"
                accept=".csv,.json,.nmea"
                onChange={(e) => setSensorFile(e.target.files?.[0] || null)}
                className="text-sm text-slate-400 file:mr-3 file:py-1.5 file:px-3 file:rounded-lg
                  file:border-0 file:bg-surface-border file:text-slate-200 file:text-sm"
              />
              {!sensorFile && (
                <p className="text-xs text-slate-500 mt-2">
                  No sensor file supplied — pose estimation will run visual-only and report this explicitly.
                </p>
              )}

              <button
                onClick={handleStart}
                className="mt-6 w-full rounded-xl bg-accent hover:bg-accent-dim text-slate-900 font-semibold
                  py-3 transition-colors"
              >
                START RECONSTRUCTION
              </button>
            </div>
          )}

          {phase === "starting" && (
            <p className="text-sm text-accent mt-6">Creating reconstruction job…</p>
          )}
        </div>
      )}

      {error && (
        <p className="mt-4 text-sm text-red-400 bg-red-500/10 border border-red-500/30 rounded-lg px-4 py-3">
          {error}
        </p>
      )}
    </div>
  );
}

function Stat({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="rounded-lg bg-surface border border-surface-border px-3 py-2">
      <p className="text-[10px] uppercase tracking-wide text-slate-500">{label}</p>
      <p className="text-sm text-slate-200 mt-0.5">{value ?? "—"}</p>
    </div>
  );
}
