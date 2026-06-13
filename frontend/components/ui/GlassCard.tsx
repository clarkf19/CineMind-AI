import { type PropsWithChildren } from "react";

export function GlassCard({ children }: PropsWithChildren) {
  return (
    <div className="rounded-3xl border border-white/10 bg-white/5 p-6 shadow-glow backdrop-blur-2xl">
      {children}
    </div>
  );
}
