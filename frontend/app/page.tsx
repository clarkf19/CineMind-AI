"use client";

import Link from "next/link";
import { GradientText } from "../components/ui/GradientText";
import { GlassCard } from "../components/ui/GlassCard";
import { SearchBar } from "../components/search/SearchBar";
import { SuggestionChip } from "../components/search/SuggestionChip";
import { Container } from "../components/layout/Container";
import { SUGGESTIONS } from "../lib/constants";

export default function HomePage() {
  return (
    <div className="relative overflow-hidden">
      <div className="pointer-events-none absolute inset-0 bg-radialGlow opacity-80" />
      <Container>
        <section className="relative z-10 py-20">
          <div className="max-w-3xl space-y-8">
            <p className="text-sm uppercase tracking-[0.4em] text-slate-500">CineMind AI</p>
            <h1 className="text-5xl font-semibold leading-tight text-white sm:text-6xl">
              Discover Movies Through <GradientText>Meaning</GradientText>
            </h1>
            <p className="max-w-2xl text-lg leading-8 text-slate-300">
              Search using ideas, emotions, themes and concepts. CineMind AI transforms natural language movie discovery into inspirational recommendations.
            </p>
            <GlassCard>
              <SearchBar query="" onSearch={() => undefined} />
            </GlassCard>
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              {SUGGESTIONS.map((suggestion) => (
                <Link key={suggestion} href={`/search?query=${encodeURIComponent(suggestion)}`} className="rounded-3xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-slate-200 transition hover:border-white/20 hover:bg-white/10">
                  {suggestion}
                </Link>
              ))}
            </div>
          </div>
        </section>

        <section className="grid gap-6 pt-16 lg:grid-cols-3">
          <GlassCard>
            <h2 className="text-xl font-semibold text-white">AI-powered discovery</h2>
            <p className="mt-3 text-slate-300">Search by mood, theme, concept, or a phrase like “movies like Interstellar but darker.”</p>
          </GlassCard>
          <GlassCard>
            <h2 className="text-xl font-semibold text-white">Hybrid reranking</h2>
            <p className="mt-3 text-slate-300">Semantic embeddings, genre-aware boosting, popularity, and audience confidence work together.</p>
          </GlassCard>
          <GlassCard>
            <h2 className="text-xl font-semibold text-white">Premium user experience</h2>
            <p className="mt-3 text-slate-300">A refined, minimal interface with motion and glassmorphism for modern discovery.</p>
          </GlassCard>
        </section>
      </Container>
    </div>
  );
}
