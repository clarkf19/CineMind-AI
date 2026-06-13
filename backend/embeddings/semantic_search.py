from __future__ import annotations

import logging
import re
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

try:
    from backend.faiss.vector_store import MovieVectorStore
    from backend.recommenders.content_based import ContentBasedRecommender
except ModuleNotFoundError:
    project_root = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(project_root))
    from backend.faiss.vector_store import MovieVectorStore
    from backend.recommenders.content_based import ContentBasedRecommender

logger = logging.getLogger(__name__)

QUERY_EXPANSIONS: dict[str, list[str]] = {
    "mind bending": [
        "psychological thriller",
        "reality manipulation",
        "simulation",
        "consciousness",
        "dream layers",
        "memory",
    ],
    "sci fi": [
        "science fiction",
        "futuristic technology",
        "space",
        "time travel",
        "AI",
    ],
    "science fiction": [
        "futuristic technology",
        "space",
        "time travel",
        "alternate realities",
        "AI",
    ],
    "time travel": [
        "paradox",
        "alternate timeline",
        "future",
        "causality",
    ],
    "space": [
        "astronauts",
        "universe",
        "galaxy",
        "exploration",
    ],
    "AI": [
        "artificial intelligence",
        "machine learning",
        "robots",
        "consciousness",
    ],
    "cyberpunk": [
        "dystopian future",
        "hacking",
        "virtual reality",
        "corporations",
    ],
    "crime": [
        "detective",
        "investigation",
        "mystery",
        "thriller",
    ],
    "mystery": [
        "detective",
        "investigation",
        "suspense",
        "crime",
    ],
}

GENRE_BOOST_TERMS: dict[str, float] = {
    "science fiction": 0.16,
    "thriller": 0.15,
    "action": 0.10,
    "romance": 0.08,
    "comedy": 0.08,
    "crime": 0.10,
    "mystery": 0.12,
    "psychological thriller": 0.14,
    "sci-fi": 0.16,
}

GENRE_PATTERNS = {
    term: re.compile(rf"\b{re.escape(term)}\b", re.I)
    for term in GENRE_BOOST_TERMS
}

KEYWORD_MATCH_TERMS: dict[str, list[str]] = {
    "dream": ["dream", "subconscious", "sleep", "lucid", "mind bending"],
    "time travel": ["time travel", "paradox", "timeline", "future", "causality"],
    "AI": ["artificial intelligence", "robot", "machine learning", "AI", "android"],
    "space": ["space", "astronaut", "universe", "galaxy", "exploration"],
    "simulation": ["simulation", "virtual reality", "alternate reality", "matrix"],
    "crime": ["detective", "murder", "mystery", "heist", "investigation"],
}

NORMALIZE_PATTERN = re.compile(r"[^a-z0-9 ]+")


@dataclass(frozen=True)
class MovieRecommendation:
    title: str
    semantic_score: float
    genre_score: float
    keyword_score: float
    content_score: float
    rating_score: float
    popularity_score: float
    final_score: float
    reasons: list[str]
    id: int | None = None
    release_date: str | None = None


