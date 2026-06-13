"""Hybrid movie recommendations combining content and collaborative signals."""

from __future__ import annotations

import logging
import re
from typing import TypedDict

try:
    from backend.recommenders.content_based import ContentBasedRecommender
    from backend.recommenders.collaborative import CollaborativeRecommender
except ModuleNotFoundError as exc:
    if exc.name != "backend":
        raise
    from content_based import ContentBasedRecommender
    from collaborative import CollaborativeRecommender


logger = logging.getLogger(__name__)


class HybridRecommendation(TypedDict):
    """Public hybrid recommendation response shape."""

    title: str
    content_score: float
    collaborative_score: float
    final_score: float


class HybridRecommender:
    """Combine content-based and collaborative recommendations.

    The hybrid score uses a weighted blend of normalized source scores:
    ``0.6 * content_score + 0.4 * collaborative_score``.

    Parameters
    ----------
    content_recommender:
        Optional pre-built content recommender, useful for dependency injection
        in tests or services.
    collaborative_recommender:
        Optional pre-built collaborative recommender, useful for dependency
        injection in tests or services.
    content_weight:
        Weight assigned to normalized content-based scores.
    collaborative_weight:
        Weight assigned to normalized collaborative scores.
    """

    YEAR_SUFFIX_PATTERN = re.compile(r"\s*\(\d{4}\)\s*$")

    def __init__(
        self,
        content_recommender: ContentBasedRecommender | None = None,
        collaborative_recommender: CollaborativeRecommender | None = None,
        content_weight: float = 0.6,
        collaborative_weight: float = 0.4,
    ) -> None:
        if content_weight < 0 or collaborative_weight < 0:
            raise ValueError("Hybrid recommender weights must be non-negative.")
        if content_weight + collaborative_weight <= 0:
            raise ValueError("At least one hybrid recommender weight must be positive.")

        self.content_recommender = content_recommender or ContentBasedRecommender()
        self.collaborative_recommender = (
            collaborative_recommender or CollaborativeRecommender()
        )
        self.content_weight = content_weight
        self.collaborative_weight = collaborative_weight

        logger.info(
            "Hybrid recommender initialized with weights: content=%s, collaborative=%s.",
            self.content_weight,
            self.collaborative_weight,
        )

    def recommend(
        self,
        user_id: int,
        movie_title: str,
        top_n: int = 10,
    ) -> list[HybridRecommendation]:
        """Return hybrid recommendations for a user and seed movie.

        Parameters
        ----------
        user_id:
            MovieLens user identifier for collaborative recommendations.
        movie_title:
            Seed movie title for content-based recommendations.
        top_n:
            Maximum number of hybrid recommendations to return.

        Raises
        ------
        ValueError
            If inputs are invalid, or if either underlying recommender cannot
            generate recommendations for the requested user/title.
        RuntimeError
            If an unexpected failure occurs while combining recommendations.
        """

        if top_n <= 0:
            raise ValueError("top_n must be greater than zero.")
        if not movie_title.strip():
            raise ValueError("movie_title must be a non-empty string.")

        try:
            content_recommendations = self.content_recommender.recommend(
                movie_title=movie_title,
                top_n=top_n,
            )
            collaborative_recommendations = (
                self.collaborative_recommender.recommend_for_user(
                    user_id=user_id,
                    top_n=top_n,
                )
            )
        except ValueError:
            logger.exception(
                "Unable to generate hybrid recommendations for user=%s, movie=%r.",
                user_id,
                movie_title,
            )
            raise
        except Exception as exc:
            logger.exception("Unexpected hybrid recommendation failure.")
            raise RuntimeError("Failed to generate hybrid recommendations.") from exc

        content_scores = self._normalize_scores(
            {
                recommendation["title"]: float(recommendation["similarity_score"])
                for recommendation in content_recommendations
            }
        )
        collaborative_scores = self._normalize_scores(
            {
                recommendation["title"]: float(recommendation["predicted_rating"])
                for recommendation in collaborative_recommendations
            }
        )

        merged_recommendations = self._merge_scores(
            content_scores=content_scores,
            collaborative_scores=collaborative_scores,
        )
        ranked_recommendations = sorted(
            merged_recommendations.values(),
            key=lambda recommendation: recommendation["final_score"],
            reverse=True,
        )

        logger.info(
            "Generated %d hybrid recommendations for user=%s, movie=%r.",
            min(len(ranked_recommendations), top_n),
            user_id,
            movie_title,
        )
        return ranked_recommendations[:top_n]

    def _merge_scores(
        self,
        content_scores: dict[str, float],
        collaborative_scores: dict[str, float],
    ) -> dict[str, HybridRecommendation]:
        """Merge normalized source scores and compute final hybrid scores."""

        merged: dict[str, HybridRecommendation] = {}
        display_titles: dict[str, str] = {}

        for title in content_scores:
            display_titles.setdefault(self._normalize_title(title), title)
        for title in collaborative_scores:
            display_titles.setdefault(self._normalize_title(title), title)

        normalized_content_scores = {
            self._normalize_title(title): score for title, score in content_scores.items()
        }
        normalized_collaborative_scores = {
            self._normalize_title(title): score
            for title, score in collaborative_scores.items()
        }

        for title_key in sorted(
            set(normalized_content_scores) | set(normalized_collaborative_scores)
        ):
            content_score = normalized_content_scores.get(title_key, 0.0)
            collaborative_score = normalized_collaborative_scores.get(title_key, 0.0)
            final_score = (
                self.content_weight * content_score
                + self.collaborative_weight * collaborative_score
            )

            merged[title_key] = {
                "title": display_titles[title_key],
                "content_score": round(content_score, 4),
                "collaborative_score": round(collaborative_score, 4),
                "final_score": round(final_score, 4),
            }

        return merged

    @staticmethod
    def _normalize_scores(scores_by_title: dict[str, float]) -> dict[str, float]:
        """Normalize recommendation scores to the 0-1 range."""

        if not scores_by_title:
            return {}

        values = list(scores_by_title.values())
        min_score = min(values)
        max_score = max(values)

        if max_score == min_score:
            return {title: 1.0 for title in scores_by_title}

        return {
            title: (score - min_score) / (max_score - min_score)
            for title, score in scores_by_title.items()
        }

    @classmethod
    def _normalize_title(cls, title: str) -> str:
        """Normalize titles for duplicate merging across movie datasets."""

        without_year = cls.YEAR_SUFFIX_PATTERN.sub("", title)
        return " ".join(without_year.casefold().split())


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    recommender = HybridRecommender()
    print(
        recommender.recommend(
            user_id=1,
            movie_title="Inception",
        )
    )
