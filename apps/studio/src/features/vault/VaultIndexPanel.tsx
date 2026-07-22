import type {
  VaultArchitectureSummary,
  VaultEmbeddingInfo,
  VaultIndexSnapshot,
  VaultMemoryItemDetail,
  VaultSearchHit,
  VaultSearchOptions,
  VaultSearchResponse,
  VaultSourceType,
} from "@mensura/shared-types";
import {
  useMutation,
  useQuery,
  useQueryClient,
  type UseMutationResult,
  type UseQueryResult,
} from "@tanstack/react-query";
import { useState, type FormEvent } from "react";

import { useCoreClient } from "../../api/CoreClientProvider";
import { CoreApiError } from "../../api/coreClient";
import { queryKeys } from "../../app/queryClient";
import { EmptyState, LoadingState } from "../../components/AsyncState";
import { Panel } from "../../components/Panel";
import { ProblemDetailsView } from "../../components/ProblemDetailsView";
import type { OpenInWorkspaceHandler } from "../workspace/types";
import { VaultFileView } from "./VaultFileView";

const INDEX_NOT_BUILT_TYPE = "urn:mensura:problem:vault-index-not-built";
const MEMORY_NOT_FOUND_TYPE = "urn:mensura:problem:vault-memory-not-found";
const SEARCH_LIMIT = 20;

// Retrieval-mode strings Core reports honestly on `VaultSearchResponse.strategy` (see
// shared-types `vault-index.ts`). We only read them here — never invent new ones.
const SEMANTIC_STRATEGY_PREFIX = "semantic-cosine:";
const LEXICAL_FALLBACK_STRATEGY = "lexical-fallback:reindex-required";

type SelectedHit = {
  memoryItemId: string;
  chunkId: string;
  path: string;
  sourceType: VaultSourceType;
  language: string | null;
  startLine: number;
  endLine: number;
};

