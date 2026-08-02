import { Check, CircleAlert, Database, FlaskConical, Minus } from "lucide-react";

import type { IntegrationStatus, Severity } from "../types";

type BadgeStatus = IntegrationStatus | Severity | "complete" | "skipped" | "failed" | "published";

interface StatusBadgeProps {
  status: BadgeStatus;
  label?: string;
}

const labelByStatus: Record<BadgeStatus, string> = {
  connected: "Connected",
  demo: "Demo data",
  unavailable: "Not connected",
  info: "Info",
  low: "Low",
  medium: "Medium",
  high: "High",
  critical: "Critical",
  complete: "Complete",
  skipped: "Skipped",
  failed: "Failed",
  published: "Published",
};

function BadgeIcon({ status }: { status: BadgeStatus }) {
  if (status === "connected" || status === "complete" || status === "published") {
    return <Check aria-hidden="true" />;
  }
  if (status === "demo") return <FlaskConical aria-hidden="true" />;
  if (status === "unavailable" || status === "skipped") return <Minus aria-hidden="true" />;
  if (["medium", "high", "critical", "failed"].includes(status)) {
    return <CircleAlert aria-hidden="true" />;
  }
  return <Database aria-hidden="true" />;
}

export function StatusBadge({ status, label }: StatusBadgeProps) {
  return (
    <span className={`status-badge status-${status}`}>
      <BadgeIcon status={status} />
      {label ?? labelByStatus[status]}
    </span>
  );
}
