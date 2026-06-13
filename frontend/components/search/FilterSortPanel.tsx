"use client";

export type SortKey = "relevance" | "rating" | "year" | "popularity";

interface FilterSortPanelProps {
  allGenres: string[];
  activeGenres: string[];
  sortBy: SortKey;
  onGenreToggle: (genre: string) => void;
  onSortChange: (sort: SortKey) => void;
  onClear: () => void;
}

const SORT_OPTIONS: { value: SortKey; label: string }[] = [
  { value: "relevance",  label: "Relevance"  },
  { value: "rating",     label: "Rating"     },
  { value: "year",       label: "Year"       },
  { value: "popularity", label: "Popularity" },
];

export function FilterSortPanel({
  allGenres,
  activeGenres,
  sortBy,
  onGenreToggle,
  onSortChange,
  onClear,
}: FilterSortPanelProps) {
  const isDirty = activeGenres.length > 0 || sortBy !== "relevance";

  return (
    <div className="rounded-3xl border border-white/10 bg-white/5 p-4 backdrop-blur-xl space-y-3">
      {/* Header row */}
      <div className="flex items-center justify-between">
        <p className="text-xs uppercase tracking-[0.22em] text-slate-500">Filter &amp; Sort</p>
        {isDirty && (
          <button
            onClick={onClear}
            className="text-xs text-slate-400 transition hover:text-white"
          >
            Clear all
          </button>
        )}
      </div>

      {/* Sort chips */}
      <div className="flex flex-wrap items-center gap-2">
        <span className="shrink-0 text-xs text-slate-500">Sort:</span>
        {SORT_OPTIONS.map(({ value, label }) => (
          <button
            key={value}
            onClick={() => onSortChange(value)}
            className={`rounded-full px-3 py-1 text-xs font-medium transition-all ${
              sortBy === value
                ? "bg-violet-600 text-white shadow shadow-violet-600/30"
                : "border border-white/10 bg-white/5 text-slate-400 hover:border-white/20 hover:text-white"
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {/* Genre filter chips */}
      {allGenres.length > 0 && (
        <div className="flex flex-wrap gap-2">
          <span className="shrink-0 self-center text-xs text-slate-500">Genre:</span>
          {allGenres.map((genre) => {
            const active = activeGenres.includes(genre);
            return (
              <button
                key={genre}
                onClick={() => onGenreToggle(genre)}
                className={`rounded-full px-3 py-1 text-xs font-medium transition-all ${
                  active
                    ? "border border-blue-400/30 bg-blue-600/70 text-white"
                    : "border border-white/10 bg-white/5 text-slate-400 hover:border-white/20 hover:text-white"
                }`}
              >
                {genre}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}
