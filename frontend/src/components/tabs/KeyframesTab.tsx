import { useEffect, useState } from "react";
import { api } from "../../services/api";

export default function KeyframesTab({ jobId }: { jobId: string }) {
  const [keyframes, setKeyframes] = useState<any[]>([]);

  useEffect(() => {
    api.getKeyframes(jobId).then(setKeyframes);
  }, [jobId]);

  return (
    <div>
      <p className="text-sm text-slate-400 mb-4">{keyframes.length} keyframes selected via ORB similarity + motion + overlap analysis</p>
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3">
        {keyframes.map((kf) => (
          <div key={kf.frame_id} className="rounded-lg overflow-hidden border border-surface-border bg-surface-panel">
            <img src={api.artifactUrl(kf.path)} className="w-full aspect-video object-cover" loading="lazy" />
            <div className="p-2 text-[11px] text-slate-400 space-y-0.5">
              <p className="text-slate-200 font-medium">{kf.frame_id}</p>
              <p>t = {kf.timestamp?.toFixed(2)}s</p>
              <p>similarity: {kf.similarity?.toFixed(2)} · motion: {kf.motion_score?.toFixed(2)}</p>
              <p className="text-accent">{kf.selection_reason}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
