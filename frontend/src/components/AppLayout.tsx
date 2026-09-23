import { Link } from "react-router-dom";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen flex flex-col bg-surface">
      <header className="border-b border-surface-border bg-surface-panel/60 backdrop-blur px-6 py-4">
        <Link to="/" className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-accent/20 border border-accent/40 flex items-center justify-center text-accent font-bold">
            M
          </div>
          <div>
            <h1 className="text-lg font-semibold tracking-tight text-white">MEGALODON</h1>
            <p className="text-xs text-slate-400 -mt-0.5">
              Intelligent Single-Pass Drone 3D Reconstruction System
            </p>
          </div>
        </Link>
      </header>
      <main className="flex-1">{children}</main>
      <footer className="border-t border-surface-border px-6 py-3 text-xs text-slate-500">
        Single-Pass 4K Drone Video → Metric Georeferenced 3D Model · SIH26158
      </footer>
    </div>
  );
}
