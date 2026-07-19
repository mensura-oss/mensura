import type {
  ProviderDescriptor,
  ProviderId,
  Run,
  RunExecutionResult,
} from "@mensura/shared-types";
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { useCoreClient } from "../../api/CoreClientProvider";
import { queryKeys } from "../../app/queryClient";
import { ProblemDetailsView } from "../../components/ProblemDetailsView";

export function RunExecutionPanel({ run }: { run: Run }) {
  const client = useCoreClient();
  const queryClient = useQueryClient();
  const [selectedProviderId, setSelectedProviderId] =
    useState<ProviderId>("mensura.builtin");
  const providers = useQuery({
    queryKey: queryKeys.providers,
    queryFn: () => client.listProviders(),
    enabled: run.status === "queued",
    retry: false,
  });
  const availableProviders = providers.data?.items ?? [DETERMINISTIC_PROVIDER];
  const selectedProvider = availableProviders.find(
    (provider) => provider.id === selectedProviderId,
  ) ?? DETERMINISTIC_PROVIDER;
  const execute = useMutation({
    mutationFn: () =>
      client.executeRun(run.id, { providerId: selectedProvider.id }),
    onSuccess: (executedRun) => {
      queryClient.setQueryData(queryKeys.run(executedRun.id), executedRun);
    },
    onSettled: async () => {
      await queryClient.invalidateQueries({ queryKey: queryKeys.run(run.id) });
    },
  });
  const visibleStatus = execute.isPending ? "running" : run.status;

  return (
    <section className="run-execution" aria-labelledby={`run-execution-${run.id}`}>
      <div className="run-execution__heading">
        <div>
          <span>Manual provider boundary</span>
          <h4 id={`run-execution-${run.id}`}>Execution</h4>
        </div>
        <span className={`badge badge--${visibleStatus}`}>{visibleStatus}</span>
      </div>

      {run.execution ? (
        <dl className="run-provider">
          <div>
            <dt>Provider</dt>
            <dd>{run.execution.provider.providerId}</dd>
          </div>
          <div>
            <dt>Kind</dt>
            <dd>{run.execution.provider.providerKind}</dd>
          </div>
          <div>
            <dt>Adapter</dt>
            <dd>
              {run.execution.provider.adapterId} · v
              {run.execution.provider.adapterVersion}
            </dd>
          </div>
          <div>
            <dt>Model</dt>
            <dd>{run.execution.provider.model ?? "No model (deterministic)"}</dd>
          </div>
          <div>
            <dt>Duration</dt>
            <dd>
              {run.execution.durationMs === null
                ? "In progress"
                : formatDuration(run.execution.durationMs)}
            </dd>
          </div>
          <div>
            <dt>Prompt</dt>
            <dd>{run.execution.provider.promptVersion}</dd>
          </div>
        </dl>
      ) : null}

      {run.status === "queued" ? (
        <div className="run-execution__action">
          <div className="run-provider-selection">
            <label className="form-field">
              <span>Execution provider</span>
              <select
                value={selectedProvider.id}
                onChange={(event) => {
                  setSelectedProviderId(event.target.value as ProviderId);
                  execute.reset();
                }}
                disabled={execute.isPending}
              >
                {availableProviders.map((provider) => (
                  <option
                    key={provider.id}
                    value={provider.id}
                    disabled={!provider.configured}
                  >
                    {provider.name}
                    {provider.configured ? "" : " · configure first"}
                  </option>
                ))}
              </select>
            </label>
            <p>
              Selected: {selectedProvider.kind} · {selectedProvider.promptVersion}
              {selectedProvider.model ? ` · ${selectedProvider.model}` : ""}. Execution
              uses only the persisted task and immutable context pack.
            </p>
          </div>
          <button
            className="button button--secondary"
            type="button"
            onClick={() => execute.mutate()}
            disabled={execute.isPending || !selectedProvider.configured}
          >
            {execute.isPending ? "Execution running…" : "Execute run"}
          </button>
        </div>
      ) : null}

      {providers.isError && run.status === "queued" ? (
        <ProblemDetailsView error={providers.error} />
      ) : null}

      {execute.isPending ? (
        <p className="run-execution__pending" role="status">
          Core is running the provider against the immutable execution context…
        </p>
      ) : null}
      {run.status === "running" && !execute.isPending ? (
        <p className="run-execution__pending" role="status">
          Provider execution is running. This view refreshes until Core records a
          terminal result.
        </p>
      ) : null}
      {execute.isError ? <ProblemDetailsView error={execute.error} /> : null}
      {run.execution?.result ? (
        <ExecutionResult result={run.execution.result} />
      ) : null}
      {run.execution?.failure ? (
        <div className="run-execution-failure" role="alert">
          <strong>{formatFailureCode(run.execution.failure.code)}</strong>
          <span>{run.execution.failure.summary}</span>
        </div>
      ) : null}
    </section>
  );
}

const DETERMINISTIC_PROVIDER: ProviderDescriptor = {
  id: "mensura.builtin",
  name: "Deterministic review",
  kind: "deterministic",
  configured: true,
  model: null,
  promptVersion: "review.v1",
};

function ExecutionResult({ result }: { result: RunExecutionResult }) {
  return (
    <div className="run-result" aria-live="polite">
      <div className="run-result__copy">
        <div>
          <span>Task summary</span>
          <p>{result.taskSummary}</p>
        </div>
        <div>
          <span>Interpreted intent</span>
          <p>{result.interpretedIntent}</p>
        </div>
      </div>

      <dl className="run-result__context">
        <div>
          <dt>Files</dt>
          <dd>{result.context.fileCount.toLocaleString()}</dd>
        </div>
        <div>
          <dt>Text / binary</dt>
          <dd>
            {result.context.textFileCount} / {result.context.binaryFileCount}
          </dd>
        </div>
        <div>
          <dt>Preview bytes</dt>
          <dd>{result.context.totalPreviewBytes.toLocaleString()}</dd>
        </div>
        <div>
          <dt>Truncated</dt>
          <dd>{result.context.truncatedTextFileCount.toLocaleString()}</dd>
        </div>
      </dl>
      <p className="run-result__identity">
        Context <code>{result.context.contextPackId}</code>
      </p>
      <p className="run-result__identity">
        Languages: {result.context.languages.join(", ") || "Not detected"}
      </p>

      <ResultList
        title="Warnings"
        items={result.warnings}
        empty="No provider warnings."
      />
      <ResultList
        title="Recommended next steps"
        items={result.recommendedNextSteps}
      />
    </div>
  );
}

function ResultList({
  title,
  items,
  empty,
}: {
  title: string;
  items: readonly string[];
  empty?: string;
}) {
  return (
    <div className="run-result__list">
      <strong>{title}</strong>
      {items.length ? (
        <ul>
          {items.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      ) : (
        <span>{empty}</span>
      )}
    </div>
  );
}

function formatDuration(durationMs: number) {
  return durationMs < 1000 ? `${durationMs} ms` : `${(durationMs / 1000).toFixed(2)} s`;
}

function formatFailureCode(code: string) {
  if (code === "structured_result_invalid") return "Structured result invalid";
  if (code === "provider_credentials_invalid") return "Provider credentials invalid";
  if (code === "provider_upstream_failed") return "Upstream provider failed";
  return "Provider execution failed";
}
