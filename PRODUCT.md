# Product

## Register

product

## Users

Data platform, analytics, and ML engineers reviewing schema and pipeline changes before merge. They work under time pressure, need to understand downstream impact quickly, and cannot afford to manually assemble lineage, ownership, governance, and quality context from several tools.

## Product Purpose

ImpactLint reviews proposed data changes against a live DataHub context graph. It identifies affected assets and owners, explains risk, generates migration steps and regression tests, and records the review back into DataHub. Paritok reduces the metadata context sent to the reasoning model and provides measurable token and cost savings.

Success means an engineer can move from a proposed SQL change to a defensible, shareable review in under two minutes, with every conclusion traceable to DataHub metadata.

## Brand Personality

Exact, calm, and operational. The product should feel like a trusted review instrument: confident without theatrics, technical without becoming cryptic, and concise without hiding evidence.

## Anti-references

- Generic chat interfaces that hide the workflow behind an empty prompt.
- Marketing dashboards with oversized metrics, decorative gradients, and excessive cards.
- Security tools that use alarmist red everywhere or imply certainty without evidence.
- Dense observability screens that require hovering every control to understand the current state.

## Design Principles

1. Evidence before recommendation: every risk links back to the metadata that caused it.
2. One review, one path: proposed change, affected graph, decision, and generated artifacts remain in a predictable reading order.
3. Progressive depth: show the decision first, then let experts inspect lineage and individual signals.
4. Honest automation: distinguish deterministic analysis, model inference, and unavailable integrations.
5. Demo is a real workflow: the sample environment behaves like the connected product instead of being a static mockup.

## Accessibility & Inclusion

Target WCAG 2.2 AA. All workflows must be keyboard operable, focus must remain visible, status cannot rely on color alone, motion must respect reduced-motion preferences, and compact data views must remain readable at 200% zoom.
