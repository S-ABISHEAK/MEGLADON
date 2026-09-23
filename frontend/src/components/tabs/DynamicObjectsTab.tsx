const STATUS_COLORS: Record<string, string> = {
  DYNAMIC: "text-status-failed", STATIC: "text-status-completed", UNCERTAIN: "text-slate-400",
};

export default function DynamicObjectsTab({ jobId, objects }: { jobId: string; objects: any[] }) {
  const dynamic = objects.filter((o) => o.motion_status === "DYNAMIC");
  const staticObjs = objects.filter((o) => o.motion_status === "STATIC");

  return (
    <div>
      <div className="grid grid-cols-3 gap-3 mb-6">
        <Stat label="Tracked objects" value={objects.length} />
        <Stat label="Dynamic" value={dynamic.length} accent="text-status-failed" />
        <Stat label="Static" value={staticObjs.length} accent="text-status-completed" />
      </div>

      <div className="rounded-xl border border-surface-border bg-surface-panel overflow-hidden">
        <table className="w-full text-xs">
          <thead className="bg-surface text-slate-500 uppercase text-[10px]">
            <tr>
              <th className="text-left px-4 py-2">Object ID</th>
              <th className="text-left px-4 py-2">Class</th>
              <th className="text-left px-4 py-2">Confidence</th>
              <th className="text-left px-4 py-2">Motion Status</th>
              <th className="text-left px-4 py-2">Frames tracked</th>
              <th className="text-left px-4 py-2">First / Last seen</th>
            </tr>
          </thead>
          <tbody>
            {objects.map((o) => (
              <tr key={o.object_id} className="border-t border-surface-border">
                <td className="px-4 py-2 text-slate-300">{o.object_id}</td>
                <td className="px-4 py-2 text-slate-200 capitalize">{o.class}</td>
                <td className="px-4 py-2 text-slate-400">{(o.confidence * 100).toFixed(0)}%</td>
                <td className={`px-4 py-2 font-medium ${STATUS_COLORS[o.motion_status] || ""}`}>{o.motion_status}</td>
                <td className="px-4 py-2 text-slate-400">{o.trajectory?.length ?? 0}</td>
                <td className="px-4 py-2 text-slate-500">{o.first_seen?.toFixed(1)}s – {o.last_seen?.toFixed(1)}s</td>
              </tr>
            ))}
            {objects.length === 0 && (
              <tr><td colSpan={6} className="px-4 py-6 text-center text-slate-500">No dynamic objects detected in this reconstruction.</td></tr>
            )}
          </tbody>
        </table>
      </div>

      <p className="text-xs text-slate-500 mt-4">
        Dynamic objects are excluded from the static 3D geometry (not deleted) and preserved as a separate
        inspectable layer — see <code className="text-slate-400">dynamic/dynamic_layer/</code> in the job's artifact directory.
      </p>
    </div>
  );
}

function Stat({ label, value, accent }: { label: string; value: any; accent?: string }) {
  return (
    <div className="rounded-lg bg-surface-panel border border-surface-border px-3 py-2">
      <p className="text-[10px] uppercase text-slate-500">{label}</p>
      <p className={`text-lg font-semibold ${accent || "text-white"}`}>{value}</p>
    </div>
  );
}
