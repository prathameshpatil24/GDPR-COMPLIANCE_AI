# V3 Frontend — Component Architecture

Planned source layout for the **Vite + React** app (e.g. under repository root `frontend/`). Paths below are relative to that app’s `src/`.

---

## Directory tree

```
src/
├── main.jsx                    # Entry: createRoot, StrictMode, router
├── App.jsx                     # Shell: theme provider, sidebar layout, outlet
├── api/
│   └── client.js               # Fetch/axios wrapper, base URL, errors
├── hooks/
│   ├── useAnalyze.js           # POST violation analyze; maps errors
│   ├── useAssess.js            # POST compliance analyze
│   ├── useHistory.js           # Load analysis list + detail
│   └── useStats.js             # Load aggregate + series stats
├── components/
│   ├── layout/
│   │   ├── Sidebar.jsx
│   │   ├── Header.jsx
│   │   └── PageTransition.jsx
│   ├── analyze/
│   │   ├── ModeToggle.jsx
│   │   ├── ScenarioInput.jsx
│   │   ├── SubmitButton.jsx
│   │   └── LoadingState.jsx
│   ├── results/
│   │   ├── ViolationReport.jsx
│   │   ├── ComplianceReport.jsx
│   │   ├── SeverityBadge.jsx
│   │   ├── StatusBadge.jsx
│   │   ├── FindingCard.jsx
│   │   ├── ArticleTag.jsx
│   │   ├── ConfidenceBar.jsx
│   │   ├── RecommendationList.jsx
│   │   ├── CitationList.jsx
│   │   ├── RetrievalGapNote.jsx
│   │   ├── RiskOverviewChart.jsx
│   │   ├── ConfidenceChart.jsx
│   │   └── DataFlowDiagram.jsx
│   ├── history/
│   │   ├── HistoryTable.jsx
│   │   ├── HistoryFilters.jsx
│   │   └── HistoryDetail.jsx
│   ├── stats/
│   │   ├── StatCard.jsx
│   │   ├── CostChart.jsx
│   │   ├── LatencyChart.jsx
│   │   ├── QueryChart.jsx
│   │   └── SeverityChart.jsx
│   ├── settings/
│   │   ├── ApiKeyInput.jsx
│   │   └── ThemeToggle.jsx
│   └── shared/
│       ├── Card.jsx
│       ├── Badge.jsx
│       ├── Toast.jsx
│       ├── Skeleton.jsx
│       └── EmptyState.jsx
├── pages/
│   ├── AnalyzePage.jsx
│   ├── HistoryPage.jsx
│   ├── StatsPage.jsx
│   └── SettingsPage.jsx
├── styles/
│   └── globals.css             # Tailwind, fonts, CSS variables
└── lib/
    ├── theme.js
    ├── formatters.js
    └── constants.js
```

---

## Root files

### `main.jsx`

**Responsibility:** Bootstrap React, mount `App`, attach **React Router** (or chosen router), import `globals.css`.

**Props:** none.

### `App.jsx`

**Responsibility:** Wrap children with **theme** context (dark default), render **Sidebar** + **Header** + routed **PageTransition** + outlet.

**Props:** none.

---

## `api/client.js`

**Responsibility:** Central HTTP client: base URL (`''` when using Vite proxy), JSON serialization, timeout handling, mapping HTTP errors to app error type.

**Exports:** functions or configured client instance — no React props.

---

## Hooks

### `useAnalyze.js`

**Responsibility:** Mutation for `POST /api/v1/analyze/violation`; exposes `mutate`, `isPending`, `data`, `error`, `reset`.

**Props:** N/A (hook). **Options:** `{ onSuccess, onError }`.

### `useAssess.js`

**Responsibility:** Mutation for `POST /api/v1/analyze/compliance`.

**Props:** N/A. **Options:** `{ onSuccess, onError }`.

### `useHistory.js`

**Responsibility:** Query list of analyses (from API or composed calls) + lazy-load detail by id.

**Returns:** `{ rows, isLoading, error, refetch, getDetail(id) }`.

### `useStats.js`

**Responsibility:** Query aggregate stats and optional time-series for charts.

**Returns:** `{ summary, series, isLoading, error, refetch }`.

---

## Layout components

### `Sidebar.jsx`

**Responsibility:** Left nav links: Analyze, History, Stats, Settings; highlight active route.

**Props:**

| Prop | Type | Description |
|------|------|-------------|
| `className` | `string?` | Optional layout class. |

### `Header.jsx`

**Responsibility:** Top bar: product name/logo, optional connection/health indicator, slot for **ThemeToggle**.

**Props:**

| Prop | Type | Description |
|------|------|-------------|
| `health` | `{ ok: boolean, version?: string }?` | From `GET /health`. |

