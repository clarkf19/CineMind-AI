from typing import List, Optional

import logging
import traceback

from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel

logger = logging.getLogger("backend.api.routes")

router = APIRouter()


class SearchItem(BaseModel):
    title: str
    similarity_score: float
    genres: List[str]
    vote_average: Optional[float]
    popularity: Optional[float]
    overview: Optional[str]
    # optional fields that may help the frontend map UI
    id: Optional[int] = None
    poster_path: Optional[str] = None
    release_date: Optional[str] = None
    # new fields
    reasons: Optional[List[str]] = None
    semantic_score: Optional[float] = None
    genre_score: Optional[float] = None
    keyword_score: Optional[float] = None
    content_score: Optional[float] = None
    rating_score: Optional[float] = None
    popularity_score: Optional[float] = None
    final_score: Optional[float] = None


class SearchResponse(BaseModel):
    results: List[SearchItem]


@router.get("/search", response_model=SearchResponse)
async def search_movies(request: Request, q: str):
    """Search endpoint that reuses the existing SemanticMovieSearch pipeline.

    Returns up to 20 results enriched with metadata fields.
    """
    logger.info("Received search request: q=%s", q)

    if not q or not str(q).strip():
        logger.warning("Bad request: empty query")
        raise HTTPException(status_code=400, detail="query parameter 'q' is required")

    engine = getattr(request.app.state, "search_engine", None)
    if engine is None:
        # Try lazy import/instantiate (should be set during startup)
        try:
            from backend.embeddings.semantic_search import SemanticMovieSearch

            logger.info("Lazily initializing SemanticMovieSearch for request")
            engine = SemanticMovieSearch()
            try:
                engine.store.load_index()
            except Exception:
                logger.debug("store.load_index() raised during lazy init, continuing")
            request.app.state.search_engine = engine
            logger.info("Lazy initialization complete")
        except Exception as exc:
            logger.error("Failed to initialize search engine on demand: %s", exc)
            logger.debug(traceback.format_exc())
            raise HTTPException(status_code=500, detail=f"Search engine unavailable: {exc}")

    # Reuse the existing search implementation
    try:
        raw_matches = engine.search(q, top_n=40)
    except Exception as exc:
        logger.error("Search execution failed for query=%s: %s", q, exc)
        logger.debug(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Search failed: {exc}")

    results = []
    try:
        for match in raw_matches:
            title = match.get("title")
            semantic_score = float(match.get("semantic_score", 0.0))

            # Lookup metadata row by title
            meta_row = None
            try:
                meta = engine.store.metadata
                rows = meta[meta["title"] == title]
                if not rows.empty:
                    meta_row = rows.iloc[0]
            except Exception:
                meta_row = None

            genres = []
            vote_average = None
            popularity = None
            overview = None
            _id = None
            poster_path = None
            release_date = None

            if meta_row is not None:
                # genres may be pipe-separated or a list-like string
                raw_genres = meta_row.get("genres")
                if isinstance(raw_genres, str):
                    genres = [g.strip() for g in raw_genres.split("|") if g.strip()]
                elif getattr(raw_genres, "__iter__", False):
                    try:
                        genres = list(raw_genres)
                    except Exception:
                        genres = []

                vote_average = meta_row.get("vote_average")
                popularity = meta_row.get("popularity")
                overview = meta_row.get("overview")
                _id = match.get("id")
                poster_path = match.get("poster_path")
                release_date = match.get("release_date")

            results.append(
                {
                    "title": title,
                    "similarity_score": semantic_score,
                    "genres": genres,
                    "vote_average": float(vote_average) if vote_average is not None else None,
                    "popularity": float(popularity) if popularity is not None else None,
                    "overview": str(overview) if overview is not None else None,
                    "id": int(_id) if _id is not None else None,
                    "poster_path": str(poster_path) if poster_path is not None else None,
                    "release_date": str(release_date) if release_date is not None else None,
                    "reasons": match.get("reasons"),
                    "semantic_score": match.get("semantic_score"),
                    "genre_score": match.get("genre_score"),
                    "keyword_score": match.get("keyword_score"),
                    "content_score": match.get("content_score"),
                    "rating_score": match.get("rating_score"),
                    "popularity_score": match.get("popularity_score"),
                    "final_score": match.get("final_score"),
                }
            )
    except Exception as exc:
        logger.error("Failed while building response for query=%s: %s", q, exc)
        logger.debug(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Failed to build response: {exc}")

    logger.info("Returning %d results for query=%s", len(results), q)
    return {"results": results}
