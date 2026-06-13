export function Footer() {
  return (
    <footer className="border-t border-white/10 bg-black/60 py-8 text-sm text-slate-400 backdrop-blur-xl">
      <div className="mx-auto flex max-w-7xl flex-col gap-4 px-6 xl:px-0 sm:flex-row sm:items-center sm:justify-between">
        <span>© {new Date().getFullYear()} CineMind AI.</span>
        <span>AI-powered movie discovery with meaning-driven search.</span>
      </div>
    </footer>
  );
}
