import { Movie } from "../../types/movie";
import { GenrePill } from "./GenrePill";
import { RatingBadge } from "./RatingBadge";
import { ExplanationPanel } from "../recommendation/ExplanationPanel";

interface MovieDetailsProps {
  movie: Movie;
}

export function MovieDetails({ movie }: MovieDetailsProps) {
  return (
    <div className="space-y-8">
      <div className="rounded-4xl border border-white/10 bg-surface/80 p-8 shadow-glow">
        <div className="space-y-6">
          <div className="space-y-3">
            <div className="flex flex-wrap items-center gap-3">
              <RatingBadge rating={movie.rating} />
              <span className="text-sm uppercase tracking-[0.24em] text-slate-500">{movie.releaseYear}</span>
            </div>
            <h1 className="text-4xl font-semibold text-white">{movie.title}</h1>
            <div className="flex flex-wrap gap-2">
              {movie.genres.map((genre) => (
                <GenrePill key={genre} label={genre} />
              ))}
            </div>
          </div>

          <div className="rounded-3xl border border-white/10 bg-white/5 p-6 text-slate-200">
            <p className="text-sm leading-7">{movie.overview}</p>
          </div>
        </div>
      </div>

      <ExplanationPanel movie={movie} />
    </div>
  );
}