export function VaultIndexPanel({
  activeWorkspaceId,
  onOpenInWorkspace,
}: {
  activeWorkspaceId: string | null;
  /** When provided, a search hit's file view can open in the Workspace editor. */
  onOpenInWorkspace?: OpenInWorkspaceHandler;
}) {
  const client = useCoreClient();
  const queryClient = useQueryClient();
  const [queryText, setQueryText] = useState("");
  const [sourceType, setSourceType] = useState<VaultSourceType | "">("");
  const [submittedQuery, setSubmittedQuery] = useState<string | null>(null);
  const [selectedHit, setSelectedHit] = useState<SelectedHit | null>(null);

  const index = useQuery({
    queryKey: queryKeys.vaultIndex(activeWorkspaceId ?? "none"),
    queryFn: () => {
      if (!activeWorkspaceId) {
        throw new Error("Select a workspace before loading its Vault index.");
      }
      return client.getVaultIndex(activeWorkspaceId);
    },
    enabled: activeWorkspaceId !== null,
    retry: false,
  });

  const search = useMutation({
    mutationFn: (options: VaultSearchOptions) => {
      if (!activeWorkspaceId) {
        throw new Error("Select a workspace before searching Vault.");
      }
      return client.searchVault(activeWorkspaceId, options);
    },
  });

  const summarize = useMutation({
    mutationFn: () => {
      if (!activeWorkspaceId) {
        throw new Error("Select a workspace before summarizing Vault.");
      }
      return client.summarizeVaultWorkspace(activeWorkspaceId);
    },
  });

  const buildIndex = useMutation({
    mutationFn: () => {
      if (!activeWorkspaceId) {
        throw new Error("Select a workspace before indexing it into Vault.");
      }
      return client.indexVaultWorkspace(activeWorkspaceId);
    },
    onSuccess: (snapshot) => {
      queryClient.setQueryData(queryKeys.vaultIndex(snapshot.workspaceId), snapshot);
      // A re-index replaces the whole index — drop stale search, summary, and detail.
      setSubmittedQuery(null);
      setSelectedHit(null);
      search.reset();
      summarize.reset();
    },
  });

  const memory = useQuery({
    queryKey: queryKeys.vaultMemoryItem(selectedHit?.memoryItemId ?? "none"),
    queryFn: () => {
      if (!selectedHit) {
        throw new Error("Select a search result before loading its chunk detail.");
      }
      return client.getVaultMemoryItem(selectedHit.memoryItemId);
    },
    enabled: selectedHit !== null,
    retry: false,
  });

  const notIndexed = index.isError && isIndexNotBuilt(index.error);

  function handleSearch(event: FormEvent) {
    event.preventDefault();
    const trimmed = queryText.trim();
    if (!trimmed) return;
    setSubmittedQuery(trimmed);
    setSelectedHit(null);
    const options: VaultSearchOptions = { query: trimmed, limit: SEARCH_LIMIT };
    if (sourceType) options.sourceType = sourceType;
    search.mutate(options);
  }

  return (
    <Panel
      eyebrow="Semantic index (MVP)"
      title="Vault memory"
      toolbar={
        activeWorkspaceId && !index.isPending ? (
          <button
            className="button button--primary"
            type="button"
            onClick={() => buildIndex.mutate()}
            disabled={buildIndex.isPending}
          >
            {buildIndex.isPending
              ? "Indexing…"
              : index.isSuccess
                ? "Re-index"
                : "Index workspace"}
          </button>
        ) : undefined
      }
    >
      <AboutVault />

      {!activeWorkspaceId ? (
        <EmptyState>Select an active workspace to index and search its Vault memory.</EmptyState>
      ) : null}
      {activeWorkspaceId && index.isPending ? (
        <LoadingState>Checking Vault index status…</LoadingState>
      ) : null}
      {notIndexed ? (
        <EmptyState>
          This workspace is not indexed yet. Index it to enable search and the architecture
          summary.
        </EmptyState>
      ) : null}
      {index.isError && !notIndexed ? <ProblemDetailsView error={index.error} /> : null}
      {buildIndex.isPending ? (
        <div className="vault-building" role="status">
          <span className="spinner" aria-hidden="true" />
          <span>Core is reading and chunking workspace files (full re-index)…</span>
        </div>
      ) : null}
      {buildIndex.isError ? <ProblemDetailsView error={buildIndex.error} /> : null}

      {index.isSuccess ? (
        <VaultIndexReady
          snapshot={index.data}
          summarize={summarize}
          search={search}
          submittedQuery={submittedQuery}
          queryText={queryText}
          onQueryTextChange={setQueryText}
          sourceType={sourceType}
          onSourceTypeChange={setSourceType}
          onSubmit={handleSearch}
          selectedHit={selectedHit}
          onSelectHit={(hit) =>
            setSelectedHit({
              memoryItemId: hit.memoryItemId,
              chunkId: hit.chunkId,
              path: hit.path,
              sourceType: hit.sourceType,
              language: hit.language,
              startLine: hit.startLine,
              endLine: hit.endLine,
            })
          }
          onClearHit={() => setSelectedHit(null)}
          memory={memory}
          onOpenInWorkspace={onOpenInWorkspace}
        />
      ) : null}
    </Panel>
  );
}

function isIndexNotBuilt(error: unknown) {
  return error instanceof CoreApiError && error.problem.type === INDEX_NOT_BUILT_TYPE;
}

function AboutVault() {
  return (
    <details className="vault-about">
      <summary>About Vault memory</summary>
      <ul>
        <li>
          Indexing is <strong>manual and full-replace</strong> — re-indexing rebuilds the entire
          index. There is no incremental or file-watch indexing yet.
        </li>
        <li>
          Search ranks by vector similarity. With a local embedding backend it is{" "}
          <strong>semantic</strong>; otherwise it falls back to a <strong>local lexical model</strong>{" "}
          (hashed term frequencies) — the badge above shows the active mode. Either way, exact
          substring matches get a small boost.
        </li>
        <li>
          After the embedding backend changes, <strong>re-index</strong> the workspace to refresh its
          vectors. Until then, search reports a lexical fallback — results still work, but relevance
          may be lower.
        </li>
        <li>Very large or binary files are skipped by design and won&apos;t appear in results.</li>
      </ul>
    </details>
  );
}

