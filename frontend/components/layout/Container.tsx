import { type PropsWithChildren } from "react";

export function Container({ children }: PropsWithChildren) {
  return <div className="mx-auto max-w-7xl px-6 xl:px-0">{children}</div>;
}
