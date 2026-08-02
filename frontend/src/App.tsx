import { useEffect, useMemo, useState } from "react";
import {
  Activity,
  Boxes,
  Braces,
  ChevronDown,
  GitBranch,
  PlugZap,
  ScanSearch,
} from "lucide-react";

import { api } from "./api";
import { IntegrationsView } from "./components/IntegrationsView";
import { LineageView } from "./components/LineageView";
import { ReviewView } from "./components/ReviewView";
import { RunLogView } from "./components/RunLogView";
import { StatusBadge } from "./components/StatusBadge";
import type { Asset, Integration, ReviewRequest, ReviewResponse, Scenario } from "./types";

type ViewId = "review" | "lineage" | "run" | "integrations";

const navItems = [
  { id: "review" as const, label: "Review", icon: ScanSearch },
  { id: "lineage" as const, label: "Lineage", icon: Boxes },
  { id: "run" as const, label: "Run log", icon: Activity },
  { id: "integrations" as const, label: "Integrations", icon: PlugZap },
];

const emptyDraft: ReviewRequest = { dataset_urn: "", change_sql: "", dialect: "snowflake" };

export default function App() {
  const [activeView, setActiveView] = useState<ViewId>("review");
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [integrations, setIntegrations] = useState<Integration[]>([]);
  const [draft, setDraft] = useState<ReviewRequest>(emptyDraft);
  const [review, setReview] = useState<ReviewResponse | null>(null);
  const [selectedUrn, setSelectedUrn] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [publishing, setPublishing] = useState(false);
  const [publishDestination, setPublishDestination] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function bootstrap() {
      try {
        const [loadedScenarios, loadedIntegrations] = await Promise.all([
          api.scenarios(),
          api.integrations(),
        ]);
        if (cancelled) return;
        setScenarios(loadedScenarios);
        setIntegrations(loadedIntegrations);

        const first = loadedScenarios[0];
        if (!first) throw new Error("No review scenarios are available");
        const initialDraft = {
          dataset_urn: first.dataset_urn,
          change_sql: first.change_sql,
          dialect: first.dialect,
        };
        setDraft(initialDraft);
        const initialReview = await api.createReview(initialDraft);
        if (cancelled) return;
        setReview(initialReview);
        setIntegrations(initialReview.integrations);
        setSelectedUrn(initialReview.target.urn);
      } catch (reason) {
        if (!cancelled) setError(reason instanceof Error ? reason.message : "Unable to load ImpactLint");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    void bootstrap();
    return () => {
      cancelled = true;
    };
  }, []);

  const selectedAsset = useMemo<Asset | null>(
    () => review?.graph_assets.find((asset) => asset.urn === selectedUrn) ?? null,
    [review, selectedUrn],
  );

  async function runReview() {
    setLoading(true);
    setError(null);
    setPublishDestination(null);
    try {
      const result = await api.createReview(draft);
      setReview(result);
      setIntegrations(result.integrations);
      setSelectedUrn(result.target.urn);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Review failed");
    } finally {
      setLoading(false);
    }
  }

  async function publishReview() {
    if (!review) return;
    setPublishing(true);
    setError(null);
    try {
      const result = await api.publishReview(review.id);
      setReview({ ...review, publish_status: "published" });
      setPublishDestination(result.destination);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Publish failed");
    } finally {
      setPublishing(false);
    }
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="product-mark">
          <span>
            <ScanSearch aria-hidden="true" />
          </span>
          <strong>ImpactLint</strong>
        </div>
        <div className="repository-context">
          <GitBranch aria-hidden="true" />
          <span>warehouse-core</span>
          <strong>schema/customer-key</strong>
          <ChevronDown aria-hidden="true" />
        </div>
        <div className="topbar-status">
          <StatusBadge status={integrations.find((item) => item.id === "datahub")?.status ?? "demo"} />
          <span className="avatar" aria-label="Workspace owner">
            JN
          </span>
        </div>
      </header>

      <aside className="nav-rail">
        <nav aria-label="Primary navigation">
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <button
                type="button"
                className={activeView === item.id ? "is-active" : ""}
                aria-current={activeView === item.id ? "page" : undefined}
                key={item.id}
                onClick={() => setActiveView(item.id)}
              >
                <Icon aria-hidden="true" />
                <span>{item.label}</span>
                {item.id === "lineage" && review ? <small>{review.affected_assets.length}</small> : null}
              </button>
            );
          })}
        </nav>

        <div className="rail-runtime">
          <Braces aria-hidden="true" />
          <div>
            <strong>Context engine</strong>
            <span>{review?.compression.status === "measured" ? "Paritok measured" : "Deterministic mode"}</span>
          </div>
        </div>
      </aside>

      <main className="main-content">
        {activeView === "review" ? (
          <ReviewView
            scenarios={scenarios}
            draft={draft}
            onDraftChange={setDraft}
            review={review}
            loading={loading}
            publishing={publishing}
            publishDestination={publishDestination}
            error={error}
            onRun={() => void runReview()}
            onPublish={() => void publishReview()}
          />
        ) : null}
        {activeView === "lineage" ? (
          <LineageView review={review} selectedAsset={selectedAsset} onSelectAsset={setSelectedUrn} />
        ) : null}
        {activeView === "run" ? <RunLogView review={review} /> : null}
        {activeView === "integrations" ? <IntegrationsView integrations={integrations} /> : null}
      </main>
    </div>
  );
}
