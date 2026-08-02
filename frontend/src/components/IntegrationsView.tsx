import { Braces, CircleHelp, Database, ExternalLink, PlugZap } from "lucide-react";

import type { Integration } from "../types";
import { StatusBadge } from "./StatusBadge";

export function IntegrationsView({ integrations }: { integrations: Integration[] }) {
  return (
    <div className="view-stack integrations-view">
      <header className="view-header">
        <div>
          <p className="eyebrow">Runtime connections</p>
          <h1>Integrations</h1>
        </div>
      </header>

      <section className="integration-table" aria-label="Integration status">
        <div className="integration-row integration-header">
          <span>Provider</span>
          <span>Status</span>
          <span>Runtime detail</span>
          <span>Surface</span>
        </div>
        {integrations.map((integration) => {
          const Icon = integration.id === "datahub" ? Database : Braces;
          return (
            <div className="integration-row" key={integration.id}>
              <div className="integration-name">
                <Icon aria-hidden="true" />
                <strong>{integration.label}</strong>
              </div>
              <StatusBadge status={integration.status} />
              <span>{integration.detail}</span>
              <code>{integration.id === "datahub" ? "MCP" : "Hosted GPU"}</code>
            </div>
          );
        })}
      </section>

      <section className="runtime-config">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Environment contract</p>
            <h2>Live runtime keys</h2>
          </div>
          <PlugZap aria-hidden="true" />
        </div>
        <div className="config-list">
          <div>
            <code>IMPACTLINT_MODE</code>
            <span>fixture | datahub</span>
          </div>
          <div>
            <code>DATAHUB_MCP_URL</code>
            <span>http://localhost:8001/mcp</span>
          </div>
          <div>
            <code>PARITOK_API_URL</code>
            <span>https://www.paritok.com/api</span>
          </div>
        </div>
        <div className="reference-links">
          <a href="https://github.com/acryldata/mcp-server-datahub" target="_blank" rel="noreferrer">
            <CircleHelp aria-hidden="true" /> DataHub MCP reference <ExternalLink aria-hidden="true" />
          </a>
          <a href="https://github.com/Paritok-official/paritok-4b-v1" target="_blank" rel="noreferrer">
            <CircleHelp aria-hidden="true" /> Paritok reference <ExternalLink aria-hidden="true" />
          </a>
        </div>
      </section>
    </div>
  );
}
