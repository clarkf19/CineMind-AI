from pathlib import Path
import logging

import faiss
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class MovieVectorStore:

    def __init__(self):

        project_root = Path(__file__).resolve().parents[2]

        self.embeddings_path = (
            project_root
            / "data"
            / "embeddings"
            / "movie_embeddings.npy"
        )

        self.metadata_path = (
            project_root
            / "data"
            / "embeddings"
            / "movie_metadata.csv"
        )

        self.index_path = (
            project_root
            / "data"
            / "faiss"
            / "movie_index.faiss"
        )

        self.embeddings = None
        self.metadata = None
        self.index = None

    def build_index(self):

        logger.info("Loading embeddings...")

        self.embeddings = np.load(self.embeddings_path)
        self.metadata = pd.read_csv(self.metadata_path)

        faiss.normalize_L2(self.embeddings)

        dimension = self.embeddings.shape[1]

        self.index = faiss.IndexFlatIP(dimension)

        self.index.add(self.embeddings)

        self.index_path.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        faiss.write_index(
            self.index,
            str(self.index_path)
        )

        logger.info(
            f"Indexed {self.index.ntotal} movies."
        )

    def load_index(self):

        self.metadata = pd.read_csv(self.metadata_path)

        self.embeddings = np.load(
            self.embeddings_path
        )

        self.index = faiss.read_index(
            str(self.index_path)
        )

    def search_by_title(
        self,
        movie_title,
        top_n=10
    ):

        if self.index is None:
            self.load_index()

        matches = self.metadata[
            self.metadata["title"].str.lower()
            == movie_title.lower()
        ]

        if len(matches) == 0:
            raise ValueError(
                f"Movie not found: {movie_title}"
            )

        movie_idx = matches.index[0]

        query = self.embeddings[movie_idx].reshape(1, -1)

        faiss.normalize_L2(query)

        scores, indices = self.index.search(
            query,
            top_n + 1
        )

        results = []

        for score, idx in zip(
            scores[0],
            indices[0]
        ):

            if idx == movie_idx:
                continue

            results.append(
                {
                    "title":
                    self.metadata.iloc[idx]["title"],
                    "similarity_score":
                    round(float(score), 4),
                }
            )

        return results[:top_n]


if __name__ == "__main__":

    logging.basicConfig(level=logging.INFO)

    store = MovieVectorStore()

    store.build_index()

    print(
        store.search_by_title(
            "Inception",
            top_n=10
        )
    )