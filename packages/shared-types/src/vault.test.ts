import { describe, expect, it } from "vitest";

import { VAULT_FILE_KINDS, VAULT_INVENTORY_STATUSES } from "./vault.js";

describe("Vault v1 contracts", () => {
  it("keeps the inventory lifecycle intentionally minimal", () => {
    expect(VAULT_INVENTORY_STATUSES).toEqual(["ready"]);
  });

  it("uses a conservative text or binary classification", () => {
    expect(VAULT_FILE_KINDS).toEqual(["text", "binary"]);
  });
});