function VaultIndexReady({
  snapshot,
  summarize,
  search,
  submittedQuery,
  queryText,
  onQueryTextChange,
  sourceType,
  onSourceTypeChange,
  onSubmit,
  selectedHit,
  onSelectHit,
  onClearHit,
  memory,
  onOpenInWorkspace,
}: {
  snapshot: VaultIndexSnapshot;
  summarize: UseMutationResult<VaultArchitectureSummary, Error, void, unknown>;
  search: UseMutationResult<VaultSearchResponse, Error, VaultSearchOptions, unknown>;
  submittedQuery: string | null;
  queryText: string;
  onQueryTextChange: (value: string) => void;
  sourceType: VaultSourceType | "";
  onSourceTypeChange: (value: VaultSourceType | "") => void;
  onSubmit: (event: FormEvent) => void;
  selectedHit: SelectedHit | null;
  onSelectHit: (hit: VaultSearchHit) => void;
  onClearHit: () => void;
  memory: UseQueryResult<VaultMemoryItemDetail, Error>;
  onOpenInWorkspace: OpenInWorkspaceHandler | undefined;
}) {
  return (
    <div className="vault-index">
      <IndexStatus snapshot={snapshot} />

      <section className="vault-index-section" aria-label="Architecture summary">
        <div className="vault-section-heading">
          <strong>Architecture summary</strong>
          <button
            className="button button--secondary"
            type="button"
            onClick={() => summarize.mutate()}
            disabled={summarize.isPending}
          >
            {summarize.isPending
              ? "Generating…"
              : summarize.isSuccess
                ? "Regenerate summary"
                : "Generate summary"}
          </button>
        </div>
        {!summarize.isSuccess && !summarize.isPending && !summarize.isError ? (
          <EmptyState>
            Generate a heuristic architecture summary (modules, languages, technologies) from the
            index.
          </EmptyState>
        ) : null}
        {summarize.isPending ? <LoadingState>Deriving the architecture summary…</LoadingState> : null}
        {summarize.isError ? <ProblemDetailsView error={summarize.error} /> : null}
        {summarize.isSuccess ? <ArchitectureSummaryView summary={summarize.data} /> : null}
      </section>

      <section className="vault-index-section" aria-label="Vault search">
        <div className="vault-section-heading">
          <strong>Search</strong>
        </div>
        <form className="vault-index-search-form" onSubmit={onSubmit}>
          <input
            type="search"
            aria-label="Vault search query"
            placeholder="Search indexed code, docs, and config…"
            value={queryText}
            onChange={(event) => onQueryTextChange(event.target.value)}
          />
          <select
            aria-label="Source type filter"
            value={sourceType}
            onChange={(event) => onSourceTypeChange(event.target.value as VaultSourceType | "")}
          >
            <option value="">All types</option>
            <option value="code">Code</option>
            <option value="doc">Docs</option>
            <option value="config">Config</option>
          </select>
          <button
            className="button button--primary"
            type="submit"
            disabled={search.isPending || queryText.trim().length === 0}
          >
            {search.isPending ? "Searching…" : "Search"}
          </button>
        </form>

        <div className="vault-index-layout">
          <div className="vault-index-results" aria-label="Search results">
            {search.isIdle ? (
              <EmptyState>Enter a query to retrieve ranked chunks from the index.</EmptyState>
            ) : null}
            {search.isPending ? <LoadingState>Ranking chunks by relevance…</LoadingState> : null}
            {search.isError ? <ProblemDetailsView error={search.error} /> : null}
            {search.isSuccess && search.data.hits.length === 0 ? (
              <EmptyState>
                No matching chunks found{submittedQuery ? ` for “${submittedQuery}”` : ""}. Try
                different or broader terms.
              </EmptyState>
            ) : null}
            {search.isSuccess && search.data.hits.length > 0 ? (
              <SearchResults
                response={search.data}
                selectedChunkId={selectedHit?.chunkId ?? null}
                onSelectHit={onSelectHit}
              />
            ) : null}
          </div>
          <div className="vault-index-detail" aria-label="File view">
            <div className="vault-section-heading">
              <strong>File view</strong>
            </div>
            {!selectedHit ? (
              <EmptyState>Select a result to open its file here.</EmptyState>
            ) : null}
            {selectedHit && memory.isPending ? (
              <LoadingState>Opening file…</LoadingState>
            ) : null}
            {selectedHit && memory.isError ? (
              isMemoryStale(memory.error) ? (
                <div className="vault-file-view">
                  <div className="vault-file-view__bar">
                    <button
                      type="button"
                      className="button button--quiet"
                      onClick={onClearHit}
                    >
                      ← Back to results
                    </button>
                  </div>
                  <EmptyState>
                    This result is stale — its file is no longer in the current index. Re-run the
                    search to refresh results.
                  </EmptyState>
                </div>
              ) : (
                <ProblemDetailsView error={memory.error} />
              )
            ) : null}
            {selectedHit && memory.isSuccess ? (
              <VaultFileView
                detail={memory.data}
                hit={selectedHit}
                onBack={onClearHit}
                onOpenInWorkspace={onOpenInWorkspace}
              />
            ) : null}
          </div>
        </div>
      </section>
    </div>
  );
}

