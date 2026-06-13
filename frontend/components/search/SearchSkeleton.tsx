export function SearchSkeleton() {
  return (
    <div className="grid gap-6 sm:grid-cols-2 xl:grid-cols-3">
      {Array.from({ length: 6 }).map((_, index) => (
        <div key={index} className="animate-pulse rounded-4xl border border-white/10 bg-surface/80 p-6">
          <div className="mb-4 h-64 rounded-3xl bg-slate-900" />
          <div className="h-5 w-3/4 rounded-full bg-slate-900" />
          <div className="mt-3 h-4 w-1/2 rounded-full bg-slate-900" />
          <div className="mt-6 space-y-2">
            <div className="h-3 w-full rounded-full bg-slate-900" />
            <div className="h-3 w-5/6 rounded-full bg-slate-900" />
          </div>
        </div>
      ))}
    </div>
  );
}
