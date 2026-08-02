export type Severity = "info" | "low" | "medium" | "high" | "critical";
export type IntegrationStatus = "connected" | "demo" | "unavailable";

export interface Scenario {
  id: string;
  name: string;
  description: string;
  dataset_urn: string;
  change_sql: string;
  dialect: string;
}

export interface ChangeOperation {
  kind: "rename_column" | "drop_column" | "alter_column" | "add_column" | "unknown";
  table: string | null;
  field: string | null;
  replacement: string | null;
  rendered_sql: string;
}

export interface Asset {
  urn: string;
  name: string;
  platform: string;
  kind: string;
  layer: number;
  description: string;
  fields: string[];
  depends_on_fields: string[];
  owners: string[];
  tags: string[];
  quality_signals: string[];
}

export interface GraphEdge {
  source: string;
  target: string;
  kind: string;
}

export interface Evidence {
  source: string;
  label: string;
  value: string;
  asset_urn: string | null;
}

export interface ImpactSignal {
  id: string;
  severity: Severity;
  title: string;
  detail: string;
  evidence: Evidence[];
}

export interface GeneratedArtifact {
  kind: "migration_plan" | "dbt_tests" | "review_manifest" | "compressed_context";
  path: string;
  language: string;
  content: string;
  rationale: string;
}

export interface CompressionMetrics {
  status: "measured" | "not_connected";
  original_tokens: number;
  compressed_tokens: number | null;
  tokens_saved: number | null;
  reduction_percent: number | null;
  source: string;
}

export interface RunStep {
  id: string;
  label: string;
  status: "complete" | "skipped" | "failed";
  detail: string;
  duration_ms: number;
}

export interface Integration {
  id: string;
  label: string;
  status: IntegrationStatus;
  detail: string;
}

export interface ReviewResponse {
  id: string;
  created_at: string;
  risk_score: number;
  risk_level: Severity;
  headline: string;
  summary: string;
  operations: ChangeOperation[];
  target: Asset;
  affected_assets: Asset[];
  graph_assets: Asset[];
  graph_edges: GraphEdge[];
  signals: ImpactSignal[];
  artifacts: GeneratedArtifact[];
  compression: CompressionMetrics;
  run_steps: RunStep[];
  integrations: Integration[];
  publish_status: "not_published" | "published";
}

export interface ReviewRequest {
  dataset_urn: string;
  change_sql: string;
  dialect: string;
}

export interface PublishResponse {
  review_id: string;
  status: "published";
  destination: string;
}
