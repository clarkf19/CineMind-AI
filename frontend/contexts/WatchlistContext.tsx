"use client";

import { createContext, useContext, useState, useEffect, useCallback } from "react";
import { Movie } from "../types/movie";

const STORAGE_KEY = "cinemind_watchlist";

interface WatchlistContextType {
  watchlist: Movie[];
  isInWatchlist: (id: string) => boolean;
  toggleWatchlist: (movie: Movie) => void;
}

const WatchlistContext = createContext<WatchlistContextType>({
  watchlist: [],
  isInWatchlist: () => false,
  toggleWatchlist: () => {},
});

export function WatchlistProvider({ children }: { children: React.ReactNode }) {
  const [watchlist, setWatchlist] = useState<Movie[]>([]);

  useEffect(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored) setWatchlist(JSON.parse(stored));
    } catch {}
  }, []);

  const isInWatchlist = useCallback(
    (id: string) => watchlist.some((m) => m.id === id),
    [watchlist]
  );

  const toggleWatchlist = useCallback((movie: Movie) => {
    setWatchlist((prev) => {
      const exists = prev.some((m) => m.id === movie.id);
      const next = exists ? prev.filter((m) => m.id !== movie.id) : [movie, ...prev];
      try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
      } catch {}
      return next;
    });
  }, []);

  return (
    <WatchlistContext.Provider value={{ watchlist, isInWatchlist, toggleWatchlist }}>
      {children}
    </WatchlistContext.Provider>
  );
}

export const useWatchlist = () => useContext(WatchlistContext);
