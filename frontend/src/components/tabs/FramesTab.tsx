import { useEffect, useState } from "react";
import { api } from "../../services/api";

export default function FramesTab({ jobId }: { jobId: string }) {
  const [frames, setFrames] = useState<any[]>([]);

  useEffect(() => {
    api.getFrames(jobId).then(setFrames);
  }, [jobId]);

  const accepted = frames.filter((f) => f.selected);
  const rejected = frames.filter((f) => !f.selected);
  const avgQuality = frames.length ? frames.reduce((s, f) => s + (f.quality_score || 0), 0) / frames.length : 0;

  return (
    <div>
      <div className="grid grid-cols-4 gap-3 mb-6">
        <Stat label="Total frames" value={frames.length} />
        <Stat label="Accepted" value={accepted.length} />
        <Stat label="Rejected" value={rejected.length} />
        <Stat label="Avg quality" value={avgQuality.toFixed(2)} />
      </div>

      <QualityHistogram frames={frames} />

      <h4 className="text-sm text-slate-300 mt-6 mb-2">Sample frames</h4>
      <div className="grid grid-cols-4 sm:grid-cols-6 md:grid-cols-8 gap-2">
        {frames.slice(0, 24).map((f) => (
          <div key={f.frame_id} className="relative rounded-lg overflow-hidden border border-surface-border">
            <img src={api.artifactUrl(f.path)} className="w-full aspect-video object-cover" loading="lazy" />
            <span
              className={`absolute top-1 right-1 text-[9px] px-1.5 py-0.5 rounded-full ${
                f.selected ? "bg-status-completed/80 text-black" : "bg-status-failed/80 text-white"
              }`}
            >
              {f.quality_score?.toFixed(2)}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

function QualityHistogram({ frames }: { frames: any[] }) {
  const buckets = new Array(10).fill(0);
  frames.forEach((f) => {
    const idx = Math.min(9, Math.floor((f.quality_score || 0) * 10));
    buckets[idx]++;
  });
  const max = Math.max(...buckets, 1);
  return (
    <div>
      <h4 className="text-sm text-slate-300 mb-2">Frame quality distribution</h4>
      <div className="flex items-end gap-1 h-24 bg-surface-panel border border-surface-border rounded-xl p-3">
        {buckets.map((count, i) => (
          <div key={i} className="flex-1 flex flex-col items-center gap-1">
            <div
              className="w-full bg-accent/60 rounded-t"
              style={{ height: `${(count / max) * 70}px` }}
              title={`${count} frames`}
            />
            <span className="text-[9px] text-slate-600">{(i / 10).toFixed(1)}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: any }) {
  return (
    <div className="rounded-lg bg-surface-panel border border-surface-border px-3 py-2">
      <p className="text-[10px] uppercase text-slate-500">{label}</p>
      <p className="text-lg text-white font-semibold">{value}</p>
    </div>
  );
}
