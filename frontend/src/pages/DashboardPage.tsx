import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api } from "../services/api";
import { useJobSocket } from "../hooks/useJobSocket";
import StageCard from "../components/StageCard";
import { STAGE_ORDER, STAGE_LABELS } from "../types";
import type { StageInfo } from "../types";

export default function DashboardPage() {
  const { jobId } = useParams();
  const navigate = useNavigate();
  const { events, connected } = useJobSocket(jobId);
  const [stages, setStages] = useState<Record<string, StageInfo>>({});
  const [jobStatus, setJobStatus] = useState<string>("UPLOADED");
  const [startedAt] = useState(Date.now());
  const [now, setNow] = useState(Date.now());

  useEffect(() => {
    if (!jobId) return;
    api.getStages(jobId).then((s) => {
      const map: Record<string, StageInfo> = {};
      s.forEach((st) => (map[st.stage] = st));
      setStages(map);
    });
  }, [jobId]);

  useEffect(() => {
    const t = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(t);
  }, []);

  useEffect(() => {
    const last = events[events.length - 1];
    if (!last) return;

    if (last.type === "stage_started" || last.type === "stage_progress" || last.type === "stage_completed" || last.type === "stage_failed") {
      setStages((prev) => {
        const existing = prev[last.stage!] || {
          stage: last.stage!, status: "PENDING", progress: 0, current_operation: null, stats: {}, demo_mode: null, log: "",
        };
        const updated: StageInfo = { ...existing };
        if (last.type === "stage_started") { updated.status = "RUNNING"; updated.current_operation = last.operation ?? null; }
        if (last.type === "stage_progress") {
          updated.progress = last.progress ?? updated.progress;
          updated.current_operation = last.operation ?? updated.current_operation;
          updated.stats = { ...updated.stats, ...(last.stats || {}) };
        }
        if (last.type === "stage_completed") { updated.status = "COMPLETED"; updated.progress = 100; updated.stats = { ...updated.stats, ...(last.stats || {}) }; }
        if (last.type === "stage_failed") { updated.status = "FAILED"; }
        return { ...prev, [last.stage!]: updated };
      });
    }

    if (last.type === "demo_mode") {
      setStages((prev) => {
        const existing = prev[last.stage!];
        if (!existing) return prev;
        const list = new Set((existing.demo_mode || "").split(",").filter(Boolean));
        list.add(last.component!);
        return { ...prev, [last.stage!]: { ...existing, demo_mode: Array.from(list).join(",") } };
      });
    }

    if (last.type === "job_completed") {
      setJobStatus("COMPLETED");
      setTimeout(() => navigate(`/jobs/${jobId}/results`), 900);
    }
    if (last.type === "job_failed") {
      setJobStatus("FAILED");
    }
  }, [events, jobId, navigate]);

  const orderedStages = useMemo(
    () => STAGE_ORDER.map((s) => stages[s]).filter(Boolean) as StageInfo[],
    [stages]
  );

  const overallProgress = orderedStages.length
    ? orderedStages.reduce((sum, s) => sum + s.progress, 0) / STAGE_ORDER.length
    : 0;

  const logLines = events.filter((e) => e.type === "log").slice(-40);
  const elapsedTotal = (now - startedAt) / 1000;
  const failed = orderedStages.find((s) => s.status === "FAILED");

  return (
    <div className="max-w-6xl mx-auto px-6 py-10">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-xl font-semibold text-white">Reconstruction Pipeline</h2>
          <p className="text-sm text-slate-400 mt-1">
            Job {jobId?.slice(0, 8)} · {connected ? "live" : "connecting…"} · elapsed {elapsedTotal.toFixed(0)}s
          </p>
        </div>
        <div className="text-right">
          <p className="text-2xl font-semibold text-accent">{overallProgress.toFixed(0)}%</p>
          <p className="text-xs text-slate-500">overall progress</p>
        </div>
      </div>

      {failed && jobStatus === "FAILED" && (
        <div className="mb-6 rounded-xl border border-status-failed/40 bg-status-failed/10 px-4 py-3">
          <p className="text-sm text-status-failed font-medium">
            Pipeline failed at {STAGE_LABELS[failed.stage]}
          </p>
          <button
            onClick={() => jobId && api.retryJob(jobId).then(() => window.location.reload())}
            className="mt-2 text-xs bg-status-failed/20 hover:bg-status-failed/30 text-status-failed px-3 py-1.5 rounded-lg"
          >
            Retry from failed stage
          </button>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {STAGE_ORDER.map((stageId) => {
          const stage = stages[stageId] || {
            stage: stageId, status: "PENDING", progress: 0, current_operation: null, stats: {}, demo_mode: null, log: "",
          };
          return <StageCard key={stageId} stage={stage} />;
        })}
      </div>

      <div className="mt-8">
        <h3 className="text-sm font-medium text-slate-300 mb-2">Processing Log</h3>
        <div className="rounded-xl border border-surface-border bg-black/40 px-4 py-3 h-56 overflow-y-auto font-mono text-xs text-slate-400">
          {logLines.length === 0 && <p className="text-slate-600">Waiting for pipeline events…</p>}
          {logLines.map((l, i) => (
            <div key={i}>
              <span className="text-slate-600">[{new Date(l.ts * 1000).toLocaleTimeString()}]</span>{" "}
              <span className="text-accent">{l.stage}</span> {l.message}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
