"""Offline evaluation metrics for CineMind-AI recommenders.

The evaluator uses MovieLens ratings as ground truth, creates a train/test
split, evaluates content-based, collaborative, and hybrid recommenders, and
saves comparable metrics to ``ml/metrics/evaluation_results.json``.
"""

from __future__ import annotations

import json
import logging
import re
import sys
import tempfile
from itertools import combinations
from pathlib import Path
from typing import Callable, Iterable, Mapping, Sequence, TypedDict

import numpy as np
import pandas as pd

try:
    from backend.recommenders.collaborative import CollaborativeRecommender
    from backend.recommenders.content_based import ContentBasedRecommender
    from backend.recommenders.hybrid import HybridRecommender
except ModuleNotFoundError as exc:
    if exc.name != "backend":
        raise
    project_root = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(project_root))
    from backend.recommenders.collaborative import CollaborativeRecommender
    from backend.recommenders.content_based import ContentBasedRecommender
    from backend.recommenders.hybrid import HybridRecommender


logger = logging.getLogger(__name__)


EvaluationMetrics = TypedDict(
    "EvaluationMetrics",
    {
        "precision@10": float,
        "recall@10": float,
        "ndcg@10": float,
        "coverage": float,
        "diversity": float,
    },
)


class ComparisonResults(TypedDict):
    """Metric output for all recommender models."""

    content_based: EvaluationMetrics
    collaborative: EvaluationMetrics
    hybrid: EvaluationMetrics


YEAR_SUFFIX_PATTERN = re.compile(r"\s*\(\d{4}\)\s*$")


def precision_at_k(
    recommended_items: Sequence[str],
    relevant_items: set[str],
    k: int = 10,
) -> float:
    """Compute Precision@K for one recommendation list."""

    if k <= 0:
        raise ValueError("k must be greater than zero.")
    if not recommended_items:
        return 0.0

    top_k = recommended_items[:k]
    hits = sum(1 for item in top_k if item in relevant_items)
    return hits / k


def recall_at_k(
    recommended_items: Sequence[str],
    relevant_items: set[str],
    k: int = 10,
) -> float:
    """Compute Recall@K for one recommendation list."""

    if k <= 0:
        raise ValueError("k must be greater than zero.")
    if not relevant_items:
        return 0.0

    top_k = recommended_items[:k]
    hits = sum(1 for item in top_k if item in relevant_items)
    return hits / len(relevant_items)


def ndcg_at_k(
    recommended_items: Sequence[str],
    relevant_items: set[str],
    k: int = 10,
) -> float:
    """Compute binary-relevance NDCG@K for one recommendation list."""

    if k <= 0:
        raise ValueError("k must be greater than zero.")
    if not recommended_items or not relevant_items:
        return 0.0

    dcg = 0.0
    for rank, item in enumerate(recommended_items[:k], start=1):
        if item in relevant_items:
            dcg += 1.0 / np.log2(rank + 1)

    ideal_hits = min(len(relevant_items), k)
    ideal_dcg = sum(1.0 / np.log2(rank + 1) for rank in range(1, ideal_hits + 1))
    return dcg / ideal_dcg if ideal_dcg else 0.0


def coverage(
    recommendation_lists: Iterable[Sequence[str]],
    catalog_items: set[str],
) -> float:
    """Compute catalog coverage across recommendation lists."""

    if not catalog_items:
        return 0.0

    recommended_items: set[str] = set()
    for recommendations in recommendation_lists:
        recommended_items.update(recommendations)

    return len(recommended_items.intersection(catalog_items)) / len(catalog_items)


def diversity(
    recommendation_lists: Iterable[Sequence[str]],
    item_features: Mapping[str, set[str]] | None = None,
) -> float:
    """Compute average intra-list diversity.

    When ``item_features`` is provided, diversity is average pairwise Jaccard
    dissimilarity over feature sets. Without features, diversity falls back to
    title uniqueness within each recommendation list.
    """

    list_diversities: list[float] = []
    for recommendations in recommendation_lists:
        unique_items = list(dict.fromkeys(recommendations))
        if len(unique_items) < 2:
            continue

        pairwise_diversities: list[float] = []
        for left, right in combinations(unique_items, 2):
            if item_features is None:
                pairwise_diversities.append(1.0 if left != right else 0.0)
                continue

            left_features = item_features.get(left, set())
            right_features = item_features.get(right, set())
            union = left_features.union(right_features)
            similarity = (
                len(left_features.intersection(right_features)) / len(union)
                if union
                else 0.0
            )
            pairwise_diversities.append(1.0 - similarity)

        if pairwise_diversities:
            list_diversities.append(float(np.mean(pairwise_diversities)))

    return float(np.mean(list_diversities)) if list_diversities else 0.0


