"use client";

import { useMemo } from "react";
import { Movie } from "../types/movie";

export const useRecommendations = (movies: Movie[]) => {
  return useMemo(
    () => movies.sort((a, b) => b.recommendationScore - a.recommendationScore),
    [movies]
  );
};
