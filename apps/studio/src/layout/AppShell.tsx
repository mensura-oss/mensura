import type { PropsWithChildren } from "react";

export function AppShell({
  baseUrl,
  children,
}: PropsWithChildren<{ baseUrl: string }>) {
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <span className="brand__mark">M</span>
          <div>
            <strong>Mensura</strong>
            <span>Studio</span>
          </div>
        </div>
        <nav aria-label="Studio sections">
          <span className="nav-item nav-item--active">
            <span className="nav-item__icon" aria-hidden="true">⌁</span>
            Core overview
          </span>
        </nav>
        <div className="sidebar__note">
          <span>Cycle 3</span>
          <p>Stable shell and Core connectivity only.</p>
        </div>
      </aside>

      <div className="workspace">
        <header className="topbar">
          <div>
            <p className="eyebrow">Local development</p>
            <h1>Core overview</h1>
          </div>
          <div className="endpoint">
            <span>Core endpoint</span>
            <code>{baseUrl}</code>
          </div>
        </header>
        <main className="main-content">{children}</main>
      </div>
    </div>
  );
}
