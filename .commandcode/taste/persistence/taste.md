# persistence
- Use Alembic for migrations rather than create_all-only startup behavior; make migrations descriptive and reversible. Confidence: 0.65
- Keep bounded structured JSON fields acceptable where appropriate; avoid premature normalization that obscures the domain model. Confidence: 0.55
- Make migration execution an explicit startup step with a toggle (e.g., run_migrations_on_startup=True) rather than a hard-wired side effect of app construction; tests must be able to disable it. Confidence: 0.75
- Configure SQLite with PRAGMA foreign_keys=ON, journal_mode=WAL, and synchronous=NORMAL. Confidence: 0.80
- Add restart-persistence verification as a first-class acceptance criterion: create artifacts, restart Core, verify lineage remains readable. Confidence: 0.70
- Use SQLite backup API or equivalent safe mechanism for database backups; avoid raw file-copy approaches that risk corruption with live databases. Confidence: 0.70