type RetrievalTone = "semantic" | "lexical" | "fallback";

type RetrievalMode = {
  tone: RetrievalTone;
  /** Short badge text. */
  label: string;
  /** Backend/model qualifier shown beside the badge, when known. */
  detail: string | null;
  /** Hover disclosure explaining the mode and any action it implies. */
  title: string;
};

const RETRIEVAL_BADGE_CLASS: Record<RetrievalTone, string> = {
  semantic: "badge badge--clean",
  lexical: "badge",
  fallback: "badge badge--dirty",
};

/**
 * How the *stored* index was built, from the embedding metadata Core records on the snapshot
 * summary. Absent metadata means a pre-embedding-backend (legacy lexical) index. This is the
 * durable, always-visible mode; the live per-query mode comes from {@link describeSearchStrategy}.
 */
function describeIndexMode(embedding: VaultEmbeddingInfo | undefined): RetrievalMode {
  if (!embedding) {
    return {
      tone: "lexical",
      label: "Lexical search active",
      detail: "legacy index — re-index for semantic",
      title:
        "This index has no embedding metadata — it was built by the local lexical model. Re-index with an embedding backend configured to enable semantic search.",
    };
  }
  if (embedding.semantic) {
    return {
      tone: "semantic",
      label: "Semantic search active",
      detail: `${embedding.backend} / ${embedding.model}`,
      title:
        "Chunks were embedded by a local neural model, so search ranks by semantic similarity — local embeddings, no cloud. This reflects how the index was built; the mode used for each query is shown with the results.",
    };
  }
  return {
    tone: "lexical",
    label: "Lexical search active",
    detail: embedding.model,
    title:
      "Chunks were embedded by the local lexical model (hashed term frequencies). Results are keyword/intent matches; re-index with an embedding backend for semantic search.",
  };
}

/**
 * How the *last query* was actually ranked, from `VaultSearchResponse.strategy`. This carries the
 * live signal the durable badge cannot: a `lexical-fallback:reindex-required` strategy means the
 * index was built by a different backend than the one configured now, so a re-index is required.
 */
function describeSearchStrategy(strategy: string): RetrievalMode {
  if (strategy.startsWith(SEMANTIC_STRATEGY_PREFIX)) {
    const backendModel = strategy.slice(SEMANTIC_STRATEGY_PREFIX.length);
    return {
      tone: "semantic",
      label: "Ranked by semantic similarity",
      detail: backendModel || null,
      title: "Results ranked by local neural embedding similarity.",
    };
  }
  if (strategy === LEXICAL_FALLBACK_STRATEGY) {
    return {
      tone: "fallback",
      label: "Lexical fallback — re-index for semantic search",
      detail: null,
      title:
        "The index was built by a different embedding backend than the one configured now, so results fall back to lexical ranking over the stored text. Results still work, but relevance may be lower — re-index this workspace to restore semantic search.",
    };
  }
  return {
    tone: "lexical",
    label: "Ranked by lexical similarity",
    detail: null,
    title: "Results ranked by the local lexical model (hashed term frequencies).",
  };
}

function RetrievalModeBadge({ mode }: { mode: RetrievalMode }) {
  return (
    <span className="vault-retrieval-mode" title={mode.title}>
      <span className={RETRIEVAL_BADGE_CLASS[mode.tone]}>{mode.label}</span>
      {mode.detail ? <span className="vault-retrieval-mode__detail">{mode.detail}</span> : null}
    </span>
  );
}

function IndexStatus({ snapshot }: { snapshot: VaultIndexSnapshot }) {
  const summary = snapshot.summary;
  return (
    <div className="vault-index-status-block">
      <div className="vault-index-status">
        <span className="badge badge--clean">Indexed</span>
        <span className="vault-index-when">
          Last indexed{" "}
          <time dateTime={snapshot.indexedAt}>{formatTimestamp(snapshot.indexedAt)}</time>
        </span>
      </div>
      <RetrievalModeBadge mode={describeIndexMode(summary.embedding)} />
      <dl className="vault-index-counts">
        <Count label="Memory items" value={summary.memoryItemCount} />
        <Count label="Chunks" value={summary.chunkCount} />
        <Count label="Code" value={summary.codeFileCount} />
        <Count label="Docs" value={summary.docFileCount} />
        <Count label="Config" value={summary.configFileCount} />
        <Count label="Size" value={formatBytes(summary.totalSizeBytes)} />
        <Count label="Skipped" value={summary.skippedCount} />
      </dl>
      <div className="vault-languages">
        <span>Languages</span>
        <div>
          {summary.languages.length ? (
            summary.languages.slice(0, 8).map((language) => (
              <span className="badge" key={language.value}>
                {language.value} {language.count}
              </span>
            ))
          ) : (
            <small>None detected</small>
          )}
        </div>
      </div>
    </div>
  );
}

