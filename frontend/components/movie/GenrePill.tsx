interface GenrePillProps {
  label: string;
}

export function GenrePill({ label }: GenrePillProps) {
  return (
    <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs uppercase tracking-[0.12em] text-slate-200">
      {label}
    </span>
  );
}
