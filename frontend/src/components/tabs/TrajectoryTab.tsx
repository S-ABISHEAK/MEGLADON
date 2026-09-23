import { useEffect, useMemo, useState } from "react";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from "recharts";
import { Canvas } from "@react-three/fiber";
import { OrbitControls, Line as DreiLine } from "@react-three/drei";
import { api } from "../../services/api";

const SOURCE_COLORS: Record<string, string> = {
  VISUAL: "#38bdf8", IMU: "#a855f7", GPS: "#22c55e", RTK: "#f97316", FUSED: "#eab308",
};

export default function TrajectoryTab({ jobId }: { jobId: string }) {
  const [poses, setPoses] = useState<any[]>([]);

  useEffect(() => {
    api.getTrajectory(jobId).then(setPoses);
  }, [jobId]);

  const sources = useMemo(() => Array.from(new Set(poses.map((p) => p.source))), [poses]);
  const points = useMemo(() => poses.map((p) => [p.x, p.y, p.z] as [number, number, number]), [poses]);

  return (
    <div>
      <div className="flex gap-3 mb-4 text-xs">
        {sources.map((s) => (
          <span key={s} className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full inline-block" style={{ background: SOURCE_COLORS[s] || "#94a3b8" }} />
            {s}
          </span>
        ))}
        <span className="text-slate-500 ml-auto">{poses.length} poses</span>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="rounded-xl border border-surface-border bg-surface-panel p-4">
          <h4 className="text-xs uppercase text-slate-500 mb-3">2D Trajectory (top-down X/Y)</h4>
          <ResponsiveContainer width="100%" height={280}>
            <LineChart data={poses}>
              <CartesianGrid stroke="#1f2937" />
              <XAxis dataKey="x" stroke="#64748b" fontSize={11} />
              <YAxis dataKey="y" stroke="#64748b" fontSize={11} />
              <Tooltip contentStyle={{ background: "#111827", border: "1px solid #1f2937", fontSize: 12 }} />
              <Legend />
              <Line type="monotone" dataKey="y" stroke="#38bdf8" dot={false} name="Y position" />
              <Line type="monotone" dataKey="confidence" stroke="#22c55e" dot={false} name="Confidence" yAxisId={0} />
            </LineChart>
          </ResponsiveContainer>
        </div>

        <div className="rounded-xl border border-surface-border bg-surface-panel p-4 h-[340px]">
          <h4 className="text-xs uppercase text-slate-500 mb-3">3D Camera Trajectory</h4>
          <div className="h-[280px]">
            <Canvas camera={{ position: [2, 2, 2], fov: 50 }}>
              <ambientLight intensity={0.8} />
              <axesHelper args={[1]} />
              {points.length > 1 && <DreiLine points={points} color="#38bdf8" lineWidth={2} />}
              {points.map((p, i) => (
                <mesh key={i} position={p}>
                  <sphereGeometry args={[0.02, 8, 8]} />
                  <meshBasicMaterial color={SOURCE_COLORS[poses[i]?.source] || "#94a3b8"} />
                </mesh>
              ))}
              <OrbitControls makeDefault />
            </Canvas>
          </div>
        </div>
      </div>
    </div>
  );
}
