# architecture
- Use RFC 9457 Problem Details (application/problem+json) for all HTTP API errors. Confidence: 0.85
- Use SQLite as the first durable backend with SQLAlchemy 2 patterns, explicit sessions, and repository interfaces; keep architecture open to future Postgres but avoid Postgres-first complexity. Confidence: 0.70
- Keep provider prompts code-bounded, versioned, and immutable; never generate prompts dynamically from user input. Confidence: 0.70
- Keep immutable artifact semantics intact; preserve artifact identities, references, and retrieval semantics across restarts. Confidence: 0.65
- Use explicit transaction boundaries for all database operations. Confidence: 0.65
- Keep blocking database access honest; do not disguise blocking I/O as async. Confidence: 0.60
