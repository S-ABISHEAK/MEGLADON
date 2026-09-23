export default function Panel({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-xl border border-surface-border bg-surface-panel p-4">
      <h4 className="text-[11px] uppercase tracking-wide text-slate-500 mb-2">{title}</h4>
      <div>{children}</div>
    </div>
  );
}
