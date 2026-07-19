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
});
