"use client";

import { useState } from "react";

interface SearchBarProps {
  query: string;
  onSearch: (query: string) => void;
}

export function SearchBar({ query, onSearch }: SearchBarProps) {
  const [value, setValue] = useState(query);

  return (
    <form
      onSubmit={(event) => {
        event.preventDefault();
        onSearch(value.trim());
      }}
      className="space-y-4"
    >
      <label htmlFor="query" className="text-sm uppercase tracking-[0.24em] text-slate-400">
        Search ideas, themes, emotions
      </label>
      <div className="relative flex items-center gap-3 rounded-3xl border border-white/10 bg-white/5 px-4 py-4 shadow-glow backdrop-blur-xl transition focus-within:border-white/20">
        <input
          id="query"
          value={value}
          onChange={(event) => setValue(event.target.value)}
          placeholder="mind bending science fiction movies"
          className="w-full bg-transparent text-lg font-medium text-white outline-none placeholder:text-slate-500"
        />
        <button
          type="submit"
          className="rounded-2xl bg-accent px-5 py-3 text-sm font-semibold text-white transition hover:bg-accent2"
        >
          Discover
        </button>
      </div>
    </form>
  );
}
