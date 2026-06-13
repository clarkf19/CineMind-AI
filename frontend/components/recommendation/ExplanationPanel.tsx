import { Movie } from "../../types/movie";
import { ReasonBadge } from "./ReasonBadge";

interface ExplanationPanelProps {
  movie: Movie;
}

export function ExplanationPanel({ movie }: ExplanationPanelProps) {
  return (
    <div className="rounded-4xl border border-white/10 bg-surface/80 p-8 shadow-glow">
      <div className="grid gap-6 lg:grid-cols-[1.4fr_0.9fr]">
        <div className="space-y-4">
          <div>
            <p className="text-xs uppercase tracking-[0.24em] text-slate-500">Recommendation explanation</p>
            <h2 className="mt-3 text-2xl font-semibold text-white">Why CineMind selected this movie</h2>
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <div className="rounded-3xl bg-white/5 p-5">
              <p className="text-sm text-slate-400">Semantic Match</p>
              <p className="mt-3 text-3xl font-semibold text-white">{Math.round(movie.semanticScore * 100)}%</p>
            </div>
            <div className="rounded-3xl bg-white/5 p-5">
              <p className="text-sm text-slate-400">Genre Match</p>
              <p className="mt-3 text-3xl font-semibold text-white">{Math.round(movie.genreScore * 100)}%</p>
            </div>
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <div className="rounded-3xl bg-white/5 p-5">
              <p className="text-sm text-slate-400">Audience Rating</p>
              <p className="mt-3 text-3xl font-semibold text-white">{movie.rating.toFixed(1)}</p>
            </div>
            <div className="rounded-3xl bg-white/5 p-5">
              <p className="text-sm text-slate-400">Popularity</p>
              <p className="mt-3 text-3xl font-semibold text-white">{Math.round(movie.popularityScore * 100)}%</p>
            </div>
          </div>
        </div>

        <div className="space-y-4">
          <div className="rounded-3xl border border-white/10 bg-black/50 p-6">
            <p className="text-sm uppercase tracking-[0.24em] text-slate-500">Reasons</p>
            <div className="mt-4 flex flex-wrap gap-2">
              {movie.reasons.map((reason) => (
                <ReasonBadge key={reason} reason={reason} />
              ))}
            </div>
          </div>

          <div className="rounded-3xl bg-white/5 p-6">
            <p className="text-sm text-slate-400">Final recommendation score</p>
            <p className="mt-3 text-4xl font-semibold text-white">{movie.recommendationScore}%</p>
          </div>
        </div>
      </div>
    </div>
  );
}
