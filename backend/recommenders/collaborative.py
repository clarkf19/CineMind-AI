"""Collaborative filtering movie recommendations using scikit-learn SVD.

This module trains a matrix-factorization recommender on MovieLens ratings
without scikit-surprise. Ratings are stored in a sparse user-movie matrix,
factorized with ``TruncatedSVD``, and reconstructed on demand for personalized
recommendations.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TypedDict

import numpy as np
import pandas as pd
from scipy.sparse import coo_matrix, csr_matrix
from sklearn.decomposition import TruncatedSVD


logger = logging.getLogger(__name__)


class CollaborativeRecommendation(TypedDict):
    """Public collaborative recommendation response shape."""

    title: str
    predicted_rating: float


class CollaborativeRecommender:
    """Recommend unrated movies for users with sparse matrix factorization.

    Parameters
    ----------
    movies_path:
        Optional path to a MovieLens movies CSV. Defaults to
        ``data/movielens/movie.csv`` and automatically handles common filename
        variants such as ``movies.csv``.
    ratings_path:
        Optional path to a MovieLens ratings CSV. Defaults to
        ``data/movielens/rating.csv`` and automatically handles common filename
        variants such as ``ratings.csv``.
    n_components:
        Number of latent factors for ``TruncatedSVD``.
    random_state:
        Random seed for reproducible factorization.
    rating_bounds:
        Minimum and maximum predicted rating values to return.
    max_ratings:
        Optional cap for development or smoke tests. ``None`` trains on all
        available ratings.
    """

    REQUIRED_MOVIE_COLUMNS = {"movieId", "title"}
    REQUIRED_RATING_COLUMNS = {"userId", "movieId", "rating"}

    def __init__(
        self,
        movies_path: str | Path | None = None,
        ratings_path: str | Path | None = None,
        n_components: int = 100,
        random_state: int = 42,
        rating_bounds: tuple[float, float] = (0.5, 5.0),
        max_ratings: int | None = None,
    ) -> None:
        if n_components <= 0:
            raise ValueError("n_components must be greater than zero.")
        if rating_bounds[0] >= rating_bounds[1]:
            raise ValueError("rating_bounds minimum must be less than maximum.")
        if max_ratings is not None and max_ratings <= 0:
            raise ValueError("max_ratings must be greater than zero when provided.")

        project_root = Path(__file__).resolve().parents[2]
        movielens_dir = project_root / "data" / "movielens"

        self.movies_path = self._resolve_csv_path(
            Path(movies_path)
            if movies_path is not None
            else movielens_dir / "movie.csv",
            fallback_dir=movielens_dir,
            fallback_names=("movie.csv", "movies.csv"),
        )
        self.ratings_path = self._resolve_csv_path(
            Path(ratings_path)
            if ratings_path is not None
            else movielens_dir / "rating.csv",
            fallback_dir=movielens_dir,
            fallback_names=("rating.csv", "ratings.csv"),
        )
        self.n_components = n_components
        self.random_state = random_state
        self.rating_bounds = rating_bounds
        self.max_ratings = max_ratings

        self.movies: pd.DataFrame
        self.ratings: pd.DataFrame
        self.user_to_row: dict[int, int]
        self.row_to_user: dict[int, int]
        self.movie_to_column: dict[int, int]
        self.column_to_movie: dict[int, int]
        self.movie_id_to_title: dict[int, str]
        self.user_mean_ratings: np.ndarray
        self.interaction_matrix: csr_matrix
        self.model: TruncatedSVD
        self.user_factors: np.ndarray

        logger.info("Initializing collaborative recommender.")
        self._fit()

    def recommend_for_user(
        self,
        user_id: int,
        top_n: int = 10,
    ) -> list[CollaborativeRecommendation]:
        """Return top predicted movies the given user has not rated.

        Parameters
        ----------
        user_id:
            MovieLens user identifier.
        top_n:
            Maximum number of recommendations to return.

        Raises
        ------
        ValueError
            If ``top_n`` is not positive or the user does not exist in the
            loaded ratings.
        """

        if top_n <= 0:
            raise ValueError("top_n must be greater than zero.")

        user_row = self.user_to_row.get(int(user_id))
        if user_row is None:
            raise ValueError(f"User ID not found in ratings dataset: {user_id!r}")

        rated_columns = set(self.interaction_matrix[user_row].indices)
        if len(rated_columns) == self.interaction_matrix.shape[1]:
            logger.info("User %s has rated every known movie.", user_id)
            return []

        predicted_ratings = self._predict_user_ratings(user_row)
        if rated_columns:
            predicted_ratings[list(rated_columns)] = -np.inf

        candidate_count = min(top_n, self.interaction_matrix.shape[1] - len(rated_columns))
        top_columns = np.argpartition(-predicted_ratings, candidate_count - 1)[
            :candidate_count
        ]
        top_columns = top_columns[np.argsort(-predicted_ratings[top_columns])]

        recommendations = [
            {
                "title": self.movie_id_to_title[self.column_to_movie[int(column)]],
                "predicted_rating": round(float(predicted_ratings[column]), 4),
            }
            for column in top_columns
            if np.isfinite(predicted_ratings[column])
        ]

        logger.info(
            "Generated %d collaborative recommendations for user %s.",
            len(recommendations),
            user_id,
        )
        return recommendations

    def _fit(self) -> None:
        """Load MovieLens data, build a sparse matrix, and train SVD."""

        self.movies = self._load_movies()
        self.ratings = self._load_ratings()

        self.movie_id_to_title = dict(
            zip(self.movies["movieId"].astype(int), self.movies["title"].astype(str))
        )
        self.user_to_row, self.row_to_user = self._build_index_maps(
            self.ratings["userId"]
        )
        self.movie_to_column, self.column_to_movie = self._build_index_maps(
            self.ratings["movieId"]
        )
        self.user_mean_ratings = self._compute_user_means(self.ratings, self.user_to_row)
        self.interaction_matrix = self._build_interaction_matrix(self.ratings)

        component_count = min(
            self.n_components,
            self.interaction_matrix.shape[0] - 1,
            self.interaction_matrix.shape[1] - 1,
        )
        if component_count <= 0:
            raise ValueError("Not enough users or movies to train TruncatedSVD.")
        if component_count != self.n_components:
            logger.warning(
                "Reducing n_components from %d to %d for matrix shape %s.",
                self.n_components,
                component_count,
                self.interaction_matrix.shape,
            )

        logger.info(
            "Training TruncatedSVD with %d ratings, %d users, %d movies, %d factors.",
            self.interaction_matrix.nnz,
            self.interaction_matrix.shape[0],
            self.interaction_matrix.shape[1],
            component_count,
        )
        try:
            self.model = TruncatedSVD(
                n_components=component_count,
                random_state=self.random_state,
            )
            self.user_factors = self.model.fit_transform(self.interaction_matrix)
        except Exception as exc:
            logger.exception("Failed to train TruncatedSVD collaborative model.")
            raise RuntimeError("Failed to train collaborative SVD model.") from exc

        logger.info("Collaborative recommender model is ready.")

    def _predict_user_ratings(self, user_row: int) -> np.ndarray:
        """Reconstruct predicted ratings for every movie for one user row."""

        centered_predictions = self.user_factors[user_row] @ self.model.components_
        predictions = centered_predictions + self.user_mean_ratings[user_row]
        return np.clip(predictions, self.rating_bounds[0], self.rating_bounds[1])

    def _build_interaction_matrix(self, ratings: pd.DataFrame) -> csr_matrix:
        """Create a sparse user-movie matrix with user-mean-centered ratings."""

        row_indices = ratings["userId"].map(self.user_to_row).to_numpy(dtype=np.int64)
        column_indices = ratings["movieId"].map(self.movie_to_column).to_numpy(
            dtype=np.int64
        )
        centered_ratings = (
            ratings["rating"].to_numpy(dtype=np.float32)
            - self.user_mean_ratings[row_indices].astype(np.float32)
        )

        matrix = coo_matrix(
            (centered_ratings, (row_indices, column_indices)),
            shape=(len(self.user_to_row), len(self.movie_to_column)),
            dtype=np.float32,
        ).tocsr()
        matrix.sum_duplicates()
        return matrix

    def _load_movies(self) -> pd.DataFrame:
        """Load MovieLens movie metadata and validate required columns."""

        logger.info("Loading MovieLens movies CSV: %s", self.movies_path)
        try:
            movies = pd.read_csv(self.movies_path, usecols=["movieId", "title"])
        except ValueError:
            movies = pd.read_csv(self.movies_path)
        except Exception as exc:
            logger.exception("Failed to load MovieLens movies CSV: %s", self.movies_path)
            raise RuntimeError(f"Failed to load movies CSV: {self.movies_path}") from exc

        self._validate_columns(movies, self.REQUIRED_MOVIE_COLUMNS, self.movies_path)
        movies = movies.dropna(subset=["movieId", "title"]).drop_duplicates("movieId")
        movies["movieId"] = movies["movieId"].astype(int)
        movies["title"] = movies["title"].astype(str)

        if movies.empty:
            raise ValueError("MovieLens movies dataset is empty.")

        return movies

    def _load_ratings(self) -> pd.DataFrame:
        """Load MovieLens ratings and validate required columns."""

        logger.info("Loading MovieLens ratings CSV: %s", self.ratings_path)
        try:
            ratings = pd.read_csv(
                self.ratings_path,
                usecols=["userId", "movieId", "rating"],
                nrows=self.max_ratings,
            )
        except ValueError:
            ratings = pd.read_csv(self.ratings_path, nrows=self.max_ratings)
        except Exception as exc:
            logger.exception("Failed to load MovieLens ratings CSV: %s", self.ratings_path)
            raise RuntimeError(f"Failed to load ratings CSV: {self.ratings_path}") from exc

        self._validate_columns(ratings, self.REQUIRED_RATING_COLUMNS, self.ratings_path)
        ratings = ratings.dropna(subset=["userId", "movieId", "rating"])
        ratings = ratings[ratings["movieId"].isin(self.movies["movieId"])]
        ratings["userId"] = ratings["userId"].astype(int)
        ratings["movieId"] = ratings["movieId"].astype(int)
        ratings["rating"] = ratings["rating"].astype(float)
        ratings = ratings.drop_duplicates(["userId", "movieId"], keep="last")

        if ratings.empty:
            raise ValueError("MovieLens ratings dataset is empty after validation.")

        return ratings

    @staticmethod
    def _build_index_maps(values: pd.Series) -> tuple[dict[int, int], dict[int, int]]:
        """Build forward and reverse integer index maps from unique IDs."""

        unique_values = sorted(values.dropna().astype(int).unique())
        value_to_index = {value: index for index, value in enumerate(unique_values)}
        index_to_value = {index: value for value, index in value_to_index.items()}
        return value_to_index, index_to_value

    @staticmethod
    def _compute_user_means(
        ratings: pd.DataFrame,
        user_to_row: dict[int, int],
    ) -> np.ndarray:
        """Compute each user's average rating for mean-centered factorization."""

        user_means = np.zeros(len(user_to_row), dtype=np.float32)
        grouped_means = ratings.groupby("userId")["rating"].mean()
        for user_id, mean_rating in grouped_means.items():
            user_means[user_to_row[int(user_id)]] = float(mean_rating)
        return user_means

    @staticmethod
    def _resolve_csv_path(
        path: Path,
        fallback_dir: Path,
        fallback_names: tuple[str, ...],
    ) -> Path:
        """Resolve direct CSV paths, nested CSV directories, and common variants."""

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
    def _validate_columns(
        data: pd.DataFrame,
        required_columns: set[str],
        path: Path,
    ) -> None:
        """Validate that a loaded CSV contains required columns."""

        missing_columns = required_columns.difference(data.columns)
        if missing_columns:
            missing = ", ".join(sorted(missing_columns))
            raise ValueError(f"CSV {path} is missing required columns: {missing}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    recommender = CollaborativeRecommender()
    print(recommender.recommend_for_user(1))
