interface SuggestionChipProps {
  label: string;
  onClick: () => void;
}

export function SuggestionChip({ label, onClick }: SuggestionChipProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="rounded-full border border-white/10 bg-white/5 px-4 py-2 text-sm text-slate-200 transition hover:border-white/20 hover:bg-white/10"
    >
      {label}
    </button>
  );
}
