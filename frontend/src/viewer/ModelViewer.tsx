import { Suspense, useEffect, useMemo, useRef, useState } from "react";
import { Canvas, useLoader, useThree } from "@react-three/fiber";
import { OrbitControls, Grid, Html } from "@react-three/drei";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";
import { PLYLoader } from "three/examples/jsm/loaders/PLYLoader.js";
import * as THREE from "three";

export type ViewMode = "textured" | "wireframe" | "pointcloud" | "confidence";

const TIER_COLORS: Record<string, [number, number, number]> = {
  HIGH_CONFIDENCE: [0.13, 0.77, 0.37],
  MEDIUM_CONFIDENCE: [0.92, 0.7, 0.03],
  LOW_CONFIDENCE: [0.98, 0.45, 0.09],
  INFERRED: [0.66, 0.33, 0.97],
};

function GlbMesh({ url, wireframe }: { url: string; wireframe: boolean }) {
  const gltf = useLoader(GLTFLoader, url);
  useEffect(() => {
    gltf.scene.traverse((obj) => {
      if ((obj as THREE.Mesh).isMesh) {
        const mesh = obj as THREE.Mesh;
        const mat = mesh.material as THREE.MeshStandardMaterial;
        if (mat) mat.wireframe = wireframe;
      }
    });
  }, [gltf, wireframe]);
  return <primitive object={gltf.scene} />;
}

function PlyMesh({ url, wireframe }: { url: string; wireframe: boolean }) {
  const geom = useLoader(PLYLoader, url);
  useEffect(() => {
    geom.computeVertexNormals();
  }, [geom]);
  return (
    <mesh geometry={geom}>
      <meshStandardMaterial vertexColors wireframe={wireframe} side={THREE.DoubleSide} />
    </mesh>
  );
}

function PointCloud({ url, confidenceTiers }: { url: string; confidenceTiers: string[] | null }) {
  const geom = useLoader(PLYLoader, url);
  const coloredGeom = useMemo(() => {
    if (!confidenceTiers || !confidenceTiers.length) return geom;
    const g = geom.clone();
    const count = g.attributes.position.count;
    const colors = new Float32Array(count * 3);
    for (let i = 0; i < count; i++) {
      const tier = confidenceTiers[i] || "MEDIUM_CONFIDENCE";
      const [r, gg, b] = TIER_COLORS[tier] || TIER_COLORS.MEDIUM_CONFIDENCE;
      colors[i * 3] = r;
      colors[i * 3 + 1] = gg;
      colors[i * 3 + 2] = b;
    }
    g.setAttribute("color", new THREE.BufferAttribute(colors, 3));
    return g;
  }, [geom, confidenceTiers]);

  return (
    <points geometry={coloredGeom}>
      <pointsMaterial size={0.02} vertexColors sizeAttenuation />
    </points>
  );
}

function AutoFrame({ children }: { children: React.ReactNode }) {
  const ref = useRef<THREE.Group>(null);
  const { camera, controls } = useThree() as any;
  const [framed, setFramed] = useState(false);

  useEffect(() => {
    setFramed(false);
  }, [children]);

  useEffect(() => {
    if (framed || !ref.current) return;
    const box = new THREE.Box3().setFromObject(ref.current);
    if (box.isEmpty()) return;
    const size = box.getSize(new THREE.Vector3());
    const center = box.getCenter(new THREE.Vector3());
    const maxDim = Math.max(size.x, size.y, size.z, 0.01);
    const dist = maxDim * 1.8;

    camera.near = maxDim / 1000;
    camera.far = maxDim * 100;
    camera.position.set(center.x + dist, center.y + dist * 0.6, center.z + dist);
    camera.updateProjectionMatrix();
    camera.lookAt(center);

    if (controls) {
      controls.target.copy(center);
      controls.update();
    }
    setFramed(true);
  });

  return <group ref={ref}>{children}</group>;
}

export default function ModelViewer({
  glbUrl,
  plyModelUrl,
  pointCloudUrl,
  mode,
  confidenceTiers,
}: {
  glbUrl: string | null;
  plyModelUrl: string | null;
  pointCloudUrl: string | null;
  mode: ViewMode;
  confidenceTiers: string[] | null;
}) {
  const wireframe = mode === "wireframe";

  return (
    <div className="w-full h-full rounded-xl overflow-hidden border border-surface-border bg-black">
      <Canvas camera={{ fov: 50, near: 0.01, far: 5000 }}>
        <ambientLight intensity={0.6} />
        <directionalLight position={[5, 10, 5]} intensity={1.1} />
        <directionalLight position={[-5, -5, -5]} intensity={0.3} />
        <Grid args={[50, 50]} cellColor="#1f2937" sectionColor="#334155" position={[0, -0.001, 0]} infiniteGrid fadeDistance={40} />

        <Suspense fallback={<Html center className="text-slate-400 text-sm">Loading model…</Html>}>
          <AutoFrame>
            {mode === "pointcloud" || mode === "confidence" ? (
              pointCloudUrl && (
                <PointCloud url={pointCloudUrl} confidenceTiers={mode === "confidence" ? confidenceTiers : null} />
              )
            ) : glbUrl ? (
              <GlbMesh url={glbUrl} wireframe={wireframe} />
            ) : plyModelUrl ? (
              <PlyMesh url={plyModelUrl} wireframe={wireframe} />
            ) : null}
          </AutoFrame>
        </Suspense>

        <OrbitControls makeDefault enableDamping dampingFactor={0.08} />
      </Canvas>
    </div>
  );
}
