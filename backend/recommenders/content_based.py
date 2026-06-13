"""Content-based movie recommendations built from TMDB metadata.

This module loads the TMDB 5000 movie and credits datasets, builds a textual
profile for each movie from genres, keywords, cast, director, and overview, and
uses TF-IDF cosine similarity to recommend related titles.
"""

from __future__ import annotations

import ast
import logging
from pathlib import Path
from typing import Any, TypedDict

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


logger = logging.getLogger(__name__)


class MovieRecommendation(TypedDict):
    """Public recommendation response shape."""

    title: str
    similarity_score: float
    genres: list[str]
    overview: str


class ContentBasedRecommender:
    """Recommend movies by comparing TF-IDF profiles built from TMDB metadata.

    Parameters
    ----------
    movies_path:
        Optional path to ``tmdb_5000_movies.csv``. Defaults to the project
        ``data/tmdb`` location.
    credits_path:
        Optional path to ``tmdb_5000_credits.csv``. Defaults to the project
        ``data/tmdb`` location.
    top_cast_count:
        Number of cast members to include in each movie profile.
    """

    REQUIRED_MOVIES_COLUMNS = {"title", "genres", "keywords", "overview"}
    REQUIRED_CREDITS_COLUMNS = {"title", "cast", "crew"}

    def __init__(
        self,
        movies_path: str | Path | None = None,
        credits_path: str | Path | None = None,
        top_cast_count: int = 5,
    ) -> None:
        if top_cast_count <= 0:
            raise ValueError("top_cast_count must be greater than zero.")

        project_root = Path(__file__).resolve().parents[2]
        self.movies_path = self._resolve_csv_path(
            Path(movies_path)
            if movies_path is not None
            else project_root / "data" / "tmdb" / "tmdb_5000_movies.csv"
        )
        self.credits_path = self._resolve_csv_path(
            Path(credits_path)
            if credits_path is not None
            else project_root / "data" / "tmdb" / "tmdb_5000_credits.csv"
        )
        self.top_cast_count = top_cast_count

        self.movies: pd.DataFrame
        self.title_to_index: dict[str, int]
        self.vectorizer: TfidfVectorizer
        self.tfidf_matrix: Any
        self.cosine_similarities: Any

        logger.info("Initializing content-based recommender.")
        self._fit()

    def recommend(self, movie_title: str, top_n: int = 10) -> list[MovieRecommendation]:
        """Return the most similar movies for a given title.

        Parameters
        ----------
        movie_title:
            Title to search for. Matching is case-insensitive and ignores
            leading/trailing whitespace.
        top_n:
            Maximum number of recommendations to return.

        Raises
        ------
        ValueError
            If ``movie_title`` is empty, ``top_n`` is not positive, or the title
            does not exist in the loaded dataset.
        """

        normalized_title = self._normalize_title(movie_title)
        if not normalized_title:
            raise ValueError("movie_title must be a non-empty string.")
        if top_n <= 0:
            raise ValueError("top_n must be greater than zero.")
        if normalized_title not in self.title_to_index:
            raise ValueError(f"Movie title not found in dataset: {movie_title!r}")

        movie_index = self.title_to_index[normalized_title]
        similarity_scores = list(enumerate(self.cosine_similarities[movie_index]))
        similarity_scores = sorted(
            similarity_scores,
            key=lambda item: item[1],
            reverse=True,
        )

        recommendations: list[MovieRecommendation] = []
        for candidate_index, score in similarity_scores:
            if candidate_index == movie_index:
                continue

            movie = self.movies.iloc[candidate_index]
            recommendations.append(
                {
                    "title": str(movie["title"]),
                    "similarity_score": round(float(score), 4),
                    "genres": list(movie["genres"]),
                    "overview": str(movie["overview"]),
                }
            )

            if len(recommendations) == top_n:
                break

        logger.info(
            "Generated %d recommendations for %r.",
            len(recommendations),
            movie_title,
        )
        return recommendations

    def _fit(self) -> None:
        """Load data, build movie profiles, and compute cosine similarities."""

        movies = self._load_csv(self.movies_path, self.REQUIRED_MOVIES_COLUMNS)
        credits = self._load_csv(self.credits_path, self.REQUIRED_CREDITS_COLUMNS)

        logger.info("Merging TMDB movies and credits datasets on title.")
        merged = movies.merge(credits, on="title", how="inner")
        if merged.empty:
            raise ValueError("Merged TMDB dataset is empty. Check title alignment.")

        self.movies = self._prepare_features(merged)
        self.title_to_index = self._build_title_index(self.movies["title"])

        self.vectorizer = TfidfVectorizer(stop_words="english")
        self.tfidf_matrix = self.vectorizer.fit_transform(self.movies["combined_features"])
        self.cosine_similarities = cosine_similarity(self.tfidf_matrix)

        logger.info(
            "Content-based recommender ready with %d movies and %d TF-IDF terms.",
            self.tfidf_matrix.shape[0],
            self.tfidf_matrix.shape[1],
        )

    def _prepare_features(self, movies: pd.DataFrame) -> pd.DataFrame:
        """Extract structured metadata and create a combined text feature."""

        prepared = movies.copy()
        prepared["genres"] = prepared["genres"].apply(self._extract_names)
        prepared["keywords"] = prepared["keywords"].apply(self._extract_names)
        prepared["cast"] = prepared["cast"].apply(
            lambda value: self._extract_names(value, limit=self.top_cast_count)
        )
        prepared["director"] = prepared["crew"].apply(self._extract_director)
        prepared["overview"] = prepared["overview"].fillna("").astype(str)
        prepared["combined_features"] = prepared.apply(self._combine_features, axis=1)

        return prepared[
            ["title", "genres", "overview", "combined_features"]
        ].reset_index(drop=True)

    def _combine_features(self, row: pd.Series) -> str:
        """Create one searchable text profile from a prepared movie row."""

        profile_parts = [
            self._tokenize_names(row["genres"]),
            self._tokenize_names(row["keywords"]),
            self._tokenize_names(row["cast"]),
            self._tokenize_names([row["director"]]),
            row["overview"],
        ]
        return " ".join(part for part in profile_parts if part).lower()

    @staticmethod
    def _resolve_csv_path(path: Path) -> Path:
        """Resolve CSV paths, including directories that contain same-named CSVs."""

        if path.is_file():
            return path

        nested_path = path / path.name
        if path.is_dir() and nested_path.is_file():
            return nested_path

        raise FileNotFoundError(f"CSV file not found: {path}")

    @staticmethod
    def _load_csv(path: Path, required_columns: set[str]) -> pd.DataFrame:
        """Load a CSV and validate that required columns are present."""

        logger.info("Loading CSV: %s", path)
        try:
            data = pd.read_csv(path)
        except Exception as exc:
            logger.exception("Failed to load CSV: %s", path)
            raise RuntimeError(f"Failed to load CSV: {path}") from exc

        missing_columns = required_columns.difference(data.columns)
        if missing_columns:
            missing = ", ".join(sorted(missing_columns))
            raise ValueError(f"CSV {path} is missing required columns: {missing}")

        return data

    @classmethod
    def _extract_names(cls, value: Any, limit: int | None = None) -> list[str]:
        """Extract ``name`` values from TMDB JSON-like list columns."""

        items = cls._parse_json_like_list(value)
        names = [
            str(item.get("name", "")).strip()
            for item in items
            if isinstance(item, dict) and item.get("name")
        ]
        return names[:limit] if limit is not None else names

    @classmethod
    def _extract_director(cls, value: Any) -> str:
        """Extract the director name from a TMDB crew column."""

        crew_members = cls._parse_json_like_list(value)
        for member in crew_members:
            if isinstance(member, dict) and member.get("job") == "Director":
                return str(member.get("name", "")).strip()
        return ""

    @staticmethod
    def _parse_json_like_list(value: Any) -> list[Any]:
        """Safely parse TMDB columns stored as stringified Python lists."""

        if isinstance(value, list):
            return value
        if pd.isna(value):
            return []
        if not isinstance(value, str) or not value.strip():
            return []

        try:
            parsed = ast.literal_eval(value)
        except (SyntaxError, ValueError):
            logger.warning("Unable to parse TMDB metadata value: %r", value)
            return []

        return parsed if isinstance(parsed, list) else []

    @staticmethod
    def _tokenize_names(names: list[str]) -> str:
        """Normalize multi-word names into stable single tokens."""

        return " ".join(name.replace(" ", "").lower() for name in names if name)

    @classmethod
    def _build_title_index(cls, titles: pd.Series) -> dict[str, int]:
        """Build a case-insensitive title lookup table."""

        title_to_index: dict[str, int] = {}
        for index, title in titles.items():
            normalized_title = cls._normalize_title(str(title))
            if normalized_title and normalized_title not in title_to_index:
                title_to_index[normalized_title] = int(index)

        return title_to_index

    @staticmethod
    def _normalize_title(title: str) -> str:
        """Normalize user and dataset titles for lookup."""

        return title.strip().casefold()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    recommender = ContentBasedRecommender()
    print(recommender.recommend("Inception"))
