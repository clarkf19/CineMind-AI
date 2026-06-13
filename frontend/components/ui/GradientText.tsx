import { type PropsWithChildren } from "react";

export function GradientText({ children }: PropsWithChildren) {
  return (
    <span className="bg-gradient-to-r from-accent to-accent2 bg-clip-text text-transparent">{children}</span>
  );
}
