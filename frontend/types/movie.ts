export interface Movie {
  id: string;
  title: string;
  releaseYear: string;
  posterUrl: string;
  genres: string[];
  rating: number;
  recommendationScore: number;
  overview: string;
  reasons: string[];
  semanticScore: number;
  genreScore: number;
  popularityScore: number;
  ratingScore: number;
  contentScore: number;
}
