# Design System

## Product Scene

A data platform engineer reviews a risky pull request in a bright office: quiet steel-blue controls, crisp white working surfaces, and amber reserved for evidence that needs attention.

## Color Strategy

Restrained. Neutral surfaces carry the workspace; deep harbor blue is used for active navigation and primary commands. Amber appears only for risk and evidence highlights. Green and red are semantic states, never decoration.

```css
:root {
  --color-bg: oklch(1 0 0);
  --color-surface: oklch(0.975 0.004 230);
  --color-surface-strong: oklch(0.945 0.008 230);
  --color-ink: oklch(0.2 0.018 230);
  --color-muted: oklch(0.46 0.022 230);
  --color-border: oklch(0.88 0.012 230);
  --color-primary: oklch(0.55 0.105 230);
  --color-primary-strong: oklch(0.43 0.105 230);
  --color-primary-soft: oklch(0.93 0.035 230);
  --color-accent: oklch(0.9 0.07 82);
  --color-accent-ink: oklch(0.3 0.065 72);
  --color-success: oklch(0.5 0.115 155);
  --color-warning: oklch(0.67 0.14 72);
  --color-danger: oklch(0.54 0.18 25);
}
```

## Typography

- UI and prose: IBM Plex Sans Variable.
- Code, identifiers, and measurements: IBM Plex Mono Variable.
- Fixed product scale: 12, 13, 14, 16, 18, 22, and 28 pixels.
- Headings use 600 weight; labels use 500; body text uses 400.
- Letter spacing remains zero.

## Layout

- Desktop app shell: 56px top bar, 224px navigation rail, flexible workspace.
- Review workspace: change input on the left; evidence and decision on the right.
- Results use full-width sections separated by rules, not nested cards.
- At widths below 960px the navigation becomes a compact horizontal strip and the review columns stack.
- Stable dimensions are used for icon buttons, status markers, risk meters, and graph nodes.

## Components

- Buttons: 8px radius, 36px default height, icon-first where the command is familiar.
- Inputs and editors: 6px radius, explicit labels, visible focus ring, inline validation.
- Panels: 8px radius only when the content is a genuinely framed tool; otherwise use section rules.
- Badges: compact status labels with an icon or dot and text; color is supplementary.
- Tables and lists: 36px minimum row height, sticky headings when scrolling.
- Lineage graph: semantic asset shapes, stable node dimensions, keyboard-selectable nodes.

## Interaction

- State transitions last 160-220ms and communicate selection, expansion, or completion.
- Review runs expose queued, gathering, analyzing, writing, complete, and failed states.
- Loading uses layout-matched skeletons.
- Errors remain next to the failing integration or input and include a recovery action.
- Reduced-motion mode removes movement while preserving instant state changes.

## Voice

Use direct operational language: "Review change", "3 downstream assets", "Publish evidence". Avoid hype, vague AI claims, and instructional prose inside the primary workflow.
