"use client";

import Link from "next/link";
import { useWatchlist } from "../../contexts/WatchlistContext";

export function Navbar() {
  const { watchlist } = useWatchlist();
  const count = watchlist.length;

  return (
    <nav className="relative z-20 border-b border-white/10 bg-black/60 backdrop-blur-xl">
      <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-5 xl:px-0">
        <Link href="/" className="text-lg font-semibold tracking-tight text-white">
          CineMind AI
        </Link>

        <div className="flex items-center gap-4 text-sm text-slate-300">
          <Link href="/search" className="rounded-full border border-white/10 bg-white/5 px-4 py-2 transition hover:border-white/20 hover:bg-white/10">
            Discover
          </Link>
          
          <Link
            href="/watchlist"
            className="flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-4 py-2 transition hover:border-white/20 hover:bg-white/10"
          >
            <span>Watchlist</span>
            <svg
              viewBox="0 0 24 24"
              className={`h-4 w-4 ${count > 0 ? "fill-rose-500 text-rose-500" : "text-slate-400"}`}
              stroke="currentColor"
              strokeWidth={2}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M21 8.25c0-2.485-2.099-4.5-4.688-4.5-1.935 0-3.597 1.126-4.312 2.733-.715-1.607-2.377-2.733-4.313-2.733C5.1 3.75 3 5.765 3 8.25c0 7.22 9 12 9 12s9-4.78 9-12z"
              />
            </svg>
            {count > 0 && (
              <span className="flex h-5 w-5 items-center justify-center rounded-full bg-rose-500 text-[10px] font-bold text-white">
                {count}
              </span>
            )}
          </Link>

          <Link href="/" className="rounded-full px-4 py-2 text-white transition hover:bg-white/10">
            About
          </Link>
        </div>
      </div>
    </nav>
  );
}
