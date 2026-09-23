import clsx from "clsx";
import type { StageInfo } from "../types";
import { STAGE_LABELS } from "../types";

const STATUS_STYLES: Record<string, string> = {
  PENDING: "text-slate-500 border-surface-border",
  RUNNING: "text-accent border-accent/50",
  COMPLETED: "text-status-completed border-status-completed/50",
  FAILED: "text-status-failed border-status-failed/50",
};

export default function StageCard({ stage, elapsed }: { stage: StageInfo; elapsed?: number }) {
  const label = STAGE_LABELS[stage.stage] || stage.stage;
  return (
    <div className={clsx("rounded-xl border bg-surface-panel px-4 py-3", STATUS_STYLES[stage.status])}>
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium text-white">{label}</span>
        <span className={clsx("text-[10px] uppercase tracking-wide font-semibold px-2 py-0.5 rounded-full",
          stage.status === "RUNNING" && "bg-accent/15 text-accent",
          stage.status === "COMPLETED" && "bg-status-completed/15 text-status-completed",
          stage.status === "FAILED" && "bg-status-failed/15 text-status-failed",
          stage.status === "PENDING" && "bg-surface-border text-slate-500")}>
          {stage.status}
        </span>
      </div>

      <div className="h-1.5 rounded-full bg-surface-border overflow-hidden mt-3">
        <div
          className={clsx("h-full transition-all", stage.status === "FAILED" ? "bg-status-failed" : "bg-accent")}
          style={{ width: `${stage.progress}%` }}
        />
      </div>

      <div className="flex items-center justify-between mt-2 text-xs text-slate-400">
        <span className="truncate max-w-[70%]">{stage.current_operation || "—"}</span>
        <span>{stage.progress.toFixed(0)}%{elapsed ? ` · ${elapsed.toFixed(1)}s` : ""}</span>
      </div>

      {stage.demo_mode && (
        <p className="text-[11px] text-purple-300 bg-purple-500/10 border border-purple-500/20 rounded-md px-2 py-1 mt-2">
          DEMO ARTIFACT: {stage.demo_mode}
        </p>
      )}

      {Object.keys(stage.stats || {}).length > 0 && (
        <div className="flex flex-wrap gap-x-4 gap-y-1 mt-2 text-[11px] text-slate-500">
          {Object.entries(stage.stats).slice(0, 6).map(([k, v]) => (
            <span key={k}>{k.replace(/_/g, " ")}: <span className="text-slate-300">{String(v)}</span></span>
          ))}
        </div>
      )}
    </div>
  );
}
