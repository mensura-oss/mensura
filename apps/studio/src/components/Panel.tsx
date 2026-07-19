import type { PropsWithChildren, ReactNode } from "react";

export function Panel({
  children,
  eyebrow,
  title,
  toolbar,
}: PropsWithChildren<{
  eyebrow: string;
  title: string;
  toolbar?: ReactNode;
}>) {
  return (
    <section className="panel">
      <header className="panel__header">
        <div>
          <p className="eyebrow">{eyebrow}</p>
          <h2>{title}</h2>
        </div>
        {toolbar}
      </header>
      <div className="panel__body">{children}</div>
    </section>
  );
}
