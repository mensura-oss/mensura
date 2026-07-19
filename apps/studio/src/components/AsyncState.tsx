import type { PropsWithChildren } from "react";

export function LoadingState({ children }: PropsWithChildren) {
  return (
    <div className="state state--loading" role="status">
      <span className="spinner" aria-hidden="true" />
      <span>{children}</span>
    </div>
  );
}

export function EmptyState({ children }: PropsWithChildren) {
  return <div className="state state--empty">{children}</div>;
}
