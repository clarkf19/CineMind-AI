"use client";

import { WatchlistProvider } from "../../contexts/WatchlistContext";

export function Providers({ children }: { children: React.ReactNode }) {
  return <WatchlistProvider>{children}</WatchlistProvider>;
}