### `PageTransition.jsx`

**Responsibility:** Framer Motion wrapper for route children (fade + slide).

**Props:**

| Prop | Type | Description |
|------|------|-------------|
| `children` | `ReactNode` | Page content. |
| `routeKey` | `string` | e.g. pathname for `AnimatePresence`. |

---

## Analyze components

### `ModeToggle.jsx`

**Responsibility:** Two-segment control: `violation` | `compliance`; animated indicator.

**Props:**

| Prop | Type | Description |
|------|------|-------------|
| `value` | `'violation' \| 'compliance'` | Controlled mode. |
| `onChange` | `(v) => void` | Change handler. |
| `disabled` | `boolean?` | While request in flight. |

### `ScenarioInput.jsx`

**Responsibility:** Large textarea, placeholder by mode, optional character count, validation hint.

**Props:**

| Prop | Type | Description |
|------|------|-------------|
| `value` | `string` | Controlled text. |
| `onChange` | `(s: string) => void` | |
| `mode` | `'violation' \| 'compliance'` | Selects placeholder copy. |
| `maxLength` | `number?` | Violation 8000; compliance text up to backend limit. |
| `disabled` | `boolean?` | |

### `SubmitButton.jsx`

**Responsibility:** Primary submit with loading state and tap animation.

**Props:**

| Prop | Type | Description |
|------|------|-------------|
| `onClick` | `() => void` | |
| `loading` | `boolean` | |
| `label` | `string` | e.g. “Analyze”. |
| `disabled` | `boolean?` | |

### `LoadingState.jsx`

**Responsibility:** Skeleton blocks + indeterminate progress + time estimate copy.

**Props:**

| Prop | Type | Description |
|------|------|-------------|
| `mode` | `'violation' \| 'compliance'` | Optional copy tweak. |

---

## Results components

### `ViolationReport.jsx`

**Responsibility:** Render full `AnalysisReport`-shaped JSON: summary, entities/topics (optional collapse), violations table, recommendations, citations, similar cases, unsupported notes, disclaimer.

**Props:**

| Prop | Type | Description |
|------|------|-------------|
| `data` | `object` | `result` from API (`AnalysisReport` fields). |

### `ComplianceReport.jsx`

**Responsibility:** Render `ComplianceAssessment`: summary, overall risk, findings list, data map summary, recommendations if present in payload.

**Props:**

| Prop | Type | Description |
|------|------|-------------|
| `data` | `object` | `ComplianceAssessment` shape. |

### `SeverityBadge.jsx`

**Responsibility:** Violation `severity_level` pill; pulse for high/critical per animation spec.

**Props:**

| Prop | Type | Description |
|------|------|-------------|
| `level` | `string` | `low` / `medium` / `high` / `critical` / `unknown`. |
| `rationale` | `string?` | Tooltip or secondary line. |

### `StatusBadge.jsx`

**Responsibility:** Map `ComplianceStatus` to styled pill.

**Props:**

| Prop | Type | Description |
|------|------|-------------|
| `status` | `string` | `compliant` / `at_risk` / `non_compliant` / `insufficient_info`. |

### `FindingCard.jsx`

**Responsibility:** Expandable card for one `Finding`: area, status, articles, description, remediation, technical guidance.

**Props:**

| Prop | Type | Description |
|------|------|-------------|
| `finding` | `object` | One `Finding` model. |
| `defaultOpen` | `boolean?` | |

### `ArticleTag.jsx`

**Responsibility:** Monospace pill for one article string.

**Props:**

| Prop | Type | Description |
|------|------|-------------|
| `label` | `string` | e.g. `Art. 6 GDPR`. |

### `ConfidenceBar.jsx`

**Responsibility:** Horizontal bar **0–1** for violation confidence.

**Props:**

| Prop | Type | Description |
|------|------|-------------|
| `value` | `number` | 0–1. |
| `showLabel` | `boolean?` | |

### `RecommendationList.jsx`

**Responsibility:** Numbered list from string array.

**Props:**

| Prop | Type | Description |
|------|------|-------------|
| `items` | `string[]` | |

### `CitationList.jsx`

**Responsibility:** List of citation strings or links if URLs parsed.

**Props:**

| Prop | Type | Description |
|------|------|-------------|
| `items` | `string[]` | |

### `RetrievalGapNote.jsx`

**Responsibility:** Info callout for `unsupported_notes` items.

**Props:**

| Prop | Type | Description |
|------|------|-------------|
| `notes` | `string[]` | |

### `RiskOverviewChart.jsx`

**Responsibility:** Donut or bar of finding status counts from compliance `findings[]`.

**Props:**

