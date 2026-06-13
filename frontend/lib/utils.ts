import { Movie } from "../types/movie";

export const formatScore = (score: number) => `${Math.round(score * 100)}%`;

export const getGenreLabel = (genre: string) => genre;

export const mockSearchResults = (query: string, movies: Movie[]) => {
  if (!query) {
    return movies;
  }

  return movies.filter((movie) =>
    movie.title.toLowerCase().includes(query.toLowerCase()) ||
    movie.genres.some((genre) => genre.toLowerCase().includes(query.toLowerCase()))
  );
};
