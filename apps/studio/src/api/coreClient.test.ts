import { describe, expect, it, vi } from "vitest";

import { CoreApiError, createCoreClient } from "./coreClient";

describe("Core client", () => {
  it("returns a typed health response from the configured Core URL", async () => {
    const fetcher = vi.fn(() =>
      Promise.resolve(
        Response.json({ status: "ok", service: "mensura-core", version: "0.1.0" }),
      ),
    );
    const client = createCoreClient({
      baseUrl: "http://core.test/",
      fetcher,
    });

    await expect(client.getHealth()).resolves.toEqual({
      status: "ok",
      service: "mensura-core",
      version: "0.1.0",
    });
    expect(fetcher).toHaveBeenCalledWith("http://core.test/health", undefined);
  });

  it("preserves RFC 9457 fields in CoreApiError", async () => {
    const fetcher = vi.fn(() =>
      Promise.resolve(
        Response.json(
          {
            type: "urn:mensura:problem:resource-not-found",
            title: "Resource not found",
            status: 404,
            detail: "Task 'missing' was not found.",
            instance: "/api/v1/tasks/missing",
          },
          {
            status: 404,
            headers: { "Content-Type": "application/problem+json" },
          },
        ),
      ),
    );
    const client = createCoreClient({ baseUrl: "http://core.test", fetcher });

    const error = await client.getTask("missing").catch((cause: unknown) => cause);

    expect(error).toBeInstanceOf(CoreApiError);
    expect((error as CoreApiError).problem).toMatchObject({
      type: "urn:mensura:problem:resource-not-found",
      status: 404,
      detail: "Task 'missing' was not found.",
    });
  });

  it("turns transport failures into an endpoint-specific connection error", async () => {
    const client = createCoreClient({
      baseUrl: "http://offline.test",
      fetcher: () => Promise.reject(new TypeError("network down")),
    });

    await expect(client.listWorkspaces()).rejects.toThrow(
      "Could not connect to Mensura Core at http://offline.test.",
    );
  });

  it("creates a task with the Core v1 camelCase request", async () => {
    const task = {
      id: "20c74e92-d9fc-4e65-bfbb-4924cc181ed1",
      workspaceId: "5ca252af-76f4-4aed-9718-ff97b610ce90",
      title: "Create the first task",
      description: "Keep the flow vertical.",
      status: "ready" as const,
      assignedRole: "coder" as const,
      createdAt: "2026-07-19T12:00:00Z",
      updatedAt: "2026-07-19T12:00:00Z",
    };
    const fetcher = vi.fn(() => Promise.resolve(Response.json(task, { status: 201 })));
    const client = createCoreClient({ baseUrl: "http://core.test", fetcher });

    await expect(
      client.createTask({
        workspaceId: task.workspaceId,
        title: task.title,
        description: task.description,
        assignedRole: "coder",
      }),
    ).resolves.toEqual(task);
    expect(fetcher).toHaveBeenCalledWith("http://core.test/api/v1/tasks", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        workspaceId: task.workspaceId,
        title: task.title,
        description: task.description,
        assignedRole: "coder",
      }),
    });
  });

  it("creates a queued run for an encoded task ID", async () => {
    const contextPackId = `sha256:${"a".repeat(64)}` as const;
    const run = {
      id: "9dc58c91-105d-43af-95cb-32e546ce4c9f",
      taskId: "task/id",
      contextPackId,
      contextPack: {
        id: contextPackId,
        workspaceId: "workspace/id",
        inventoryId: "inventory/id",
        schemaVersion: "1" as const,
        fileCount: 2,
        totalFileBytes: 2048,
        totalPreviewBytes: 1024,
      },
      status: "queued" as const,
      execution: null,
      startedAt: null,
      finishedAt: null,
      createdAt: "2026-07-19T12:05:00Z",
      updatedAt: "2026-07-19T12:05:00Z",
    };
    const fetcher = vi.fn(() => Promise.resolve(Response.json(run, { status: 201 })));
    const client = createCoreClient({ baseUrl: "http://core.test", fetcher });

    await expect(
      client.createRun(run.taskId, { contextPackId }),
    ).resolves.toEqual(run);
    expect(fetcher).toHaveBeenCalledWith(
      "http://core.test/api/v1/tasks/task%2Fid/runs",
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ contextPackId }),
      },
    );
  });

  it("manually executes an encoded run ID with explicit provider selection", async () => {
    const run = {
      id: "run/id",
      status: "succeeded" as const,
    };
    const fetcher = vi.fn(() => Promise.resolve(Response.json(run)));
    const client = createCoreClient({ baseUrl: "http://core.test", fetcher });

    await expect(
      client.executeRun(run.id, { providerId: "openai" }),
    ).resolves.toEqual(run);
    expect(fetcher).toHaveBeenCalledWith(
      "http://core.test/api/v1/runs/run%2Fid/execute",
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ providerId: "openai" }),
      },
    );
  });

  it("lists providers and saves write-only OpenAI configuration", async () => {
    const fetcher = vi.fn(() =>
      Promise.resolve(
        Response.json({
          id: "openai",
          name: "OpenAI",
          kind: "real",
          configured: true,
          model: "gpt-5-mini",
          promptVersion: "review.v2",
        }),
      ),
    );
    const client = createCoreClient({ baseUrl: "http://core.test", fetcher });

    await client.listProviders();
    expect(fetcher).toHaveBeenNthCalledWith(
      1,
      "http://core.test/api/v1/providers",
      undefined,
    );

    await client.configureOpenAIProvider({
      apiKey: "sk-local-write-only",
      model: "gpt-5-mini",
    });
    expect(fetcher).toHaveBeenNthCalledWith(
      2,
      "http://core.test/api/v1/providers/openai/config",
      {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          apiKey: "sk-local-write-only",
          model: "gpt-5-mini",
        }),
      },
    );
  });

  it("retrieves repository metadata for an encoded workspace ID", async () => {
    const summary = {
      workspaceId: "workspace/id",
      isRepository: true as const,
      branch: "main",
      isDirty: false,
      stagedCount: 0,
      unstagedCount: 0,
      untrackedCount: 0,
      changedPathsCount: 0,
      diffMetadata: [],
    };
    const fetcher = vi.fn(() => Promise.resolve(Response.json(summary)));
    const client = createCoreClient({ baseUrl: "http://core.test", fetcher });

    await expect(
      client.getWorkspaceRepository(summary.workspaceId),
    ).resolves.toEqual(summary);
    expect(fetcher).toHaveBeenCalledWith(
      "http://core.test/api/v1/workspaces/workspace%2Fid/repository",
      undefined,
    );
  });

  it("creates and retrieves Guard runs for an encoded workspace ID", async () => {
    const run = {
      id: "cce3fd08-ea41-45b0-ac24-d0349acb18b8",
      workspaceId: "workspace/id",
      status: "passed" as const,
      blocking: false,
      summary: {
        totalCount: 0,
        passedCount: 0,
        failedCount: 0,
        errorCount: 0,
        blockingFailures: 0,
        isBlocking: false,
      },
      checks: [],
      startedAt: "2026-07-19T13:00:00Z",
      completedAt: "2026-07-19T13:00:00Z",
      durationMs: 0,
    };
    const fetcher = vi.fn(() => Promise.resolve(Response.json(run, { status: 201 })));
    const client = createCoreClient({ baseUrl: "http://core.test", fetcher });

    await expect(client.createGuardRun(run.workspaceId, {})).resolves.toEqual(run);
    expect(fetcher).toHaveBeenNthCalledWith(
      1,
      "http://core.test/api/v1/workspaces/workspace%2Fid/guard/runs",
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: "{}",
      },
    );

    await expect(client.getLatestGuardRun(run.workspaceId)).resolves.toEqual(run);
    expect(fetcher).toHaveBeenNthCalledWith(
      2,
      "http://core.test/api/v1/workspaces/workspace%2Fid/guard/runs/latest",
      undefined,
    );
  });

  it("builds and retrieves typed Vault inventory resources with encoded filters", async () => {
    const fetcher = vi.fn(() => Promise.resolve(Response.json({ status: "ready" })));
    const client = createCoreClient({ baseUrl: "http://core.test", fetcher });
    const workspaceId = "workspace/id";

    await client.buildVaultInventory(workspaceId);
    expect(fetcher).toHaveBeenNthCalledWith(
      1,
      "http://core.test/api/v1/workspaces/workspace%2Fid/vault/inventory",
      { method: "POST" },
    );

    await client.getVaultInventory(workspaceId);
    expect(fetcher).toHaveBeenNthCalledWith(
      2,
      "http://core.test/api/v1/workspaces/workspace%2Fid/vault/inventory",
      undefined,
    );

    await client.listVaultFiles(workspaceId, {
      query: "src/",
      extension: "PY",
      limit: 25,
    });
    expect(fetcher).toHaveBeenNthCalledWith(
      3,
      "http://core.test/api/v1/workspaces/workspace%2Fid/vault/files?query=src%2F&extension=PY&limit=25",
      undefined,
    );

    await client.getVaultFilePreview(workspaceId, "src/main.py");
    expect(fetcher).toHaveBeenNthCalledWith(
      4,
      "http://core.test/api/v1/workspaces/workspace%2Fid/vault/files/content?path=src%2Fmain.py",
      undefined,
    );
  });

  it("creates, lists, and retrieves immutable context packs", async () => {
    const fetcher = vi.fn(() => Promise.resolve(Response.json({ items: [], total: 0 })));
    const client = createCoreClient({ baseUrl: "http://core.test", fetcher });
    const workspaceId = "workspace/id";
    const packId = `sha256:${"a".repeat(64)}`;

    await client.createContextPack(workspaceId, { paths: ["src/main.py"] });
    expect(fetcher).toHaveBeenNthCalledWith(
      1,
      "http://core.test/api/v1/workspaces/workspace%2Fid/context-packs",
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ paths: ["src/main.py"] }),
      },
    );

    await client.listContextPacks(workspaceId);
    expect(fetcher).toHaveBeenNthCalledWith(
      2,
      "http://core.test/api/v1/workspaces/workspace%2Fid/context-packs",
      undefined,
    );

    await client.getContextPack(workspaceId, packId);
    expect(fetcher).toHaveBeenNthCalledWith(
      3,
      `http://core.test/api/v1/workspaces/workspace%2Fid/context-packs/${encodeURIComponent(packId)}`,
      undefined,
    );
  });

  it("creates, discovers, retrieves, and reviews change proposals", async () => {
    const fetcher = vi.fn(() =>
      Promise.resolve(Response.json({ items: [], total: 0 }, { status: 200 })),
    );
    const client = createCoreClient({ baseUrl: "http://core.test", fetcher });

    await client.createChangeProposal("run/id");
    expect(fetcher).toHaveBeenNthCalledWith(
      1,
      "http://core.test/api/v1/runs/run%2Fid/change-proposals",
      { method: "POST" },
    );

    await client.listChangeProposals("workspace/id");
    expect(fetcher).toHaveBeenNthCalledWith(
      2,
      "http://core.test/api/v1/workspaces/workspace%2Fid/change-proposals",
      undefined,
    );

    await client.getChangeProposal("proposal/id");
    expect(fetcher).toHaveBeenNthCalledWith(
      3,
      "http://core.test/api/v1/change-proposals/proposal%2Fid",
      undefined,
    );

    await client.approveChangeProposal("proposal/id");
    expect(fetcher).toHaveBeenNthCalledWith(
      4,
      "http://core.test/api/v1/change-proposals/proposal%2Fid/approve",
      { method: "POST" },
    );

    await client.rejectChangeProposal("proposal/id");
    expect(fetcher).toHaveBeenNthCalledWith(
      5,
      "http://core.test/api/v1/change-proposals/proposal%2Fid/reject",
      { method: "POST" },
    );
  });

  it("verifies proposals in the sandbox and reads verification artifacts", async () => {
    const fetcher = vi.fn(() =>
      Promise.resolve(Response.json({ items: [], total: 0 }, { status: 200 })),
    );
    const client = createCoreClient({ baseUrl: "http://core.test", fetcher });

    await client.verifyChangeProposal("proposal/id");
    expect(fetcher).toHaveBeenNthCalledWith(
      1,
      "http://core.test/api/v1/change-proposals/proposal%2Fid/verify",
      { method: "POST" },
    );

    await client.listChangeProposalVerifications("proposal/id");
    expect(fetcher).toHaveBeenNthCalledWith(
      2,
      "http://core.test/api/v1/change-proposals/proposal%2Fid/verifications",
      undefined,
    );

    await client.getChangeProposalVerification("verification/id");
    expect(fetcher).toHaveBeenNthCalledWith(
      3,
      "http://core.test/api/v1/verifications/verification%2Fid",
      undefined,
    );
  });

  it("applies a proposal and reads application artifacts on encoded routes", async () => {
    const fetcher = vi.fn(() =>
      Promise.resolve(Response.json({ items: [], total: 0 }, { status: 200 })),
    );
    const client = createCoreClient({ baseUrl: "http://core.test", fetcher });

    await client.applyChangeProposal("proposal/id", {
      verificationId: "verification/id",
    });
    expect(fetcher).toHaveBeenNthCalledWith(
      1,
      "http://core.test/api/v1/change-proposals/proposal%2Fid/apply",
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ verificationId: "verification/id" }),
      },
    );

    await client.getApplication("application/id");
    expect(fetcher).toHaveBeenNthCalledWith(
      2,
      "http://core.test/api/v1/applications/application%2Fid",
      undefined,
    );

    await client.listWorkspaceApplications("workspace/id");
    expect(fetcher).toHaveBeenNthCalledWith(
      3,
      "http://core.test/api/v1/workspaces/workspace%2Fid/applications",
      undefined,
    );
  });
});
