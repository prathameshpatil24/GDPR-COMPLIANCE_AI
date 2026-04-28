# V3 Frontend — Design System

Specification for the GDPR AI v3 SPA. **Dark mode is the default.** All tokens are expressed in Tailwind-friendly terms for implementation in `globals.css` and component classes.

---

## Design philosophy

- **Professional and modern** — credible for **enterprise stakeholders** (e.g. compliance reviews) and **founders** shipping fast.
- **Dark-first** — default theme is dark; light mode is a supported alternate.
- **Reference aesthetics** — calm density and precision inspired by **Linear**, **Vercel**, and **Stripe** dashboards: restrained color, clear hierarchy, minimal chrome.
- **Motion** — subtle and purposeful (see [v3-animations.md](v3-animations.md)); never decorative or sluggish.
- **Tone** — every surface should read as **production-ready** and **competent**, not experimental.

---

## Color palette

Map semantic roles to Tailwind classes. Use CSS variables if needed for Recharts; values should match these roles.

| Role | Light mode | Dark mode (default) |
|------|------------|---------------------|
| Page background | `white` | `slate-950` |
| Card / surface | `slate-50` | `slate-900` |
| Card border | `slate-200` | `slate-800` |
| Elevated surface | `white` | `slate-800` |
| Primary text | `slate-900` | `slate-50` |
| Secondary text | `slate-500` | `slate-400` |
| Muted text | `slate-400` | `slate-500` |
| Accent / interactive | `indigo-600` | `indigo-500` |
| Accent hover | `indigo-700` | `indigo-400` |
| Accent subtle bg | `indigo-50` | `indigo-500/10` |
| Compliant | `emerald-600` text; bg `emerald-500/10` | `emerald-500` text; bg `emerald-500/10` |
| At risk | `amber-600` | `amber-500` + `amber-500/10` bg |
| Non-compliant | `rose-600` | `rose-500` + `rose-500/10` bg |
| Critical (compliance emphasis) | `rose-700` | `rose-600` + `rose-600/15` bg |
| Insufficient info | `slate-500` | `slate-500` + `slate-500/10` bg |
| Severity LOW | `emerald-500` | `emerald-400` |
| Severity MEDIUM | `amber-500` | `amber-500` |
| Severity HIGH | `orange-600` | `orange-500` |
| Severity CRITICAL | `rose-600` | `rose-600` |

**Note:** “Critical severity” appears in both violation (`severity_level`) and compliance (`overall_risk_level`) contexts; use the same critical styling for maximum urgency.

---

## Typography

| Use | Font | Notes |
|-----|------|--------|
| All UI copy (headings, body, labels, buttons) | **Inter** | Load via `@fontsource/inter` or Google Fonts; set as `font-sans`. |
| Article refs, confidence, IDs, code | **Geist Mono** | `font-mono`; e.g. `Art. 6(1)(a) GDPR`, `0.94`, UUIDs. |

**Scale**

- Body: **14px** (`text-sm` with default Tailwind scale — verify `text-sm` = 14px in config).
- Secondary / muted: **13px** (`text-[13px]` or closest token).
- **h1**: 24px, `font-semibold`, line-height **1.3**.
- **h2**: 20px, `font-semibold`, line-height **1.3**.
- **h3**: 16px, `font-semibold`, line-height **1.3**.
- Body line-height: **1.6**.

---

## Spacing and layout

| Rule | Value |
|------|--------|
| Max content width | `max-w-6xl` (1152px), centered (`mx-auto`). |
| Page padding | `px-6 py-8`. |
| Card padding | `p-6`. |
| Card radius | `rounded-xl`. |
| Card elevation — dark | **No shadow**; use `border border-slate-800`. |
| Card elevation — light | `shadow-sm` + border as needed. |
| Section vertical rhythm | `space-y-6`. |
| Component vertical rhythm | `space-y-4`. |

---

## Status badges

**Shape:** `rounded-full px-3 py-1 text-xs font-medium`.

Use a **subtle tinted background** with matching foreground:

| Variant | Classes (dark-first) |
|---------|----------------------|
| Compliant | `bg-emerald-500/10 text-emerald-500` |
| At risk | `bg-amber-500/10 text-amber-500` |
| Non-compliant | `bg-rose-500/10 text-rose-500` |
| Insufficient info | `bg-slate-500/10 text-slate-500` |
| Severity LOW | `bg-emerald-500/10 text-emerald-400` |
| Severity MEDIUM | `bg-amber-500/10 text-amber-500` |
| Severity HIGH | `bg-orange-500/10 text-orange-500` |
| Severity CRITICAL | `bg-rose-500/15 text-rose-500` (+ optional pulse; see animations doc) |

**Compliance status** maps from API enum: `compliant`, `at_risk`, `non_compliant`, `insufficient_info`.

**Violation severity** maps from: `low`, `medium`, `high`, `critical`, `unknown` (treat `unknown` with muted styling).

---

## Buttons

| Variant | Classes (dark mode baseline) |
|---------|------------------------------|
| Primary | `bg-indigo-500 hover:bg-indigo-400 text-white rounded-lg px-4 py-2 font-medium transition-colors` |
| Secondary | `bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 rounded-lg px-4 py-2` |
| Ghost | `hover:bg-slate-800 text-slate-400 hover:text-slate-200 rounded-lg px-4 py-2` |

Light mode: adjust backgrounds to `slate-100` / `slate-200` borders as needed while keeping indigo primary.

---

## Charts (Recharts)

- **Plot background:** transparent.
- **Grid:** `stroke-slate-800` at low opacity (e.g. `opacity-20`).
- **Axis tick labels:** `fill-slate-400`, **12px**.
- **Tooltip container:** `bg-slate-800 border border-slate-700 rounded-lg shadow-lg`; text `slate-100` / `slate-400`.
- **Primary series:** `indigo-500`.
- **Secondary series:** `slate-400`.
- **Status breakdowns:** emerald / amber / rose consistent with badges.

Ensure chart text uses **Inter** where possible; numeric annotations may use **Geist Mono** for alignment with the rest of the UI.

---

## Accessibility

- Maintain **WCAG AA** contrast for text on surfaces in both themes.
- Focus rings visible on interactive elements (`ring-2 ring-indigo-500 ring-offset-2 ring-offset-slate-950` in dark).
- Chart data should have **non-color cues** where feasible (labels, patterns) for status categories.

---

## References

- [v3-overview.md](v3-overview.md)
- [v3-animations.md](v3-animations.md)
