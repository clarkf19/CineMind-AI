"use client";

interface WatchlistButtonProps {
  isSaved: boolean;
  onToggle: (e: React.MouseEvent) => void;
}

export function WatchlistButton({ isSaved, onToggle }: WatchlistButtonProps) {
  return (
    <button
      onClick={onToggle}
      className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-full border transition-all duration-200 ${
        isSaved
          ? "border-rose-500/50 bg-rose-500/20 text-rose-400 hover:bg-rose-500/30"
          : "border-white/10 bg-white/5 text-slate-500 hover:border-white/20 hover:bg-white/10 hover:text-white"
      }`}
      title={isSaved ? "Remove from watchlist" : "Save to watchlist"}
      aria-label={isSaved ? "Remove from watchlist" : "Save to watchlist"}
    >
      <svg
        viewBox="0 0 24 24"
        className="h-4 w-4 transition-transform duration-200 hover:scale-110"
        fill={isSaved ? "currentColor" : "none"}
        stroke="currentColor"
        strokeWidth={2}
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          d="M21 8.25c0-2.485-2.099-4.5-4.688-4.5-1.935 0-3.597 1.126-4.312 2.733-.715-1.607-2.377-2.733-4.313-2.733C5.1 3.75 3 5.765 3 8.25c0 7.22 9 12 9 12s9-4.78 9-12z"
        />
      </svg>
    </button>
  );
}
