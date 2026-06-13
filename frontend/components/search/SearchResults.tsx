import { motion } from "framer-motion";
import { Movie } from "../../types/movie";
import { MovieCard } from "../movie/MovieCard";

interface SearchResultsProps {
  movies: Movie[];
}

export function SearchResults({ movies }: SearchResultsProps) {
  return (
    <div className="grid gap-6 sm:grid-cols-2 xl:grid-cols-3">
      {movies.map((movie, index) => (
        <motion.div
          key={movie.id}
          initial={{ opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, delay: index * 0.05 }}
        >
          <MovieCard movie={movie} />
        </motion.div>
      ))}
    </div>
  );
}
