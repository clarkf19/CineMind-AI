"use client";

import { useState, useEffect } from "react";
import { Movie } from "../types/movie";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

function slugify(text: string) {
  return text
    .toString()
    .toLowerCase()
    .replace(/\s+/g, "-")
    .replace(/[^\u0000-\u007F-]+/g, "")
    .replace(/[^a-z0-9-]/g, "")
    .replace(/-+/g, "-")
    .replace(/^-|-$/g, "");
}

function mapApiResultToMovie(item: any): Movie {
  const id = item.id ? String(item.id) : slugify(item.title || "unknown");
  const releaseYear = item.release_date ? String(item.release_date).split("-")[0] : "";
  return {
    id,
    title: item.title || "",
    releaseYear,
    posterUrl: "",
    genres: Array.isArray(item.genres) ? item.genres : [],
    rating: typeof item.vote_average === "number" ? item.vote_average : 0,
    recommendationScore: Math.round(
      (item.final_score !== undefined && item.final_score !== null
        ? item.final_score
        : item.similarity_score || 0) * 100
    ),
    overview: item.overview || "",
    reasons: Array.isArray(item.reasons) ? item.reasons : [],
    semanticScore: typeof item.semantic_score === "number" ? item.semantic_score : 0,
    genreScore: typeof item.genre_score === "number" ? item.genre_score : 0,
    popularityScore: typeof item.popularity_score === "number" ? item.popularity_score : 0,
    ratingScore: typeof item.rating_score === "number" ? item.rating_score : 0,
    contentScore: typeof item.content_score === "number" ? item.content_score : 0,
  } as Movie;
}

export const useMovieDetail = (movieId: string) => {
  const [movie, setMovie] = useState<Movie | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!movieId) return;

    // Convert the slug/id back to a searchable title
    const titleQuery = movieId.replace(/-/g, " ");

    const fetchMovie = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const res = await fetch(`${API_BASE}/search?q=${encodeURIComponent(titleQuery)}`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        const items: any[] = Array.isArray(data.results) ? data.results : [];

        // Try to find an exact match by id or title
        const match =
          items.find((item) => String(item.id) === movieId) ||
          items.find(
            (item) =>
              slugify(item.title || "") === movieId ||
              String(item.title || "").toLowerCase() === titleQuery.toLowerCase()
          ) ||
          items[0];

        if (match) {
          setMovie(mapApiResultToMovie(match));
        } else {
          setError("Movie not found.");
        }
      } catch (err: any) {
        setError(err?.message || "Failed to load movie.");
      } finally {
        setIsLoading(false);
      }
    };

    fetchMovie();
  }, [movieId]);

  return { movie, isLoading, error };
};
