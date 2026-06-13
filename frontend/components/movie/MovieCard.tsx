"use client";

import Link from "next/link";
import { Movie } from "../../types/movie";
import { GenrePill } from "./GenrePill";
import { MoviePoster } from "./MoviePoster";
import { RatingBadge } from "./RatingBadge";
import { WatchlistButton } from "./WatchlistButton";
import { ScoreBreakdown } from "../recommendation/ScoreBreakdown";
import { useWatchlist } from "../../contexts/WatchlistContext";

interface MovieCardProps {
  movie: Movie;
}

export function MovieCard({ movie }: MovieCardProps) {
  const { isInWatchlist, toggleWatchlist } = useWatchlist();
  const isSaved = isInWatchlist(movie.id);

  const handleWatchlistToggle = (e: React.MouseEvent) => {
    e.preventDefault(); // Prevent navigating to the details page
    e.stopPropagation();
    toggleWatchlist(movie);
  };

  return (
    <Link href={`/movie/${movie.id}`} className="group block transition duration-300 hover:-translate-y-1 hover:border-white/20 hover:bg-white/5">
      <div className="overflow-hidden rounded-4xl border border-white/10 bg-surface/80 shadow-glow">
        <div className="space-y-4 p-5">
          <div className="flex items-start justify-between gap-4">
            <div>
              <h3 className="text-xl font-semibold text-white">{movie.title}</h3>
              <p className="text-sm text-slate-400">{movie.releaseYear}</p>
            </div>
            <div className="flex items-center gap-2">
              <RatingBadge rating={movie.rating} />
              <WatchlistButton isSaved={isSaved} onToggle={handleWatchlistToggle} />
            </div>
          </div>

          <div className="flex flex-wrap gap-2">
            {movie.genres.slice(0, 3).map((genre) => (
              <GenrePill key={genre} label={genre} />
            ))}
          </div>

          {movie.overview && (
            <p className="text-sm leading-relaxed text-slate-400 line-clamp-3">
              {movie.overview}
            </p>
          )}

          {/* Score breakdown visualizer */}
          <ScoreBreakdown
            semanticScore={movie.semanticScore}
            genreScore={movie.genreScore}
            ratingScore={movie.ratingScore}
            popularityScore={movie.popularityScore}
            contentScore={movie.contentScore}
          />

          <div className="rounded-3xl bg-white/5 p-4 text-sm text-slate-300">
            <p className="font-medium text-slate-100">Why Recommended</p>
            <p className="mt-2 text-sm leading-6 text-slate-300">{movie.reasons[0]}</p>
          </div>

          <div className="flex items-center justify-between gap-3 text-sm text-slate-400">
            <span>Recommendation</span>
            <span className="font-semibold text-white">{movie.recommendationScore}%</span>
          </div>
        </div>
      </div>
    </Link>
  );
}
