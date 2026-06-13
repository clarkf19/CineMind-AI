# CineMind AI

CineMind AI is a premium, modern movie recommendation system that translates natural language concepts, moods, and emotions into highly relevant cinematic matches. By leveraging semantic vector embeddings and a hybrid rerank scoring system, CineMind matches search intents directly to movie overviews, themes, and genre structures.

---

## Short Description
Unlike standard search engines that rely strictly on keyword matching, **CineMind AI** utilizes SentenceTransformers to create a semantic representation of user queries, matching them against movie records via a FAISS vector index. The results are reranked using a hybrid scoring algorithm that balances semantic relevance, genre matching, thematic keyword density, content similarity, popularity, and audience reviews.

---

## Premium Features

1. **Semantic Movie Search**: Search using natural text prompts (e.g. *"movies about space exploration and human isolation"* or *"reality-bending psychological thrillers with a twist"*).
2. **Score Breakdown Visualizer**: Each recommendation card displays a detailed visual breakdown of the underlying metrics (Semantic, Genre, Rating, Popularity, and Content matching) contributing to the final score.
3. **Filter & Sort Control**: Instantly filter search results by active genres and sort by Relevance, Rating, Release Year, or Popularity.
4. **Favorites / Watchlist**: Save movies to a personal watchlist with client-side persistence (`localStorage`) and a live navigation badge count.
5. **Modern Dark UI**: A fluid user experience utilizing glassmorphism, responsive grid layouts, and micro-interactions powered by Tailwind CSS and Framer Motion.

---

## Tech Stack

*   **Frontend**: Next.js 14 (App Router, TypeScript), Tailwind CSS, Framer Motion
*   **Backend**: FastAPI (Python 3.10+), SentenceTransformers (`all-MiniLM-L6-v2`), FAISS, Pandas, scikit-learn
*   **Dataset**: TMDB 5000 Movies

---

## Setup & Running Locally

### 1. Prerequisites
Make sure you have **Node.js (v18+)** and **Python (v3.10+)** installed.

### 2. Run the Backend
From the root directory:
```bash
# Set up virtual environment
python -m venv venv
.\venv\Scripts\activate   # Windows
source venv/bin/activate  # macOS/Linux

# Install requirements
pip install -r backend/requirements.txt

# Run the FastAPI server
python -m backend.main
```
The backend server runs at `http://localhost:8000`.

### 3. Run the Frontend
From the `frontend/` directory:
```bash
cd frontend
npm install
npm run dev
```
The client application runs at `http://localhost:3000`.

---

## Project Structure
```
CineMind-AI/
├── backend/
│   ├── api/             # FastAPI routes & schemas
│   ├── embeddings/      # Semantic search engine & embedding loader
│   ├── faiss/           # Vector index utilities
│   ├── recommenders/    # TF-IDF content filtering
│   └── main.py          # FastAPI application entry point
├── frontend/
│   ├── app/             # Next.js App Router views (search, movie, watchlist)
│   ├── components/      # UI components (cards, navbar, visualizer)
│   ├── contexts/        # React Context hooks (Watchlist)
│   ├── hooks/           # API fetching hooks
│   └── styles/          # Tailwind & global styles
└── README.md            # Documentation
```
