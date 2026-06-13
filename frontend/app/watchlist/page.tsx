"use client";

import { useWatchlist } from "../../contexts/WatchlistContext";
import { MovieCard } from "../../components/movie/MovieCard";
import { Container } from "../../components/layout/Container";
import Link from "next/link";

export default function WatchlistPage() {
  const { watchlist } = useWatchlist();

  return (
    <Container>
      <section className="space-y-8 py-16">
        <div className="max-w-3xl space-y-4">
          <p className="text-sm uppercase tracking-[0.4em] text-slate-500">Favorites</p>
          <h1 className="text-4xl font-semibold text-white sm:text-5xl">Your Watchlist</h1>
          <p className="max-w-2xl text-slate-300">
            Keep track of the movies that match your mood and ideas.
          </p>
        </div>
      </section>

      <section className="pb-16">
        {watchlist.length === 0 ? (
          <div className="flex flex-col items-center justify-center rounded-4xl border border-white/10 bg-white/5 py-24 text-center backdrop-blur-xl animate-fadeIn">
            <div className="flex h-16 w-16 items-center justify-center rounded-full border border-rose-500/30 bg-rose-500/10 text-rose-400">
              <svg
                viewBox="0 0 24 24"
                className="h-8 w-8"
                fill="none"
                stroke="currentColor"
                strokeWidth={2}
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M21 8.25c0-2.485-2.099-4.5-4.688-4.5-1.935 0-3.597 1.126-4.312 2.733-.715-1.607-2.377-2.733-4.313-2.733C5.1 3.75 3 5.765 3 8.25c0 7.22 9 12 9 12s9-4.78 9-12z"
                />
              </svg>
            </div>
            <h2 className="mt-6 text-xl font-medium text-white">Your watchlist is empty</h2>
            <p className="mt-2 max-w-sm text-sm leading-relaxed text-slate-400">
              Explore recommendations and click the heart icon to save movies you want to watch.
            </p>
            <Link
              href="/search"
              className="mt-8 rounded-full bg-violet-600 px-6 py-3 text-sm font-semibold text-white shadow-lg shadow-violet-600/35 transition hover:bg-violet-500 hover:shadow-violet-500/40"
            >
              Discover Movies
            </Link>
          </div>
        ) : (
          <div className="grid gap-6 sm:grid-cols-2 xl:grid-cols-3">
            {watchlist.map((movie) => (
              <MovieCard key={movie.id} movie={movie} />
            ))}
          </div>
        )}
      </section>
    </Container>
  );
}