function Count({ label, value }: { label: string; value: string | number }) {
  return (
    <div>
      <dt>{label}</dt>
      <dd>{value}</dd>
    </div>
  );
}

function SearchResults({
  response,
  selectedChunkId,
  onSelectHit,
}: {
  response: VaultSearchResponse;
  selectedChunkId: string | null;
  onSelectHit: (hit: VaultSearchHit) => void;
}) {
  return (
    <>
      <div className="vault-index-results-meta">
        <span>
          Showing {response.returned} of {response.total} matches
        </span>
        <RetrievalModeBadge mode={describeSearchStrategy(response.strategy)} />
      </div>
      <ol className="vault-hit-list">
        {response.hits.map((hit, position) => (
          <li key={hit.chunkId}>
            <button
              type="button"
              className="vault-hit"
              aria-pressed={selectedChunkId === hit.chunkId}
              onClick={() => onSelectHit(hit)}
            >
              <span className="vault-hit__rank">#{position + 1}</span>
              <span className="vault-hit__body">
                <span className="vault-hit__path">{hit.path}</span>
                <span className="vault-hit__meta">
                  <span className="badge">{hit.sourceType}</span>
                  {hit.language ? <span className="badge">{hit.language}</span> : null}
                  <span>
                    lines {hit.startLine}–{hit.endLine}
                  </span>
                  <span>score {hit.score.toFixed(3)}</span>
                </span>
                <span className="vault-hit__snippet">{hit.snippet}</span>
              </span>
            </button>
          </li>
        ))}
      </ol>
    </>
  );
}

function isMemoryStale(error: unknown) {
  return error instanceof CoreApiError && error.problem.type === MEMORY_NOT_FOUND_TYPE;
}

function ArchitectureSummaryView({ summary }: { summary: VaultArchitectureSummary }) {
  return (
    <div className="vault-index-summary">
      <dl className="vault-index-counts">
        <Count label="Files" value={summary.fileCount} />
        <Count label="Code" value={summary.codeFileCount} />
        <Count label="Docs" value={summary.docFileCount} />
        <Count label="Config" value={summary.configFileCount} />
        <Count label="Size" value={formatBytes(summary.totalSizeBytes)} />
      </dl>

      {summary.technologies.length ? (
        <div className="vault-languages">
          <span>Technologies</span>
          <div>
            {summary.technologies.map((tech) => (
              <span className="badge" key={tech}>
                {tech}
              </span>
            ))}
          </div>
        </div>
      ) : null}

      {summary.entryPoints.length ? (
        <div className="vault-languages">
          <span>Entry points</span>
          <div>
            {summary.entryPoints.map((entry) => (
              <span className="badge" key={entry}>
                {entry}
              </span>
            ))}
          </div>
        </div>
      ) : null}

      <div className="vault-section-heading">
        <strong>Modules</strong>
        <span>{summary.modules.length}</span>
      </div>
      {summary.modules.length ? (
        <ul className="vault-module-list">
          {summary.modules.map((module) => (
            <li className="vault-module" key={module.path || module.name}>
              <span className="vault-module__name">{module.name}</span>
              <span className="vault-module__meta">
                <span>{module.fileCount} files</span>
                <span>{formatBytes(module.totalSizeBytes)}</span>
                {module.primaryLanguage ? (
                  <span className="badge">{module.primaryLanguage}</span>
                ) : null}
              </span>
            </li>
          ))}
        </ul>
      ) : (
        <EmptyState>No modules detected in the index.</EmptyState>
      )}
    </div>
  );
}

function formatBytes(bytes: number) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KiB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MiB`;
}

function formatTimestamp(iso: string) {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return new Intl.DateTimeFormat("en-US", {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: "UTC",
  }).format(date);
}
