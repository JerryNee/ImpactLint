import { CircleAlert, Database, ShieldCheck, UserRound } from "lucide-react";

import type { Asset, ReviewResponse } from "../types";
import { LineageGraph } from "./LineageGraph";
import { StatusBadge } from "./StatusBadge";

interface LineageViewProps {
  review: ReviewResponse | null;
  selectedAsset: Asset | null;
  onSelectAsset: (urn: string) => void;
}

export function LineageView({ review, selectedAsset, onSelectAsset }: LineageViewProps) {
  const affected = new Set(review?.affected_assets.map((asset) => asset.urn) ?? []);

  return (
    <div className="view-stack lineage-view">
      <header className="view-header">
        <div>
          <p className="eyebrow">DataHub context</p>
          <h1>Impact graph</h1>
        </div>
        {review ? <StatusBadge status={review.risk_level} label={`${review.affected_assets.length} affected`} /> : null}
      </header>

      <div className="lineage-workspace">
        <LineageGraph
          assets={review?.graph_assets ?? []}
          edges={review?.graph_edges ?? []}
          affectedUrns={affected}
          selectedUrn={selectedAsset?.urn ?? null}
          onSelect={onSelectAsset}
        />

        <aside className="asset-inspector" aria-label="Selected asset metadata">
          {selectedAsset ? (
            <>
              <div className="asset-inspector-header">
                <Database aria-hidden="true" />
                <div>
                  <span>{selectedAsset.platform}</span>
                  <h2>{selectedAsset.name}</h2>
                </div>
              </div>
              <p>{selectedAsset.description}</p>

              <dl className="metadata-list">
                <div>
                  <dt>
                    <UserRound aria-hidden="true" /> Owners
                  </dt>
                  <dd>{selectedAsset.owners.join(", ") || "Unassigned"}</dd>
                </div>
                <div>
                  <dt>
                    <ShieldCheck aria-hidden="true" /> Tags
                  </dt>
                  <dd className="tag-list">
                    {selectedAsset.tags.length
                      ? selectedAsset.tags.map((tag) => <span key={tag}>{tag}</span>)
                      : "None"}
                  </dd>
                </div>
                <div>
                  <dt>
                    <CircleAlert aria-hidden="true" /> Quality
                  </dt>
                  <dd>{selectedAsset.quality_signals.join(", ") || "No active assertions"}</dd>
                </div>
              </dl>

              <div className="field-table">
                <div className="field-table-header">
                  <span>Schema field</span>
                  <span>Impact</span>
                </div>
                {selectedAsset.fields.map((field) => {
                  const changed = review?.operations.some((operation) => operation.field === field);
                  return (
                    <div className="field-table-row" key={field}>
                      <code>{field}</code>
                      <span className={changed ? "field-impact" : ""}>{changed ? "Changed" : "Clear"}</span>
                    </div>
                  );
                })}
              </div>
            </>
          ) : (
            <div className="inspector-empty">Select an asset</div>
          )}
        </aside>
      </div>
    </div>
  );
}