| Prop | Type | Description |
|------|------|-------------|
| `findings` | `Array<{ status: string }>` | |

### `ConfidenceChart.jsx`

**Responsibility:** Bar chart of violation confidences by article label.

**Props:**

| Prop | Type | Description |
|------|------|-------------|
| `violations` | `Array<{ article_reference: string, confidence: number }>` | |

### `DataFlowDiagram.jsx`

**Responsibility:** Visualize `data_map.data_flows` (source → destination, border flag).

**Props:**

| Prop | Type | Description |
|------|------|-------------|
| `flows` | `object[]` | `DataFlow` shapes. |

---

## History components

### `HistoryTable.jsx`

**Responsibility:** Sortable table; row click selects record for detail.

**Props:**

| Prop | Type | Description |
|------|------|-------------|
| `rows` | `HistoryRow[]` | Normalized list (id, timestamp, snippet, mode, severity, cost, latency). |
| `onRowClick` | `(id: string) => void` | |
| `selectedId` | `string?` | |

### `HistoryFilters.jsx`

**Responsibility:** Mode and severity filters + search input.

**Props:**

| Prop | Type | Description |
|------|------|-------------|
| `mode` | `string?` | filter value. |
| `severity` | `string?` | |
| `search` | `string` | |
| `onModeChange` | `(v) => void` | |
| `onSeverityChange` | `(v) => void` | |
| `onSearchChange` | `(v) => void` | |

### `HistoryDetail.jsx`

**Responsibility:** Full report for selected id; delegates to ViolationReport or ComplianceReport.

**Props:**

| Prop | Type | Description |
|------|------|-------------|
| `analysis` | `{ mode, result, scenario_text, created_at }?` | |

---

## Stats components

### `StatCard.jsx`

**Responsibility:** Single KPI tile.

**Props:**

| Prop | Type | Description |
|------|------|-------------|
| `label` | `string` | |
| `value` | `string \| number` | formatted |
| `hint` | `string?` | |

### `CostChart.jsx` / `LatencyChart.jsx` / `QueryChart.jsx` / `SeverityChart.jsx`

**Responsibility:** Recharts wrappers with shared theming; consume series data from `useStats`.

**Props (each):**

| Prop | Type | Description |
|------|------|-------------|
| `data` | `array` | Chart-specific points. |
| `loading` | `boolean?` | |

---

## Settings components

### `ApiKeyInput.jsx`

**Responsibility:** Masked input; may be disabled with helper text if server-only key.

**Props:**

| Prop | Type | Description |
|------|------|-------------|
| `value` | `string` | |
| `onChange` | `(s: string) => void` | |
| `disabled` | `boolean?` | |
| `helperText` | `string?` | |

### `ThemeToggle.jsx`

**Responsibility:** Dark/light toggle; persists preference (`localStorage`).

**Props:** none or optional `className`.

---

## Shared components

### `Card.jsx`

**Responsibility:** Surface with design-system border/shadow rules.

**Props:**

| Prop | Type | Description |
|------|------|-------------|
| `children` | `ReactNode` | |
| `className` | `string?` | |

### `Badge.jsx`

**Responsibility:** Generic pill; variants map to design tokens.

**Props:**

| Prop | Type | Description |
|------|------|-------------|
| `children` | `ReactNode` | |
| `variant` | `string` | semantic variant name. |

### `Toast.jsx` / toast system

**Responsibility:** Slide-in notifications; provider + hook.

**Props:** implementation-specific (often context).

### `Skeleton.jsx`

**Responsibility:** Shimmer placeholder.

**Props:**

| Prop | Type | Description |
|------|------|-------------|
| `className` | `string?` | dimensions. |

### `EmptyState.jsx`

**Responsibility:** Illustration/message when no data.

**Props:**

| Prop | Type | Description |
|------|------|-------------|
| `title` | `string` | |
| `description` | `string?` | |
| `action` | `ReactNode?` | |

---

## Pages

### `AnalyzePage.jsx`

**Responsibility:** Compose ModeToggle, ScenarioInput, SubmitButton, LoadingState, result reports + charts.

**Props:** none (route).

### `HistoryPage.jsx` / `StatsPage.jsx` / `SettingsPage.jsx`

**Responsibility:** Page-level data loading and layout for each section.

**Props:** none.

---

## `lib` modules

| File | Responsibility |
|------|----------------|
| `theme.js` | Dark/light class names, chart color constants. |
| `formatters.js` | `formatEUR`, `formatMs`, `formatDate`, truncate scenario. |
| `constants.js` | API paths, placeholders, severity/status enums for UI. |

---

## References

- [v3-api-integration.md](v3-api-integration.md)
- [v3-design-system.md](v3-design-system.md)
