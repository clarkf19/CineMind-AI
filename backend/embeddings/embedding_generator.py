"""Generate semantic movie embeddings for CineMind-AI.

This module builds text profiles for TMDB movies, generates Sentence
Transformer embeddings, saves artifact files to ``data/embeddings``, and
provides a cosine similarity search API for related movies.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer
from tqdm import tqdm

try:
    from backend.recommenders.content_based import ContentBasedRecommender
except ModuleNotFoundError as exc:
    if exc.name != "backend":
        raise
    project_root = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(project_root))
    from backend.recommenders.content_based import ContentBasedRecommender

logger = logging.getLogger(__name__)


class MovieEmbeddingGenerator:
    """Generate and search movie embeddings from TMDB metadata."""

    DEFAULT_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
    REQUIRED_MOVIE_COLUMNS = {
        "id",
        "title",
        "genres",
        "keywords",
        "overview",
        "vote_average",
        "vote_count",
        "popularity",
    }
    REQUIRED_CREDITS_COLUMNS = {"movie_id", "title", "cast", "crew"}

    def __init__(
        self,
        movies_path: str | Path | None = None,
        credits_path: str | Path | None = None,
        output_dir: str | Path | None = None,
        model_name: str = DEFAULT_MODEL_NAME,
        batch_size: int = 64,
    ) -> None:
        if batch_size <= 0:
            raise ValueError("batch_size must be greater than zero.")

        self.project_root = Path(__file__).resolve().parents[2]
        tmdb_dir = self.project_root / "data" / "tmdb"

        self.movies_path = self._resolve_csv_path(
            Path(movies_path)
            if movies_path is not None
            else tmdb_dir / "tmdb_5000_movies.csv",
            fallback_dir=tmdb_dir,
            fallback_names=("tmdb_5000_movies.csv", "tmdb_5000_movies.csv"),
        )
        self.credits_path = self._resolve_csv_path(
            Path(credits_path)
            if credits_path is not None
            else tmdb_dir / "tmdb_5000_credits.csv",
            fallback_dir=tmdb_dir,
            fallback_names=("tmdb_5000_credits.csv", "tmdb_5000_credits.csv"),
        )
        self.output_dir = (
            Path(output_dir)
            if output_dir is not None
            else self.project_root / "data" / "embeddings"
        )
        self.embeddings_path = self.output_dir / "movie_embeddings.npy"
        self.metadata_path = self.output_dir / "movie_metadata.csv"
        self.model_name = model_name
        self.batch_size = batch_size

        self.model = self._load_model()
        self.movies = self._load_and_prepare_movies()
        self.title_to_index = {
            self._normalize_title(title): idx
            for idx, title in enumerate(self.movies["title"].astype(str))
            if self._normalize_title(title)
        }
        self.embeddings: np.ndarray | None = None

        logger.info(
            "MovieEmbeddingGenerator initialized with %d movies.",
            len(self.movies),
        )

    def generate_embeddings(self) -> None:
        """Generate embeddings for all movies and save artifacts to disk."""

        if self.movies.empty:
            raise RuntimeError("No TMDB movies available to embed.")

        texts = [self._build_text_profile(row) for _, row in self.movies.iterrows()]
        embedding_batches: list[np.ndarray] = []
        logger.info(
            "Generating embeddings for %d movies using %s.",
            len(texts),
            self.model_name,
        )

        for start in tqdm(
            range(0, len(texts), self.batch_size),
            desc="Embedding movies",
            unit="batch",
        ):
            batch_texts = texts[start : start + self.batch_size]
            try:
                batch_embeddings = self.model.encode(
                    batch_texts,
                    show_progress_bar=False,
                    batch_size=self.batch_size,
                    convert_to_numpy=True,
                )
            except Exception as exc:
                logger.exception("SentenceTransformer failed during embedding.")
                raise RuntimeError("Failed to generate movie embeddings.") from exc
            embedding_batches.append(batch_embeddings)

        self.embeddings = np.vstack(embedding_batches)
        self._save_embeddings()

    def build_faiss_index(self) -> None:
        """Build or rebuild the FAISS index from the current embeddings."""

        try:
            from backend.faiss.vector_store import MovieVectorStore
        except ModuleNotFoundError as exc:
            if exc.name != "backend":
                raise
            project_root = Path(__file__).resolve().parents[2]
            sys.path.insert(0, str(project_root))
            from backend.faiss.vector_store import MovieVectorStore

        vector_store = MovieVectorStore()
        vector_store.build_index()

    def search_similar_movies(
        self,
        movie_title: str,
        top_n: int = 10,
    ) -> list[dict[str, float]]:
        """Return the most semantically similar movies for a given title."""

        if top_n <= 0:
            raise ValueError("top_n must be greater than zero.")
        if not movie_title.strip():
            raise ValueError("movie_title must be a non-empty string.")

        if self.embeddings is None:
            if self.embeddings_path.exists() and self.metadata_path.exists():
                self._load_embeddings()
            else:
                raise RuntimeError(
                    "Embeddings are not available. Call generate_embeddings() first."
                )

        normalized_title = self._normalize_title(movie_title)
        movie_index = self.title_to_index.get(normalized_title)
        if movie_index is None:
            raise ValueError(f"Movie title not found: {movie_title!r}")

        assert self.embeddings is not None
        query_embedding = self.embeddings[movie_index]
        all_embeddings = self.embeddings

        query_norm = np.linalg.norm(query_embedding)
        if query_norm == 0.0:
            raise RuntimeError("Query embedding has zero norm.")

        norms = np.linalg.norm(all_embeddings, axis=1)
        safe_norms = np.where(norms == 0.0, 1.0, norms)
        similarities = np.dot(all_embeddings, query_embedding) / (safe_norms * query_norm)
        similarities = np.nan_to_num(similarities, nan=0.0, neginf=0.0, posinf=0.0)
        similarities[movie_index] = -np.inf

        top_indices = np.argpartition(-similarities, min(top_n, len(similarities) - 1))[
            : min(top_n, len(similarities) - 1)
        ]
        top_indices = top_indices[np.argsort(-similarities[top_indices])]

        results: list[dict[str, float]] = []
        for index in top_indices:
            results.append(
                {
                    "title": str(self.movies.iloc[index]["title"]),
                    "similarity_score": round(float(similarities[index]), 4),
                }
            )
        return results

    def _load_model(self) -> SentenceTransformer:
        """Load the Sentence Transformer model."""

        try:
            return SentenceTransformer(self.model_name)
        except Exception as exc:
            logger.exception("Failed to load SentenceTransformer model: %s.", self.model_name)
            raise RuntimeError(
                f"Unable to load embedding model: {self.model_name}"
            ) from exc

    def _load_and_prepare_movies(self) -> pd.DataFrame:
        """Load TMDB movies and credits, merge them, and retain required fields."""

        movies = self._load_csv(self.movies_path, self.REQUIRED_MOVIE_COLUMNS)
        credits = self._load_csv(self.credits_path, self.REQUIRED_CREDITS_COLUMNS)

        movies = movies.rename(columns={"id": "movieId"})
        credits = credits.rename(columns={"movie_id": "movieId"})

        merged = movies.merge(credits, on=["movieId", "title"], how="inner")
        if merged.empty:
            raise ValueError("Merged TMDB dataset is empty. Check title alignment.")

        if "movieId" not in merged.columns:
            raise ValueError("Merged TMDB dataset does not contain movieId after merge.")

        merged = merged.drop_duplicates(subset=["movieId"]).reset_index(drop=True)
        return merged

    def _build_text_profile(self, row: pd.Series) -> str:
        """Build the text representation used for semantic embedding."""

        title = str(row.get("title", "")).strip()
        overview = str(row.get("overview", "")).strip()
        genres = ContentBasedRecommender._extract_names(row.get("genres", ""))
        keywords = ContentBasedRecommender._extract_names(row.get("keywords", ""))
        cast = ContentBasedRecommender._extract_names(row.get("cast", ""), limit=5)
        director = ContentBasedRecommender._extract_director(row.get("crew", ""))

        vote_average = 0.0
        vote_count = 0
        popularity = 0.0
        try:
            vote_average = float(row.get("vote_average", 0.0) or 0.0)
        except (TypeError, ValueError):
            vote_average = 0.0
        try:
            vote_count = int(row.get("vote_count", 0) or 0)
        except (TypeError, ValueError):
            vote_count = 0
        try:
            popularity = float(row.get("popularity", 0.0) or 0.0)
        except (TypeError, ValueError):
            popularity = 0.0

        profile_parts: list[str] = []
        if title:
            profile_parts.extend([title] * 4)
        if genres:
            profile_parts.extend([" ".join(genres)] * 3)
        if keywords:
            keyword_phrase = " ".join(keywords[:10])
            profile_parts.extend([keyword_phrase] * 4)
        if cast:
            profile_parts.extend([" ".join(cast)] * 2)
        if director:
            profile_parts.extend([f"Directed by {director}"] * 3)
        if overview:
            profile_parts.append(overview)

        if vote_average > 0:
            profile_parts.append(f"Rated {vote_average:.1f} out of 10")
        if vote_count > 0:
            profile_parts.append(f"Reviewed by {vote_count} audience members")
        if popularity > 0:
            profile_parts.append(f"Popularity score {popularity:.1f}")

        return ". ".join(part for part in profile_parts if part).strip()

    def _save_embeddings(self) -> None:
        """Save embeddings and metadata artifacts to disk."""

        if self.embeddings is None:
            raise RuntimeError("No embeddings available to save.")

        try:
            self.output_dir.mkdir(parents=True, exist_ok=True)
            np.save(self.embeddings_path, self.embeddings)
            metadata = pd.DataFrame(
                {
                    "movieId": self.movies["movieId"].astype(int),
                    "title": self.movies["title"].astype(str),
                    "genres": [
                        "|".join(ContentBasedRecommender._extract_names(value))
                        for value in self.movies["genres"]
                    ],
                    "keywords": [
                        "|".join(ContentBasedRecommender._extract_names(value))
                        for value in self.movies["keywords"]
                    ],
                    "cast": [
                        "|".join(
                            ContentBasedRecommender._extract_names(value, limit=5)
                        )
                        for value in self.movies["cast"]
                    ],
                    "director": [
                        ContentBasedRecommender._extract_director(value)
                        for value in self.movies["crew"]
                    ],
                    "overview": self.movies["overview"].fillna("").astype(str),
                    "vote_average": self.movies["vote_average"].fillna(0.0).astype(float),
                    "vote_count": self.movies["vote_count"].fillna(0).astype(int),
                    "popularity": self.movies["popularity"].fillna(0.0).astype(float),
                }
            )
            metadata.to_csv(self.metadata_path, index=False)
        except Exception as exc:
            logger.exception("Failed to save embeddings or metadata.")
            raise RuntimeError(
                "Unable to write embeddings artifacts to disk."
            ) from exc

        logger.info(
            "Saved embeddings to %s and metadata to %s.",
            self.embeddings_path,
            self.metadata_path,
        )

    def _load_embeddings(self) -> None:
        """Load precomputed embeddings and ensure metadata matches."""

        if not self.embeddings_path.exists() or not self.metadata_path.exists():
            raise FileNotFoundError("Embedding artifacts not found on disk.")

        try:
            self.embeddings = np.load(self.embeddings_path)
            metadata = pd.read_csv(self.metadata_path)
        except Exception as exc:
            logger.exception("Failed to load embedding artifacts.")
            raise RuntimeError("Unable to load movie embedding artifacts.") from exc

        if len(metadata) != len(self.embeddings):
            raise ValueError(
                "Metadata length does not match number of embeddings."
            )

        self.title_to_index = {
            self._normalize_title(str(title)): int(index)
            for index, title in enumerate(metadata["title"].astype(str))
            if self._normalize_title(str(title))
        }
        self.movies = metadata
        logger.info("Loaded %d embeddings from disk.", len(self.embeddings))

    @staticmethod
    def _load_csv(path: Path, required_columns: set[str]) -> pd.DataFrame:
        """Load CSV and validate that required columns are present."""

        try:
            data = pd.read_csv(path)
        except Exception as exc:
            logger.exception("Failed to load CSV: %s", path)
            raise RuntimeError(f"Unable to load CSV file: {path}") from exc

        missing_columns = required_columns.difference(data.columns)
        if missing_columns:
            missing = ", ".join(sorted(missing_columns))
            raise ValueError(f"CSV {path} is missing required columns: {missing}")

        return data

    @staticmethod
    def _resolve_csv_path(
        path: Path,
        fallback_dir: Path,
        fallback_names: tuple[str, ...],
    ) -> Path:
        """Resolve CSV paths, nested CSV directories, and common filename variants."""

        if path.is_file():
            return path

        nested_path = path / path.name
        if path.is_dir() and nested_path.is_file():
            return nested_path

        for filename in fallback_names:
            candidate = fallback_dir / filename
            if candidate.is_file():
                return candidate
            nested_candidate = candidate / filename
            if candidate.is_dir() and nested_candidate.is_file():
                return nested_candidate

        csv_candidates = sorted(fallback_dir.glob("*.csv"))
        if csv_candidates:
            return csv_candidates[0]

        nested_csv_candidates = sorted(fallback_dir.glob("*/*.csv"))
        if nested_csv_candidates:
            return nested_csv_candidates[0]

        raise FileNotFoundError(f"CSV file not found: {path}")

    @staticmethod
    def _normalize_title(title: str) -> str:
        """Normalize movie titles for lookup."""

        return " ".join(str(title).casefold().split())


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    generator = MovieEmbeddingGenerator()
    generator.generate_embeddings()
    print(generator.search_similar_movies("Inception", top_n=10))
