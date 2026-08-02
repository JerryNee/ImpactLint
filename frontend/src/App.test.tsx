import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";

import App from "./App";
import type { Integration, ReviewResponse, Scenario } from "./types";

const scenario: Scenario = {
  id: "rename",
  name: "Rename shared key",
  description: "Breaking change",
  dataset_urn: "urn:root",
  change_sql: "ALTER TABLE customer_360 RENAME COLUMN customer_id TO customer_key;",
  dialect: "snowflake",
};

const integrations: Integration[] = [
  { id: "datahub", label: "DataHub MCP", status: "demo", detail: "Seeded demo catalog" },
  { id: "paritok", label: "Paritok", status: "unavailable", detail: "Add API keys to measure" },
];

const asset = {
  urn: "urn:root",
  name: "analytics.customer_360",
  platform: "Snowflake",
  kind: "dataset",
  layer: 0,
  description: "Canonical customer profile",
  fields: ["customer_id"],
  depends_on_fields: [],
  owners: ["Customer Data Platform"],
  tags: ["Tier 1"],
  quality_signals: ["uniqueness"],
};

const review: ReviewResponse = {
  id: "review-1234",
  created_at: "2026-08-01T12:00:00Z",
  risk_score: 92,
  risk_level: "critical",
  headline: "Critical risk: coordinate before merge",
  summary: "Changing customer_id reaches one downstream asset.",
  operations: [
    {
      kind: "rename_column",
      table: "customer_360",
      field: "customer_id",
      replacement: "customer_key",
      rendered_sql: scenario.change_sql,
    },
  ],
  target: asset,
  affected_assets: [{ ...asset, urn: "urn:child", name: "finance.monthly_revenue", layer: 1 }],
  graph_assets: [asset],
  graph_edges: [],
  signals: [
    {
      id: "breaking",
      severity: "high",
      title: "Breaking schema operation",
      detail: "Consumers require a coordinated migration.",
      evidence: [{ source: "SQL parser", label: "Operation", value: "RENAME", asset_urn: "urn:root" }],
    },
  ],
  artifacts: [
    {
      kind: "migration_plan",
      path: "artifacts/migration-plan.md",
      language: "markdown",
      content: "# Migration plan",
      rationale: "Coordinates the change.",
    },
  ],
  compression: {
    status: "not_connected",
    original_tokens: 420,
    compressed_tokens: null,
    model_output_tokens: null,
    tokens_saved: null,
    reduction_percent: null,
    source_lines_selected: 0,
    evidence_lines_checked: 0,
    evidence_lines_restored: 0,
    evidence_terms_checked: 0,
    evidence_terms_restored: 0,
    source: "Local token count",
  },
  run_steps: [
    { id: "parse", label: "Parse proposed SQL", status: "complete", detail: "sqlglot", duration_ms: 2 },
  ],
  integrations,
  publish_status: "not_published",
};

afterEach(() => vi.restoreAllMocks());

test("loads a complete review workflow on first render", async () => {
  vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
    const url = String(input);
    const payload = url.endsWith("/api/scenarios") ? [scenario] : url.endsWith("/api/integrations") ? integrations : review;
    return new Response(JSON.stringify(payload), { status: 200, headers: { "Content-Type": "application/json" } });
  });

  render(<App />);

  expect(screen.getByText("ImpactLint")).toBeInTheDocument();
  await waitFor(() => expect(screen.getByText("Critical risk: coordinate before merge")).toBeInTheDocument());
  expect(screen.getByRole("button", { name: "Review change" })).toBeEnabled();
  expect(screen.getByText("Breaking schema operation")).toBeInTheDocument();
  expect(globalThis.fetch).toHaveBeenCalledTimes(3);
});
