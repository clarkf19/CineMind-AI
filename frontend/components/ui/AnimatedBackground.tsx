export function AnimatedBackground() {
  return (
    <div className="pointer-events-none absolute inset-0 overflow-hidden">
      <div className="absolute left-[-15%] top-10 h-96 w-96 rounded-full bg-accent/20 blur-3xl" />
      <div className="absolute right-[-10%] top-1/3 h-72 w-72 rounded-full bg-accent2/15 blur-3xl" />
    </div>
  );
}
