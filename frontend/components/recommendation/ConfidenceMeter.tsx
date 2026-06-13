interface ConfidenceMeterProps {
  score: number;
}

export function ConfidenceMeter({ score }: ConfidenceMeterProps) {
  return (
    <div className="space-y-2 rounded-3xl border border-white/10 bg-white/5 p-4">
      <div className="flex items-center justify-between text-sm text-slate-300">
        <span>Confidence</span>
        <span className="font-semibold text-white">{Math.round(score * 100)}%</span>
      </div>
      <div className="h-3 overflow-hidden rounded-full bg-slate-800">
        <div className="h-full rounded-full bg-gradient-to-r from-accent to-accent2" style={{ width: `${Math.min(100, Math.max(0, score * 100))}%` }} />
      </div>
    </div>
  );
}
