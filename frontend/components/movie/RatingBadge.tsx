interface RatingBadgeProps {
  rating: number;
}

export function RatingBadge({ rating }: RatingBadgeProps) {
  return (
    <div className="rounded-2xl bg-white/5 px-3 py-1 text-sm font-semibold text-slate-200">
      ⭐ {rating.toFixed(1)}
    </div>
  );
}
