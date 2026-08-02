import { useMemo, useState } from "react";
import {
  Check,
  Clipboard,
  Download,
  FileCode2,
  GitPullRequestArrow,
  LoaderCircle,
  Play,
  Send,
  Zap,
} from "lucide-react";

import type { GeneratedArtifact, ReviewRequest, ReviewResponse, Scenario } from "../types";
import { StatusBadge } from "./StatusBadge";

interface ReviewViewProps {
  scenarios: Scenario[];
  draft: ReviewRequest;
  onDraftChange: (draft: ReviewRequest) => void;
  review: ReviewResponse | null;
  loading: boolean;
  publishing: boolean;
  publishDestination: string | null;
  error: string | null;
  onRun: () => void;
  onPublish: () => void;
}

function downloadArtifact(artifact: GeneratedArtifact) {
  const blob = new Blob([artifact.content], { type: "text/plain;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = artifact.path.split("/").at(-1) ?? "impactlint-artifact.txt";
  anchor.click();
  URL.revokeObjectURL(url);
}

export function ReviewView({
  scenarios,
  draft,
  onDraftChange,
  review,
  loading,
  publishing,
  publishDestination,
  error,
  onRun,
  onPublish,
}: ReviewViewProps) {
  const [artifactIndex, setArtifactIndex] = useState(0);
  const [copied, setCopied] = useState(false);
  const artifact = review?.artifacts[artifactIndex] ?? review?.artifacts[0];
  const ownerCount = useMemo(
    () =>
      new Set(
        review ? [review.target, ...review.affected_assets].flatMap((asset) => asset.owners) : [],
      ).size,
    [review],
  );

  function chooseScenario(id: string) {
    const scenario = scenarios.find((candidate) => candidate.id === id);
    if (!scenario) return;
    onDraftChange({
      dataset_urn: scenario.dataset_urn,
      change_sql: scenario.change_sql,
      dialect: scenario.dialect,
    });
  }

  async function copyArtifact() {
    if (!artifact) return;
    await navigator.clipboard.writeText(artifact.content);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1400);
  }

  return (
    <div className="view-stack">
      <header className="view-header">
        <div>
          <p className="eyebrow">Change review</p>
          <h1>Review a warehouse contract</h1>
        </div>
        {review ? (
          <div className="review-id">
            <GitPullRequestArrow aria-hidden="true" />
            <span>Review {review.id.slice(0, 8)}</span>
          </div>
        ) : null}
      </header>

      <div className="review-grid">
        <section className="change-editor" aria-labelledby="change-editor-title">
          <div className="section-heading compact-heading">
            <div>
              <h2 id="change-editor-title">Proposed change</h2>
              <p>Snowflake · analytics repository</p>
            </div>
          </div>

          <label className="field-label" htmlFor="scenario">
            Scenario
          </label>
          <select id="scenario" defaultValue={scenarios[0]?.id} onChange={(event) => chooseScenario(event.target.value)}>
            {scenarios.map((scenario) => (
              <option key={scenario.id} value={scenario.id}>
                {scenario.name}
              </option>
            ))}
          </select>

          <label className="field-label" htmlFor="dataset-urn">
            Dataset URN
          </label>
          <input
            id="dataset-urn"
            className="mono-input"
            value={draft.dataset_urn}
            onChange={(event) => onDraftChange({ ...draft, dataset_urn: event.target.value })}
          />

          <div className="editor-label-row">
            <label className="field-label" htmlFor="change-sql">
              SQL migration
            </label>
            <span>{draft.dialect}</span>
          </div>
          <textarea
            id="change-sql"
            className="sql-editor"
            spellCheck={false}
            value={draft.change_sql}
            onChange={(event) => onDraftChange({ ...draft, change_sql: event.target.value })}
          />

          {error ? <div className="inline-error">{error}</div> : null}

          <button className="primary-button run-button" type="button" onClick={onRun} disabled={loading}>
            {loading ? <LoaderCircle className="spin" aria-hidden="true" /> : <Play aria-hidden="true" />}
            {loading ? "Reviewing change" : "Review change"}
          </button>
        </section>

        <section className="review-result" aria-live="polite" aria-busy={loading}>
          {review ? (
            <>
              <div className="decision-row">
                <div className={`risk-score risk-${review.risk_level}`}>
                  <strong>{review.risk_score}</strong>
                  <span>Risk / 100</span>
                </div>
                <div className="decision-copy">
                  <StatusBadge status={review.risk_level} />
                  <h2>{review.headline}</h2>
                  <p>{review.summary}</p>
                </div>
              </div>

              <div className="risk-meter" aria-label={`Risk score ${review.risk_score} out of 100`}>
                <span style={{ width: `${review.risk_score}%` }} />
              </div>

              <div className="metric-strip">
                <div>
                  <strong>{review.affected_assets.length}</strong>
                  <span>Affected assets</span>
                </div>
                <div>
                  <strong>{ownerCount}</strong>
                  <span>Owner groups</span>
                </div>
                <div>
                  <strong>{review.signals.length}</strong>
                  <span>Evidence groups</span>
                </div>
                <div>
                  <strong>{review.compression.original_tokens.toLocaleString()}</strong>
                  <span>Context tokens</span>
                </div>
              </div>

              {review.compression.status === "measured" ? (
                <div className="compression-result">
                  <Zap aria-hidden="true" />
                  <div>
                    <strong>{review.compression.reduction_percent}% fewer final context tokens</strong>
                    <span>
                      Paritok GPU output: {review.compression.model_output_tokens?.toLocaleString()} tokens ·{" "}
                      {review.compression.source_lines_selected} source lines selected ·{" "}
                      {review.compression.evidence_lines_restored} evidence{" "}
                      {review.compression.evidence_lines_restored === 1 ? "line" : "lines"} restored
                    </span>
                  </div>
                  <code>
                    {review.compression.original_tokens.toLocaleString()} →{" "}
                    {review.compression.compressed_tokens?.toLocaleString()}
                  </code>
                </div>
              ) : null}

              <div className="result-actions">
                <span className="deterministic-label">
                  <Check aria-hidden="true" /> Deterministic impact analysis
                </span>
                <button
                  className="secondary-button"
                  type="button"
                  onClick={onPublish}
                  disabled={publishing || review.publish_status === "published"}
                >
                  {review.publish_status === "published" ? (
                    <Check aria-hidden="true" />
                  ) : publishing ? (
                    <LoaderCircle className="spin" aria-hidden="true" />
                  ) : (
                    <Send aria-hidden="true" />
                  )}
                  {review.publish_status === "published" ? "Published" : "Publish evidence"}
                </button>
              </div>
              {publishDestination ? <p className="publish-destination">{publishDestination}</p> : null}
            </>
          ) : (
            <ResultSkeleton />
          )}
        </section>
      </div>

      {review ? (
        <>
          <section className="evidence-section" aria-labelledby="evidence-title">
            <div className="section-heading">
              <div>
                <p className="eyebrow">Traceable findings</p>
                <h2 id="evidence-title">Evidence</h2>
              </div>
              <span>{review.signals.reduce((sum, signal) => sum + signal.evidence.length, 0)} records</span>
            </div>
            <div className="signal-list">
              {review.signals.map((signal) => (
                <article className="signal-row" key={signal.id}>
                  <div className="signal-summary">
                    <StatusBadge status={signal.severity} />
                    <div>
                      <h3>{signal.title}</h3>
                      <p>{signal.detail}</p>
                    </div>
                  </div>
                  <div className="evidence-records">
                    {signal.evidence.map((evidence, index) => (
                      <div className="evidence-record" key={`${evidence.label}-${index}`}>
                        <span>{evidence.source}</span>
                        <strong>{evidence.label}</strong>
                        <code>{evidence.value}</code>
                      </div>
                    ))}
                  </div>
                </article>
              ))}
            </div>
          </section>

          <section className="artifacts-section" aria-labelledby="artifacts-title">
            <div className="section-heading">
              <div>
                <p className="eyebrow">Generated output</p>
                <h2 id="artifacts-title">Migration artifacts</h2>
              </div>
              <div className="icon-actions">
                <button className="icon-button" type="button" onClick={copyArtifact} title="Copy artifact">
                  {copied ? <Check aria-hidden="true" /> : <Clipboard aria-hidden="true" />}
                  <span className="sr-only">Copy artifact</span>
                </button>
                <button
                  className="icon-button"
                  type="button"
                  onClick={() => artifact && downloadArtifact(artifact)}
                  title="Download artifact"
                >
                  <Download aria-hidden="true" />
                  <span className="sr-only">Download artifact</span>
                </button>
              </div>
            </div>

            <div className="artifact-tabs" role="tablist" aria-label="Generated artifacts">
              {review.artifacts.map((item, index) => (
                <button
                  type="button"
                  role="tab"
                  aria-selected={artifactIndex === index}
                  className={artifactIndex === index ? "is-active" : ""}
                  key={item.path}
                  onClick={() => setArtifactIndex(index)}
                >
                  <FileCode2 aria-hidden="true" />
                  {item.path.split("/").at(-1)}
                </button>
              ))}
            </div>
            {artifact ? (
              <div className="artifact-body">
                <div className="artifact-meta">
                  <code>{artifact.path}</code>
                  <span>{artifact.rationale}</span>
                </div>
                <pre>
                  <code>{artifact.content}</code>
                </pre>
              </div>
            ) : null}
          </section>
        </>
      ) : null}
    </div>
  );
}

function ResultSkeleton() {
  return (
    <div className="result-skeleton" aria-label="Waiting for review">
      <div className="skeleton skeleton-score" />
      <div>
        <div className="skeleton skeleton-label" />
        <div className="skeleton skeleton-title" />
        <div className="skeleton skeleton-line" />
        <div className="skeleton skeleton-line short" />
      </div>
    </div>
  );
}
