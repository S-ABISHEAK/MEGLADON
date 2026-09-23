import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { api } from "../services/api";
import ModelViewer, { ViewMode } from "../viewer/ModelViewer";
import Panel from "../components/Panel";
import FramesTab from "../components/tabs/FramesTab";
import KeyframesTab from "../components/tabs/KeyframesTab";
import TrajectoryTab from "../components/tabs/TrajectoryTab";
import DynamicObjectsTab from "../components/tabs/DynamicObjectsTab";

type Tab = "model" | "frames" | "keyframes" | "trajectory" | "dynamic";

export default function ResultsPage() {
  const { jobId } = useParams();
  const [tab, setTab] = useState<Tab>("model");
  const [mode, setMode] = useState<ViewMode>("textured");
  const [job, setJob] = useState<any>(null);
  const [report, setReport] = useState<any>(null);
  const [confidence, setConfidence] = useState<any>(null);
  const [coordinates, setCoordinates] = useState<any>(null);
  const [dynamicObjects, setDynamicObjects] = useState<any[]>([]);
  const [modelArtifacts, setModelArtifacts] = useState<any>(null);

  useEffect(() => {
    if (!jobId) return;
    api.getJob(jobId).then(setJob);
    api.getModel(jobId).then(setModelArtifacts).catch(() => {});
    api.getDynamicObjects(jobId).then(setDynamicObjects).catch(() => {});
    fetch(api.artifactUrl(`${jobId}/final/report.json`)).then((r) => r.ok && r.json()).then(setReport).catch(() => {});
    fetch(api.artifactUrl(`${jobId}/confidence/point_confidence.json`)).then((r) => r.ok && r.json()).then(setConfidence).catch(() => {});
    fetch(api.artifactUrl(`${jobId}/georeference/coordinates.json`)).then((r) => r.ok && r.json()).then(setCoordinates).catch(() => {});
  }, [jobId]);

  if (!jobId) return null;

  const glbUrl = modelArtifacts?.model_glb ? api.artifactUrl(modelArtifacts.model_glb.path) : null;
  const plyModelUrl = modelArtifacts?.model_ply ? api.artifactUrl(modelArtifacts.model_ply.path) : null;
  const pointCloudUrl = api.artifactUrl(`${jobId}/pointcloud/fused/fused_pointcloud.ply`);

  const tierCounts = confidence?.tier_counts || report?.reconstruction?.confidence_tier_counts || {};

  return (
    <div className="max-w-7xl mx-auto px-6 py-8">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-xl font-semibold text-white">Reconstruction Results</h2>
          <p className="text-sm text-slate-400 mt-1">Job {jobId.slice(0, 8)} · {job?.status}</p>
        </div>
        <div className="flex gap-2">
          <DownloadButton href={api.artifactUrl(`${jobId}/final/model.glb`)} label="GLB" />
          <DownloadButton href={api.artifactUrl(`${jobId}/final/model.obj`)} label="OBJ" />
          <DownloadButton href={api.artifactUrl(`${jobId}/final/model.ply`)} label="PLY" />
          <DownloadButton href={`/api/jobs/${jobId}/download-package`} label="Complete Package (.zip)" primary />
        </div>
      </div>

      <div className="flex gap-2 mb-4 border-b border-surface-border">
        {(["model", "frames", "keyframes", "trajectory", "dynamic"] as Tab[]).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-2 text-sm capitalize border-b-2 -mb-px transition-colors ${
              tab === t ? "border-accent text-white" : "border-transparent text-slate-400 hover:text-slate-200"
            }`}
          >
            {t === "model" ? "3D Model" : t}
          </button>
        ))}
      </div>

      {tab === "model" && (
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
          <div className="lg:col-span-3 h-[560px]">
            <div className="flex gap-2 mb-2">
              {(["textured", "wireframe", "pointcloud", "confidence"] as ViewMode[]).map((m) => (
                <button
                  key={m}
                  onClick={() => setMode(m)}
                  className={`text-xs px-3 py-1.5 rounded-lg border capitalize ${
                    mode === m
                      ? "bg-accent/15 border-accent/50 text-accent"
                      : "border-surface-border text-slate-400 hover:text-slate-200"
                  }`}
                >
                  {m}
                </button>
              ))}
            </div>
            <div className="h-[500px]">
              <ModelViewer
                glbUrl={glbUrl}
                plyModelUrl={plyModelUrl}
                pointCloudUrl={pointCloudUrl}
                mode={mode}
                confidenceTiers={confidence?.tiers || null}
              />
            </div>
            {mode === "confidence" && (
              <div className="flex gap-4 mt-2 text-xs">
                <Legend color="#22c55e" label="High confidence" />
                <Legend color="#eab308" label="Medium confidence" />
                <Legend color="#f97316" label="Low confidence" />
                <Legend color="#a855f7" label="Inferred" />
              </div>
            )}
          </div>

          <div className="space-y-4">
            <Panel title="MODEL">
              <Row k="Vertices" v={report?.reconstruction?.mesh_vertices} />
              <Row k="Triangles" v={report?.reconstruction?.mesh_triangles} />
              <Row k="Fused points" v={report?.reconstruction?.fused_point_count} />
              <Row k="Raw points" v={report?.reconstruction?.raw_point_count} />
            </Panel>

            <Panel title="GEOREFERENCE">
              <Row k="Type" v={coordinates?.reference_type} />
              <Row k="CRS" v={coordinates?.coordinate_system} />
              <Row k="Scale corrected" v={coordinates?.scale_corrected ? "Yes" : "No"} />
            </Panel>

            <Panel title="CONFIDENCE">
              <Row k="High" v={tierCounts.HIGH_CONFIDENCE ?? 0} color="#22c55e" />
              <Row k="Medium" v={tierCounts.MEDIUM_CONFIDENCE ?? 0} color="#eab308" />
              <Row k="Low" v={tierCounts.LOW_CONFIDENCE ?? 0} color="#f97316" />
              <Row k="Inferred" v={tierCounts.INFERRED ?? 0} color="#a855f7" />
            </Panel>

            <Panel title="DYNAMIC OBJECTS">
              <Row k="Detected" v={report?.processing?.dynamic_objects_detected} />
              <Row k="Tracked" v={report?.processing?.dynamic_objects_tracked} />
              <Row k="Marked dynamic" v={report?.processing?.dynamic_objects_dynamic} />
            </Panel>

            <Panel title="PROCESSING">
              <Row k="Total time" v={report?.performance?.total_time_s ? `${report.performance.total_time_s}s` : "—"} />
              <Row k="Frames processed" v={report?.processing?.frames_extracted} />
              <Row k="Keyframes" v={report?.processing?.keyframes} />
              <Row k="GPU" v={report?.performance?.gpu?.cuda_available ? report.performance.gpu.gpu_name : "CPU only"} />
            </Panel>

            {report?.demo_mode_components?.length > 0 && (
              <Panel title="DEMO MODE COMPONENTS">
                <ul className="text-xs text-purple-300 space-y-1 list-disc list-inside">
                  {report.demo_mode_components.map((c: string, i: number) => (
                    <li key={i}>{c}</li>
                  ))}
                </ul>
              </Panel>
            )}
          </div>
        </div>
      )}

      {tab === "frames" && <FramesTab jobId={jobId} />}
      {tab === "keyframes" && <KeyframesTab jobId={jobId} />}
      {tab === "trajectory" && <TrajectoryTab jobId={jobId} />}
      {tab === "dynamic" && <DynamicObjectsTab jobId={jobId} objects={dynamicObjects} />}
    </div>
  );
}

function DownloadButton({ href, label, primary }: { href: string; label: string; primary?: boolean }) {
  return (
    <a
      href={href}
      download
      className={`text-xs px-3 py-2 rounded-lg border transition-colors ${
        primary
          ? "bg-accent text-slate-900 border-accent font-semibold hover:bg-accent-dim"
          : "border-surface-border text-slate-300 hover:border-slate-500"
      }`}
    >
      {label}
    </a>
  );
}

function Row({ k, v, color }: { k: string; v: any; color?: string }) {
  return (
    <div className="flex items-center justify-between text-xs py-1">
      <span className="text-slate-400 flex items-center gap-1.5">
        {color && <span className="w-2 h-2 rounded-full inline-block" style={{ background: color }} />}
        {k}
      </span>
      <span className="text-slate-200 font-medium">{v ?? "—"}</span>
    </div>
  );
}

function Legend({ color, label }: { color: string; label: string }) {
  return (
    <div className="flex items-center gap-1.5 text-slate-400">
      <span className="w-2.5 h-2.5 rounded-full inline-block" style={{ background: color }} />
      {label}
    </div>
  );
}
