import { Braces, Check, Clock3, Cpu, DatabaseZap, FileOutput, Gauge } from "lucide-react";

import type { ReviewResponse, RunStep } from "../types";
import { StatusBadge } from "./StatusBadge";

const iconByStep: Record<string, typeof Braces> = {
  parse: Braces,
  context: DatabaseZap,
  impact: Gauge,
  artifacts: FileOutput,
  compression: Cpu,
};

export function RunLogView({ review }: { review: ReviewResponse | null }) {
  return (
    <div className="view-stack run-log-view">
      <header className="view-header">
        <div>
          <p className="eyebrow">Execution trace</p>
          <h1>Review run</h1>
        </div>
        {review ? (
          <div className="review-id">
            <Clock3 aria-hidden="true" />
            <span>{new Date(review.created_at).toLocaleTimeString()}</span>
          </div>
        ) : null}
      </header>

      <section className="run-summary">
        <div>
          <span>Run ID</span>
          <code>{review?.id ?? "Pending"}</code>
        </div>
        <div>
          <span>Engine</span>
          <strong>ImpactLint 0.1.0</strong>
        </div>
        <div>
          <span>Total duration</span>
          <strong>{review ? `${review.run_steps.reduce((sum, step) => sum + step.duration_ms, 0)} ms` : "—"}</strong>
        </div>
        <div>
          <span>Decision</span>
          {review ? <StatusBadge status={review.risk_level} /> : <span>Pending</span>}
        </div>
      </section>

      <section className="run-timeline" aria-label="Review execution steps">
        {(review?.run_steps ?? []).map((step, index) => (
          <RunStepRow key={step.id} step={step} index={index + 1} />
        ))}
      </section>

      {review ? (
        <section className="provenance-section">
          <div className="section-heading">
            <div>
              <p className="eyebrow">Analysis provenance</p>
              <h2>Decision sources</h2>
            </div>
          </div>
          <div className="provenance-grid">
            <div>
              <Check aria-hidden="true" />
              <strong>Deterministic</strong>
              <span>SQL AST, lineage traversal, field matching, risk score</span>
            </div>
            <div>
              <Cpu aria-hidden="true" />
              <strong>{review.compression.status === "measured" ? "Paritok measured" : "Model step skipped"}</strong>
              <span>{review.compression.source}</span>
            </div>
          </div>
        </section>
      ) : null}
    </div>
  );
}

function RunStepRow({ step, index }: { step: RunStep; index: number }) {
  const Icon = iconByStep[step.id] ?? Braces;
  return (
    <article className="run-step-row">
      <span className="run-step-index">{index.toString().padStart(2, "0")}</span>
      <span className="run-step-icon">
        <Icon aria-hidden="true" />
      </span>
      <div>
        <h2>{step.label}</h2>
        <p>{step.detail}</p>
      </div>
      <StatusBadge status={step.status} />
      <code>{step.duration_ms} ms</code>
    </article>
  );
}
