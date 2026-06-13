interface ScoreBreakdownProps {
  semanticScore: number;
  genreScore: number;
  ratingScore: number;
  popularityScore: number;
  contentScore: number;
}

const BARS = [
  { label: "Semantic",   key: "semanticScore",   color: "bg-violet-500" },
  { label: "Genre",      key: "genreScore",       color: "bg-blue-500"   },
  { label: "Rating",     key: "ratingScore",      color: "bg-emerald-500"},
  { label: "Popularity", key: "popularityScore",  color: "bg-amber-500"  },
  { label: "Content",    key: "contentScore",     color: "bg-rose-500"   },
] as const;

export function ScoreBreakdown({
  semanticScore,
  genreScore,
  ratingScore,
  popularityScore,
  contentScore,
}: ScoreBreakdownProps) {
  const scores: Record<string, number> = {
    semanticScore,
    genreScore,
    ratingScore,
    popularityScore,
    contentScore,
  };

  return (
    <div className="space-y-2 rounded-3xl bg-white/5 p-4">
      <p className="text-xs uppercase tracking-[0.2em] text-slate-500">Score Breakdown</p>
      <div className="space-y-2">
        {BARS.map(({ label, key, color }) => {
          const pct = Math.round((scores[key] ?? 0) * 100);
          return (
            <div key={key} className="flex items-center gap-2">
              <span className="w-[4.5rem] shrink-0 text-xs text-slate-500">{label}</span>
              <div className="relative h-1.5 flex-1 overflow-hidden rounded-full bg-white/10">
                <div
                  className={`absolute inset-y-0 left-0 rounded-full ${color} transition-all duration-700`}
                  style={{ width: `${pct}%` }}
                />
              </div>
              <span className="w-7 text-right text-xs tabular-nums text-slate-400">{pct}%</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
