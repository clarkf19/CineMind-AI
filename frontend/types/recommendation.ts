export interface RecommendationMetrics {
  semanticScore: number;
  genreScore: number;
  ratingScore: number;
  popularityScore: number;
  contentScore: number;
  finalScore: number;
  reasons: string[];
}
