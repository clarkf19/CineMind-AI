interface MoviePosterProps {
  posterUrl: string;
  title: string;
}

export function MoviePoster({ posterUrl, title }: MoviePosterProps) {
  return (
    <div className="overflow-hidden rounded-3xl bg-slate-950 shadow-xl shadow-black/40">
      <img src={posterUrl} alt={title} className="h-full w-full object-cover transition duration-300 hover:scale-105" />
    </div>
  );
}
