interface ReasonBadgeProps {
  reason: string;
}

export function ReasonBadge({ reason }: ReasonBadgeProps) {
  return (
    <span className="rounded-full bg-white/5 px-3 py-2 text-xs text-slate-200 shadow-sm">
      {reason}
    </span>
  );
}