class SemanticMovieSearch:

    def __init__(self):
        self.model = SentenceTransformer(
            "sentence-transformers/all-MiniLM-L6-v2"
        )
        self.store = MovieVectorStore()
        self.store.load_index()
        self.content_recommender = ContentBasedRecommender()
        
        # Load extra TMDB metadata for id and release_date enrichment
        try:
            import pandas as pd
            tmdb_path = Path(self.store.metadata_path).resolve().parents[2] / "data" / "tmdb" / "tmdb_5000_movies.csv" / "tmdb_5000_movies.csv"
            if tmdb_path.exists():
                logger.info("Loading extra TMDB metadata from %s", tmdb_path)
                tmdb_df = pd.read_csv(tmdb_path)
                self.tmdb_lookup = {}
                for _, row in tmdb_df.iterrows():
                    t = str(row.get("title", "")).strip().lower()
                    if t:
                        self.tmdb_lookup[t] = {
                            "id": row.get("id"),
                            "release_date": row.get("release_date")
                        }
            else:
                logger.warning("Extra TMDB metadata not found at %s", tmdb_path)
                self.tmdb_lookup = {}
        except Exception as e:
            logger.error("Failed to load extra TMDB metadata: %s", e)
            self.tmdb_lookup = {}

    def search(self, query: str, top_n: int = 10) -> list[dict[str, object]]:
        if top_n <= 0:
            raise ValueError("top_n must be greater than zero.")

        query_text = str(query).strip()
        if not query_text:
            raise ValueError("query must be a non-empty string.")

        expanded_query = self._expand_query(query_text)
        query_embedding = self.model.encode(
            [expanded_query],
            convert_to_numpy=True,
            show_progress_bar=False,
        )
        self._normalize_vector(query_embedding)

        top_k = max(100, top_n * 10)
        scores, indices = self.store.index.search(query_embedding, top_k)

        candidate_indices = [int(idx) for idx in indices[0] if idx >= 0]
        semantic_scores = [float(score) for score in scores[0][: len(candidate_indices)]]

        if not candidate_indices:
            return []

        candidate_indices, semantic_scores = self._compact_candidates(
            candidate_indices, semantic_scores
        )

        content_scores = self._score_content(expanded_query, candidate_indices)
        genre_scores = self._score_genres(query_text, candidate_indices)
        keyword_scores = self._score_keywords(query_text, candidate_indices)
        rating_scores, popularity_scores = self._score_popularity_and_rating(candidate_indices)

        matches: list[MovieRecommendation] = []
        for idx, sem_score, cont_score, gen_score, keyword_score, rating_score, popularity_score in zip(
            candidate_indices,
            semantic_scores,
            content_scores,
            genre_scores,
            keyword_scores,
            rating_scores,
            popularity_scores,
        ):
            final_score = (
                0.40 * sem_score
                + 0.15 * gen_score
                + 0.15 * keyword_score
                + 0.10 * cont_score
                + 0.15 * rating_score
                + 0.05 * popularity_score
            )

            reasons = self._build_reasons(
                query_text,
                gen_score,
                keyword_score,
                cont_score,
                rating_score,
                popularity_score,
            )

            title = str(self.store.metadata.iloc[idx]["title"])
            extra_info = self.tmdb_lookup.get(title.strip().lower(), {})
            movie_id = extra_info.get("id")
            release_date = extra_info.get("release_date")
            import pandas as pd

            matches.append(
                MovieRecommendation(
                    title=title,
                    semantic_score=round(sem_score, 4),
                    genre_score=round(gen_score, 4),
                    keyword_score=round(keyword_score, 4),
                    content_score=round(cont_score, 4),
                    rating_score=round(rating_score, 4),
                    popularity_score=round(popularity_score, 4),
                    final_score=round(final_score, 4),
                    reasons=reasons,
                    id=int(movie_id) if movie_id is not None and not pd.isna(movie_id) else None,
                    release_date=str(release_date) if release_date is not None and not pd.isna(release_date) else None,
                )
            )

        matches.sort(key=lambda match: match.final_score, reverse=True)
        return [match.__dict__ for match in matches[:top_n]]

    def _expand_query(self, query: str) -> str:
        normalized = query.lower()
        expanded_terms: list[str] = [query]
        for phrase, synonyms in QUERY_EXPANSIONS.items():
            if phrase in normalized:
                expanded_terms.extend(synonyms)
        return " ".join(expanded_terms)

    def _score_content(self, query: str, candidate_indices: list[int]) -> list[float]:
        query_vector = self.content_recommender.vectorizer.transform([query])
        candidate_matrix = self.content_recommender.tfidf_matrix[candidate_indices]
        similarity = cosine_similarity(query_vector, candidate_matrix).flatten()
        return self._normalize_scores(similarity)

    def _score_genres(self, query: str, candidate_indices: list[int]) -> list[float]:
        normalized = query.lower()
        boosts: list[float] = []
        for idx in candidate_indices:
            genre_cell = str(self.store.metadata.iloc[idx].get("genres", ""))
            genre_tokens = {token.strip().lower() for token in genre_cell.split("|") if token.strip()}
            boost_value = 0.0
            for term, weight in GENRE_BOOST_TERMS.items():
                if GENRE_PATTERNS[term].search(normalized) and term in genre_tokens:
                    boost_value += weight
            boosts.append(boost_value)
        return self._normalize_scores(np.array(boosts, dtype=float))

    def _score_keywords(self, query: str, candidate_indices: list[int]) -> list[float]:
        normalized = query.lower()
        boosts: list[float] = []
        for idx in candidate_indices:
            keyword_cell = str(self.store.metadata.iloc[idx].get("keywords", ""))
            keyword_tokens = {token.strip().lower() for token in keyword_cell.split("|") if token.strip()}
            score = 0.0
            for synonyms in KEYWORD_MATCH_TERMS.values():
                if any(re.search(rf"\b{re.escape(term)}\b", normalized) for term in synonyms):
                    score += float(len(keyword_tokens.intersection({term.lower() for term in synonyms})))
            boosts.append(score)
        return self._normalize_scores(np.array(boosts, dtype=float))

    def _score_popularity_and_rating(self, candidate_indices: list[int]) -> tuple[list[float], list[float]]:
        raw_weighted_ratings: list[float] = []
        raw_popularities: list[float] = []
        for idx in candidate_indices:
            row = self.store.metadata.iloc[idx]
            vote_average = float(row.get("vote_average", 0.0) or 0.0)
            vote_count = float(row.get("vote_count", 0) or 0.0)
            popularity = float(row.get("popularity", 0.0) or 0.0)
            rating_score = vote_average / 10.0
            confidence_score = np.log1p(vote_count)
            raw_weighted_ratings.append(rating_score * confidence_score)
            raw_popularities.append(popularity)

        normalized_ratings = self._normalize_scores(np.array(raw_weighted_ratings, dtype=float))
        normalized_popularities = self._normalize_scores(np.array(raw_popularities, dtype=float))
        return normalized_ratings, normalized_popularities

    def _compact_candidates(self, indices: list[int], scores: list[float]) -> tuple[list[int], list[float]]:
        seen: dict[int, float] = {}
        for idx, score in zip(indices, scores):
            if idx not in seen or score > seen[idx]:
                seen[idx] = score
        unique_indices = list(seen.keys())
        unique_scores = [seen[idx] for idx in unique_indices]
        return unique_indices, unique_scores

    def _build_reasons(
        self,
        query: str,
        genre_score: float,
        keyword_score: float,
        content_score: float,
        rating_score: float,
        popularity_score: float,
    ) -> list[str]:
        reasons: list[str] = []
        if genre_score >= 0.15:
            reasons.append("Strong genre match to the query")
        if keyword_score >= 0.15:
            reasons.append("Relevant thematic keywords matched")
        if content_score >= 0.25:
            reasons.append("Content similarity supports the query")
        if rating_score >= 0.25:
            reasons.append("Highly rated by audiences")
        if popularity_score >= 0.25:
            reasons.append("Popular with viewers")
        if not reasons:
            reasons.append("Good semantic relevance to the query")
        return reasons

    @staticmethod
    def _normalize_scores(raw_scores: np.ndarray) -> list[float]:
        if raw_scores.size == 0:
            return []
        min_val = float(np.min(raw_scores))
        max_val = float(np.max(raw_scores))
        if max_val == min_val:
            if max_val == 0.0:
                return [0.0 for _ in raw_scores]
            return [1.0 for _ in raw_scores]
        return [float((score - min_val) / (max_val - min_val)) for score in raw_scores]

    @staticmethod
    def _normalize_vector(vector: np.ndarray) -> None:
        norm = np.linalg.norm(vector)
        if norm > 0.0:
            vector /= norm


if __name__ == "__main__":

    search_engine = SemanticMovieSearch()

    test_queries = [
        "mind bending science fiction movies",
        "time travel movies",
        "space exploration movies",
        "artificial intelligence movies",
        "psychological thrillers"
    ]

    for query in test_queries:

        print("\n" + "=" * 60)
        print(f"QUERY: {query}")
        print("=" * 60)

        results = search_engine.search(
            query,
            top_n=10
        )

        for movie in results:
            print(movie)
