import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { createTestClient, renderWithAppProviders } from "../../test/render";
import { HealthPanel } from "./HealthPanel";

describe("HealthPanel", () => {
  it("shows the connected Core identity", async () => {
    const client = createTestClient({
      getHealth: () =>
        Promise.resolve({
          status: "ok",
          service: "mensura-core",
          version: "0.1.0",
        }),
    });

    renderWithAppProviders(<HealthPanel />, client);

    expect(await screen.findByText("Healthy")).toBeVisible();
    expect(screen.getByText("mensura-core")).toBeVisible();
    expect(screen.getByText("0.1.0")).toBeVisible();
  });
});
