"use client";

import { use } from "react";
import { MovieDetails } from "../../../components/movie/MovieDetails";
import { useMovieDetail } from "../../../hooks/useMovieDetail";
import { Container } from "../../../components/layout/Container";

interface MoviePageProps {
  params: {
    id: string;
  };
}

export default function MoviePage({ params }: MoviePageProps) {
  const { movie, isLoading, error } = useMovieDetail(params.id);

  if (isLoading) {
    return (
      <Container>
        <div className="flex items-center justify-center py-32">
          <div className="space-y-3 text-center">
            <div className="mx-auto h-8 w-8 animate-spin rounded-full border-2 border-white/20 border-t-white" />
            <p className="text-sm text-slate-400">Loading movie details…</p>
          </div>
        </div>
      </Container>
    );
  }

  if (error || !movie) {
    return (
      <Container>
        <div className="flex items-center justify-center py-32">
          <p className="text-slate-400">{error || "Movie not found."}</p>
        </div>
      </Container>
    );
  }

  return (
    <Container>
      <div className="py-16">
        <MovieDetails movie={movie} />
      </div>
    </Container>
  );
}
