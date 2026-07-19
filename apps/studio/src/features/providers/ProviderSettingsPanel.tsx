import { useEffect, useRef, useState, type FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { useCoreClient } from "../../api/CoreClientProvider";
import { queryKeys } from "../../app/queryClient";
import { LoadingState } from "../../components/AsyncState";
import { Panel } from "../../components/Panel";
import { ProblemDetailsView } from "../../components/ProblemDetailsView";

export function ProviderSettingsPanel() {
  const client = useCoreClient();
  const queryClient = useQueryClient();
  const [apiKey, setApiKey] = useState("");
  const [model, setModel] = useState("");
  const [attempted, setAttempted] = useState(false);
  const initializedModel = useRef(false);
  const providers = useQuery({
    queryKey: queryKeys.providers,
    queryFn: () => client.listProviders(),
    retry: false,
  });
  const openai = providers.data?.items.find((provider) => provider.id === "openai");

  useEffect(() => {
    if (!initializedModel.current && openai) {
      setModel(openai.model ?? "");
      initializedModel.current = true;
    }
  }, [openai]);

  const keyError = attempted && apiKey.trim().length < 20
    ? "Enter a complete API key (at least 20 characters)."
    : "";
  const modelError = attempted && !/^[A-Za-z0-9][A-Za-z0-9._:-]*$/.test(model.trim())
    ? "Enter a valid provider model ID."
    : "";
  const configure = useMutation({
    mutationFn: () =>
      client.configureOpenAIProvider({
        apiKey: apiKey.trim(),
        model: model.trim(),
      }),
    onSuccess: async () => {
      setApiKey("");
      setAttempted(false);
      await queryClient.invalidateQueries({ queryKey: queryKeys.providers });
    },
  });

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setAttempted(true);
    configure.reset();
    if (apiKey.trim().length < 20) return;
    if (!/^[A-Za-z0-9][A-Za-z0-9._:-]*$/.test(model.trim())) return;
    configure.mutate();
  }

  return (
    <Panel eyebrow="Local BYOK" title="Model provider">
      <div className="provider-status-row">
        <div>
          <strong>Deterministic review</strong>
          <span>Always available · review.v1</span>
        </div>
        <span className="badge badge--passed">default</span>
      </div>

      {providers.isPending ? <LoadingState>Reading local provider state…</LoadingState> : null}
      {providers.isError ? <ProblemDetailsView error={providers.error} /> : null}
      {openai ? (
        <div className="provider-status-row">
          <div>
            <strong>OpenAI</strong>
            <span>
              {openai.model ?? "No model saved"} · {openai.promptVersion}
            </span>
          </div>
          <span className={`badge badge--${openai.configured ? "passed" : "queued"}`}>
            {openai.configured ? "configured" : "not configured"}
          </span>
        </div>
      ) : null}

      <form className="provider-config-form" onSubmit={handleSubmit} noValidate>
        <label className="form-field">
          <span>OpenAI model</span>
          <input
            aria-label="OpenAI model"
            value={model}
            onChange={(event) => setModel(event.target.value)}
            placeholder="gpt-5-mini"
            aria-invalid={Boolean(modelError)}
            aria-describedby={modelError ? "provider-model-error" : undefined}
            autoComplete="off"
          />
          {modelError ? <small id="provider-model-error">{modelError}</small> : null}
        </label>
        <label className="form-field">
          <span>OpenAI API key</span>
          <input
            aria-label="OpenAI API key"
            type="password"
            value={apiKey}
            onChange={(event) => setApiKey(event.target.value)}
            placeholder={openai?.configured ? "Replace saved key" : "Write-only key"}
            aria-invalid={Boolean(keyError)}
            aria-describedby={keyError ? "provider-key-error" : "provider-key-help"}
            autoComplete="new-password"
          />
          {keyError ? (
            <small id="provider-key-error">{keyError}</small>
          ) : (
            <small id="provider-key-help">
              Core stores this in the OS credential backend and never returns it.
            </small>
          )}
        </label>
        <button className="button button--secondary" type="submit" disabled={configure.isPending}>
          {configure.isPending ? "Saving provider…" : "Save OpenAI config"}
        </button>
      </form>

      {configure.isSuccess ? (
        <p className="success-message" role="status">
          OpenAI configuration saved locally. The key field was cleared.
        </p>
      ) : null}
      {configure.isError ? <ProblemDetailsView error={configure.error} /> : null}
    </Panel>
  );
}
