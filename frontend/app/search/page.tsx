"use client";

import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { useSearch } from "../../hooks/useSearch";
import { SuggestionChip } from "../../components/search/SuggestionChip";
import { SearchBar } from "../../components/search/SearchBar";
import { SearchResults } from "../../components/search/SearchResults";
import { FilterSortPanel, SortKey } from "../../components/search/FilterSortPanel";
import { Container } from "../../components/layout/Container";
import { SUGGESTIONS } from "../../lib/constants";

export default function SearchPage() {
  const { query, results, onSearch } = useSearch();
  const params = useSearchParams();

  const [activeGenres, setActiveGenres] = useState<string[]>([]);
  const [sortBy, setSortBy] = useState<SortKey>("relevance");

  useEffect(() => {
    const q = params?.get("query") ?? "";
    if (q) {
      onSearch(q);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [params?.toString()]);

  // Reset filters/sort when results change (new search)
  useEffect(() => {
    setActiveGenres([]);
    setSortBy("relevance");
  }, [results]);

  // Deduplicate and sort genres across all search results
  const allGenres = Array.from(
    new Set(results.flatMap((movie) => movie.genres || []))
  ).sort();

  // Filter results
  const filteredResults = results.filter((movie) => {
    if (activeGenres.length === 0) return true;
    return movie.genres.some((genre) => activeGenres.includes(genre));
  });

  // Sort results
  const sortedResults = [...filteredResults].sort((a, b) => {
    if (sortBy === "rating") {
      return b.rating - a.rating;
    }
    if (sortBy === "year") {
      const yearA = parseInt(a.releaseYear) || 0;
      const yearB = parseInt(b.releaseYear) || 0;
      return yearB - yearA;
    }
    if (sortBy === "popularity") {
      return b.popularityScore - a.popularityScore;
    }
    // Default: relevance
    return b.recommendationScore - a.recommendationScore;
  });

  return (
    <Container>
      <section className="space-y-8 py-16">
        <div className="max-w-3xl space-y-4">
          <p className="text-sm uppercase tracking-[0.4em] text-slate-500">Search</p>
          <h1 className="text-4xl font-semibold text-white sm:text-5xl">Find movies that feel like your next idea.</h1>
          <p className="max-w-2xl text-slate-300">Type concepts, scenes, emotions, or a mood. CineMind turns natural language into cinematic recommendations.</p>
          <SearchBar query={query} onSearch={onSearch} />
        </div>

        <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
          {SUGGESTIONS.map((suggestion) => (
            <SuggestionChip key={suggestion} label={suggestion} onClick={() => onSearch(suggestion)} />
          ))}
        </div>
      </section>

      {results.length > 0 && (
        <div className="mb-8">
          <FilterSortPanel
            allGenres={allGenres}
            activeGenres={activeGenres}
            sortBy={sortBy}
            onGenreToggle={(genre) =>
              setActiveGenres((prev) =>
                prev.includes(genre) ? prev.filter((g) => g !== genre) : [...prev, genre]
              )
            }
            onSortChange={setSortBy}
            onClear={() => {
              setActiveGenres([]);
              setSortBy("relevance");
            }}
          />
        </div>
      )}

      <section className="space-y-6 pb-16">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm uppercase tracking-[0.3em] text-slate-500">Recommendations</p>
            <h2 className="text-3xl font-semibold text-white">Results for “{query || "everything"}”</h2>
          </div>
          <span className="rounded-3xl bg-white/5 px-4 py-2 text-sm text-slate-200">
            {sortedResults.length === results.length
              ? `${results.length} movies`
              : `${sortedResults.length} of ${results.length} movies`}
          </span>
        </div>

        <SearchResults movies={sortedResults} />
      </section>
    </Container>
  );
}
