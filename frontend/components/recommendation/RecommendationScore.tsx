interface RecommendationScoreProps {
  score: number;
}

export function RecommendationScore({ score }: RecommendationScoreProps) {
  return (
    <div className="rounded-3xl bg-white/5 px-4 py-4 text-center text-slate-200">
      <p className="text-xs uppercase tracking-[0.2em] text-slate-500">Recommendation</p>
      <p className="mt-2 text-3xl font-semibold text-white">{score}%</p>
    </div>
  );
}
