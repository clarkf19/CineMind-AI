export function LoadingState() {
  return (
    <div className="flex items-center justify-center rounded-3xl border border-white/10 bg-black/60 p-10 text-slate-300 shadow-glow">
      <div className="space-y-3 text-center">
        <div className="mx-auto h-10 w-10 animate-spin rounded-full border-4 border-white/20 border-t-white" />
        <p className="text-sm text-slate-400">Loading movie discoveries...</p>
      </div>
    </div>
  );
}
