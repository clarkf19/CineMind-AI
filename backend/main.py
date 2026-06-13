import sys
from pathlib import Path

# Add project root to sys.path to allow running this script directly
project_root = Path(__file__).resolve().parents[1]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import logging
import os
import traceback

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api import routes

logger = logging.getLogger("backend.main")


def create_app() -> FastAPI:
    logger.info("Creating FastAPI app")
    app = FastAPI(title="CineMind API")

    # CORS: read allowed origins from env var for production flexibility.
    # Set ALLOWED_ORIGINS=https://your-app.vercel.app on Render.
    # Falls back to localhost for local development.
    raw_origins = os.environ.get("ALLOWED_ORIGINS", "http://localhost:3000")
    allowed_origins = [o.strip() for o in raw_origins.split(",") if o.strip()]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include API routes
    logger.info("Including API routes")
    app.include_router(routes.router)

    logger.info("FastAPI app created")
    return app


app = create_app()


@app.on_event("startup")
async def startup_event():
    logger.info("Application startup: initializing SemanticMovieSearch")
    try:
        from backend.embeddings.semantic_search import SemanticMovieSearch

        try:
            search_engine = SemanticMovieSearch()
            # the constructor already loads the index, but ensure index is loaded
            try:
                search_engine.store.load_index()
            except Exception:
                logger.debug("store.load_index() raised during startup, continuing")

            app.state.search_engine = search_engine
            logger.info("SemanticMovieSearch initialized and attached to app.state")
        except Exception as inner_exc:
            logger.error("Failed to instantiate SemanticMovieSearch: %s", inner_exc)
            logger.debug(traceback.format_exc())
    except Exception as exc:
        # Log and allow application to start; route will attempt lazy init
        logger.warning("Failed to import SemanticMovieSearch at startup: %s", exc)
        logger.debug(traceback.format_exc())


if __name__ == "__main__":
    import uvicorn

    logging.basicConfig(level=logging.INFO)
    logger.info("Starting uvicorn server from backend.main")
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