class RecommendationEvaluator:
    """Evaluate CineMind-AI recommenders against held-out MovieLens ratings.

    The evaluator uses each user's relevant held-out ratings as ground truth.
    Content-based and hybrid recommenders require a seed movie, so evaluation
    uses the user's highest-rated train movie that is available in the
    content-based catalog.

    Parameters
    ----------
    movies_path:
        Optional path to MovieLens movie metadata.
    ratings_path:
        Optional path to MovieLens ratings.
    output_path:
        JSON path where comparison results are saved.
    k:
        Ranking cutoff used for Precision@K, Recall@K, and NDCG@K.
    test_size:
        Per-user rating fraction assigned to the test split.
    relevance_threshold:
        Minimum rating considered relevant in the held-out set.
    random_state:
        Random seed for reproducible splitting and sampling.
    max_ratings:
        Optional cap for local/offline runs. Set to ``None`` for full ratings.
    max_eval_users:
        Optional cap on evaluated users. Set to ``None`` for all eligible users.
    collaborative_components:
        Latent factor count for collaborative model evaluation.
    """

    REQUIRED_MOVIE_COLUMNS = {"movieId", "title", "genres"}
    REQUIRED_RATING_COLUMNS = {"userId", "movieId", "rating"}

    def __init__(
        self,
        movies_path: str | Path | None = None,
        ratings_path: str | Path | None = None,
        output_path: str | Path | None = None,
        k: int = 10,
        test_size: float = 0.2,
        relevance_threshold: float = 4.0,
        random_state: int = 42,
        max_ratings: int | None = 100_000,
        max_eval_users: int | None = 100,
        collaborative_components: int = 50,
    ) -> None:
        if k <= 0:
            raise ValueError("k must be greater than zero.")
        if not 0 < test_size < 1:
            raise ValueError("test_size must be between 0 and 1.")
        if max_ratings is not None and max_ratings <= 0:
            raise ValueError("max_ratings must be greater than zero when provided.")
        if max_eval_users is not None and max_eval_users <= 0:
            raise ValueError("max_eval_users must be greater than zero when provided.")
        if collaborative_components <= 0:
            raise ValueError("collaborative_components must be greater than zero.")

        self.project_root = Path(__file__).resolve().parents[2]
        movielens_dir = self.project_root / "data" / "movielens"
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
        self.output_path = (
            Path(output_path)
            if output_path is not None
            else self.project_root / "ml" / "metrics" / "evaluation_results.json"
        )

        self.k = k
        self.test_size = test_size
        self.relevance_threshold = relevance_threshold
        self.random_state = random_state
        self.max_ratings = max_ratings
        self.max_eval_users = max_eval_users
        self.collaborative_components = collaborative_components

        self.movies = self._load_movies()
        self.ratings = self._load_ratings()
        self.train_ratings, self.test_ratings = self._split_ratings(self.ratings)
        self.train_with_titles = self._attach_titles(self.train_ratings)
        self.test_with_titles = self._attach_titles(self.test_ratings)
        self.catalog_items = {
            self._normalize_title(title) for title in self.movies["title"].astype(str)
        }
        self.item_features = self._build_item_features(self.movies)
        self.relevant_items_by_user = self._build_relevant_items(self.test_with_titles)
        self.eval_user_ids = self._select_eval_users()

        self._temp_dir = tempfile.TemporaryDirectory()
        self._train_ratings_path = Path(self._temp_dir.name) / "train_ratings.csv"
        self.train_ratings[["userId", "movieId", "rating"]].to_csv(
            self._train_ratings_path,
            index=False,
        )

        self._content_recommender: ContentBasedRecommender | None = None
        self._collaborative_recommender: CollaborativeRecommender | None = None
        self._hybrid_recommender: HybridRecommender | None = None

        logger.info(
            "Evaluator ready with %d train ratings, %d test ratings, %d eval users.",
            len(self.train_ratings),
            len(self.test_ratings),
            len(self.eval_user_ids),
        )

    def evaluate_content_based(
        self,
        recommender: ContentBasedRecommender | None = None,
    ) -> EvaluationMetrics:
        """Evaluate ``ContentBasedRecommender`` against held-out ratings."""

        content_recommender = recommender or self._get_content_recommender()

        def recommend(user_id: int) -> list[str]:
            seed_title = self._find_content_seed_title(user_id, content_recommender)
            if seed_title is None:
                return []
            recommendations = content_recommender.recommend(seed_title, top_n=self.k)
            return [
                self._normalize_title(recommendation["title"])
                for recommendation in recommendations
            ]

        return self._evaluate_recommender("content_based", recommend)

    def evaluate_collaborative(
        self,
        recommender: CollaborativeRecommender | None = None,
    ) -> EvaluationMetrics:
        """Evaluate ``CollaborativeRecommender`` against held-out ratings."""

        collaborative_recommender = recommender or self._get_collaborative_recommender()

        def recommend(user_id: int) -> list[str]:
            recommendations = collaborative_recommender.recommend_for_user(
                user_id,
                top_n=self.k,
            )
            return [
                self._normalize_title(recommendation["title"])
                for recommendation in recommendations
            ]

        return self._evaluate_recommender("collaborative", recommend)

    def evaluate_hybrid(
        self,
        recommender: HybridRecommender | None = None,
    ) -> EvaluationMetrics:
        """Evaluate ``HybridRecommender`` against held-out ratings."""

        hybrid_recommender = recommender or self._get_hybrid_recommender()
        content_recommender = hybrid_recommender.content_recommender

        def recommend(user_id: int) -> list[str]:
            seed_title = self._find_content_seed_title(user_id, content_recommender)
            if seed_title is None:
                return []
            recommendations = hybrid_recommender.recommend(
                user_id=user_id,
                movie_title=seed_title,
                top_n=self.k,
            )
            return [
                self._normalize_title(recommendation["title"])
                for recommendation in recommendations
            ]

        return self._evaluate_recommender("hybrid", recommend)

    def compare_models(self) -> ComparisonResults:
        """Evaluate all available recommenders and save the results as JSON."""

        results: ComparisonResults = {
            "content_based": self.evaluate_content_based(),
            "collaborative": self.evaluate_collaborative(),
            "hybrid": self.evaluate_hybrid(),
        }
        self._save_results(results)
        return results

    def _evaluate_recommender(
        self,
        model_name: str,
        recommend: Callable[[int], list[str]],
    ) -> EvaluationMetrics:
        """Run one recommender across evaluation users and aggregate metrics."""

        precision_scores: list[float] = []
        recall_scores: list[float] = []
        ndcg_scores: list[float] = []
        recommendation_lists: list[list[str]] = []
        skipped_users = 0

        for user_id in self.eval_user_ids:
            relevant_items = self.relevant_items_by_user.get(user_id, set())
            if not relevant_items:
                skipped_users += 1
                continue

            try:
                recommended_items = recommend(user_id)
            except ValueError:
                logger.debug(
                    "Skipping user %s for %s due to recommendation input mismatch.",
                    user_id,
                    model_name,
                    exc_info=True,
                )
                skipped_users += 1
                continue
            except Exception:
                logger.exception(
                    "Skipping user %s after %s recommendation failure.",
                    user_id,
                    model_name,
                )
                skipped_users += 1
                continue

            if not recommended_items:
                skipped_users += 1
                continue

            recommendation_lists.append(recommended_items)
            precision_scores.append(
                precision_at_k(recommended_items, relevant_items, k=self.k)
            )
            recall_scores.append(recall_at_k(recommended_items, relevant_items, k=self.k))
            ndcg_scores.append(ndcg_at_k(recommended_items, relevant_items, k=self.k))

        if not recommendation_lists:
            logger.warning("No users could be evaluated for %s.", model_name)
            return self._empty_metrics()

        metrics: EvaluationMetrics = {
            "precision@10": round(float(np.mean(precision_scores)), 4),
            "recall@10": round(float(np.mean(recall_scores)), 4),
            "ndcg@10": round(float(np.mean(ndcg_scores)), 4),
            "coverage": round(coverage(recommendation_lists, self.catalog_items), 4),
            "diversity": round(diversity(recommendation_lists, self.item_features), 4),
        }
        logger.info(
            "Evaluated %s on %d users; skipped %d users. Metrics: %s",
            model_name,
            len(recommendation_lists),
            skipped_users,
            metrics,
        )
        return metrics

    def _get_content_recommender(self) -> ContentBasedRecommender:
        """Return a cached content-based recommender."""

        if self._content_recommender is None:
            self._content_recommender = ContentBasedRecommender()
        return self._content_recommender

    def _get_collaborative_recommender(self) -> CollaborativeRecommender:
        """Return a cached collaborative recommender trained on the train split."""

        if self._collaborative_recommender is None:
            self._collaborative_recommender = CollaborativeRecommender(
                movies_path=self.movies_path,
                ratings_path=self._train_ratings_path,
                n_components=self.collaborative_components,
                random_state=self.random_state,
            )
        return self._collaborative_recommender

    def _get_hybrid_recommender(self) -> HybridRecommender:
        """Return a cached hybrid recommender using train-split components."""

        if self._hybrid_recommender is None:
            self._hybrid_recommender = HybridRecommender(
                content_recommender=self._get_content_recommender(),
                collaborative_recommender=self._get_collaborative_recommender(),
            )
        return self._hybrid_recommender

    def _find_content_seed_title(
        self,
        user_id: int,
        recommender: ContentBasedRecommender,
    ) -> str | None:
        """Find the user's highest-rated train movie available in TMDB."""

        user_train = self.train_with_titles[self.train_with_titles["userId"] == user_id]
        if user_train.empty:
            return None

        sorted_train = user_train.sort_values(
            ["rating", "title"],
            ascending=[False, True],
        )
        content_titles = set(recommender.title_to_index)
        for title in sorted_train["title"].astype(str):
            seed_title = self._strip_year(title)
            if seed_title.casefold() in content_titles:
                return seed_title

        return None

    def _load_movies(self) -> pd.DataFrame:
        """Load MovieLens movies."""

        logger.info("Loading MovieLens movies from %s.", self.movies_path)
        try:
            movies = pd.read_csv(
                self.movies_path,
                usecols=["movieId", "title", "genres"],
            )
        except ValueError:
            movies = pd.read_csv(self.movies_path)
        except Exception as exc:
            logger.exception("Failed to load MovieLens movies.")
            raise RuntimeError(f"Failed to load movies CSV: {self.movies_path}") from exc

        self._validate_columns(movies, self.REQUIRED_MOVIE_COLUMNS, self.movies_path)
        movies = movies.dropna(subset=["movieId", "title"]).drop_duplicates("movieId")
        movies["movieId"] = movies["movieId"].astype(int)
        movies["title"] = movies["title"].astype(str)
        movies["genres"] = movies["genres"].fillna("").astype(str)

        if movies.empty:
            raise ValueError("MovieLens movies dataset is empty.")
        return movies

    def _load_ratings(self) -> pd.DataFrame:
        """Load MovieLens ratings."""

        logger.info("Loading MovieLens ratings from %s.", self.ratings_path)
        try:
            ratings = pd.read_csv(
                self.ratings_path,
                usecols=["userId", "movieId", "rating"],
                nrows=self.max_ratings,
            )
        except ValueError:
            ratings = pd.read_csv(self.ratings_path, nrows=self.max_ratings)
        except Exception as exc:
            logger.exception("Failed to load MovieLens ratings.")
            raise RuntimeError(f"Failed to load ratings CSV: {self.ratings_path}") from exc

        self._validate_columns(ratings, self.REQUIRED_RATING_COLUMNS, self.ratings_path)
        ratings = ratings.dropna(subset=["userId", "movieId", "rating"])
        ratings["userId"] = ratings["userId"].astype(int)
        ratings["movieId"] = ratings["movieId"].astype(int)
        ratings["rating"] = ratings["rating"].astype(float)
        ratings = ratings[ratings["movieId"].isin(self.movies["movieId"])]
        ratings = ratings.drop_duplicates(["userId", "movieId"], keep="last")

        if ratings.empty:
            raise ValueError("MovieLens ratings dataset is empty after validation.")
        return ratings

    def _split_ratings(self, ratings: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
        """Create a per-user train/test split with at least one train rating."""

        rng = np.random.default_rng(self.random_state)
        test_indices: list[int] = []

        for _, user_ratings in ratings.groupby("userId", sort=False):
            if len(user_ratings) < 2:
                continue
            test_count = max(1, int(round(len(user_ratings) * self.test_size)))
            test_count = min(test_count, len(user_ratings) - 1)
            sampled_indices = rng.choice(
                user_ratings.index.to_numpy(),
                size=test_count,
                replace=False,
            )
            test_indices.extend(int(index) for index in sampled_indices)

        if not test_indices:
            raise ValueError("Unable to create a train/test split from ratings.")

        test_ratings = ratings.loc[test_indices].copy()
        train_ratings = ratings.drop(index=test_indices).copy()
        return train_ratings.reset_index(drop=True), test_ratings.reset_index(drop=True)

    def _attach_titles(self, ratings: pd.DataFrame) -> pd.DataFrame:
        """Attach MovieLens titles and genres to a ratings frame."""

        return ratings.merge(self.movies, on="movieId", how="left")

    def _build_relevant_items(
        self,
        test_with_titles: pd.DataFrame,
    ) -> dict[int, set[str]]:
        """Build user-level relevant item sets from held-out ratings."""

        relevant = test_with_titles[
            test_with_titles["rating"] >= self.relevance_threshold
        ].copy()
        relevant["title_key"] = relevant["title"].astype(str).apply(self._normalize_title)
        return {
            int(user_id): set(titles)
            for user_id, titles in relevant.groupby("userId")["title_key"]
        }

    def _select_eval_users(self) -> list[int]:
        """Select users that have train history and relevant held-out items."""

        train_users = set(self.train_ratings["userId"].astype(int))
        eligible_users = sorted(
            user_id
            for user_id in self.relevant_items_by_user
            if user_id in train_users
        )
        if self.max_eval_users is None or len(eligible_users) <= self.max_eval_users:
            return eligible_users

        rng = np.random.default_rng(self.random_state)
        sampled_users = rng.choice(
            np.array(eligible_users, dtype=np.int64),
            size=self.max_eval_users,
            replace=False,
        )
        return sorted(int(user_id) for user_id in sampled_users)

    @classmethod
    def _build_item_features(cls, movies: pd.DataFrame) -> dict[str, set[str]]:
        """Build normalized title to genre-set mapping for diversity."""

        item_features: dict[str, set[str]] = {}
        for _, row in movies.iterrows():
            title_key = cls._normalize_title(str(row["title"]))
            genres = {
                genre.strip()
                for genre in str(row.get("genres", "")).split("|")
                if genre.strip() and genre.strip() != "(no genres listed)"
            }
            item_features[title_key] = genres
        return item_features

    def _save_results(self, results: ComparisonResults) -> None:
        """Save comparison results to the configured JSON path."""

        try:
            self.output_path.parent.mkdir(parents=True, exist_ok=True)
            self.output_path.write_text(
                json.dumps(results, indent=2),
                encoding="utf-8",
            )
        except Exception as exc:
            logger.exception("Failed to save evaluation results.")
            raise RuntimeError(
                f"Failed to save evaluation results: {self.output_path}"
            ) from exc
        logger.info("Saved evaluation results to %s.", self.output_path)

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

    @staticmethod
    def _empty_metrics() -> EvaluationMetrics:
        """Return a zeroed metric payload."""

        return {
            "precision@10": 0.0,
            "recall@10": 0.0,
            "ndcg@10": 0.0,
            "coverage": 0.0,
            "diversity": 0.0,
        }

    @classmethod
    def _normalize_title(cls, title: str) -> str:
        """Normalize titles for cross-dataset matching."""

        return " ".join(cls._strip_year(title).casefold().split())

    @staticmethod
    def _strip_year(title: str) -> str:
        """Remove MovieLens year suffixes from titles."""

        return YEAR_SUFFIX_PATTERN.sub("", title).strip()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    evaluator = RecommendationEvaluator()
    results = evaluator.compare_models()
    print(results)
