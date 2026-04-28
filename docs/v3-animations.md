# V3 Frontend — Animation Specification

All motion uses **Framer Motion**. Animations must **never block** interaction (no mandatory full-screen locks except explicit submit disabling on the primary button).

---

## Global principles

| Topic | Rule |
|--------|------|
| **Feel** | Snappy and purposeful — not slow, not decorative. |
| **Durations** | **200–300ms** micro-interactions; **400–500ms** route-level transitions. |
| **Easing** | Default curve **`cubic-bezier(0.25, 0.1, 0.25, 1)`** — smooth deceleration. In Framer Motion: `[0.25, 0.1, 0.25, 1]`. |
| **Interaction** | Never delay clicks or focus; avoid `pointer-events: none` on large containers except during explicit submit. |
| **Reduced motion** | If `prefers-reduced-motion: reduce`, **disable** non-essential animations (set reduced or zero duration / opacity-only / no layout animations). |

Implement a small `useReducedMotion()` helper (Framer’s `useReducedMotion` hook) and branch transitions.

---

## Specified behaviors

### 1. Page transitions

When the main content area switches routes:

- **Enter:** `opacity: 0 → 1`, `y: 10 → 0`.
- **Duration:** **400ms**.
- **Easing:** default cubic-bezier above.

Wrap outlet in `AnimatePresence` + `motion.div` with `key={location.pathname}`.

### 2. Card reveal (compliance findings)

Staggered list entrance:

- Each **FindingCard:** `opacity: 0 → 1`, `y: 20 → 0`.
- **Stagger delay:** **60ms** between siblings.
- **Duration:** **350ms**.

### 3. Severity badges

- **CRITICAL** and **HIGH** (violation severity): subtle **pulse** — opacity `0.7 ↔ 1`, scale `0.97 ↔ 1`, **2s** duration, `repeat: Infinity`, `ease: "easeInOut"`.
- **LOW**, **MEDIUM**, **compliant** badges: **no** repeating animation.

Respect reduced motion: static badge only.

### 4. Loading state (analysis in flight)

Pipeline can run **20–190s**.

- **Skeleton:** shimmer on placeholder cards / table rows (CSS gradient animation or Framer opacity sweep); **do not** shimmer the entire viewport aggressively.
- **Progress:** indeterminate — animated **dots** or thin **pulsing bar** under the submit area.
- **Copy:** static reassurance text, e.g. *“Complex runs often take 1–3 minutes.”* (adjust if compliance vs violation copy differs slightly).

### 5. Expand / collapse (finding cards)

- Use **`AnimatePresence`** for unmount.
- **Height:** prefer **`layout`** animation or measured height with Framer — avoid jarring jumps; target **~200ms** for content fade-in after height starts opening.
- **Content fade:** **200ms** opacity on inner body.

If reduced motion: instant expand/collapse or simple opacity only.

### 6. Chart mount

- **Bar charts:** bars animate **height 0 → value**, **stagger 30ms**, **600ms** duration.
- **Donut / pie:** segment or stroke **draw** clockwise, **800ms** duration.

Reduced motion: show final state immediately.

### 7. Hover effects

- **Cards:** border color transition **`slate-800 → slate-700`**, **150ms** `transition-colors`.
- **Primary buttons:** optional **`scale: 1.02`** on hover (100–150ms); must not break layout.

### 8. Toast notifications

- **Enter:** from top-right: `x: 100 → 0`, `opacity: 0 → 1`, **250ms**.
- **Exit:** fade out, **200ms**.
- **Auto-dismiss:** **4s** after enter completes.

### 9. Tab / mode toggle (Violation | Compliance)

- Sliding **indicator** under active segment (background pill).
- Use **spring** for indicator position (`type: "spring", stiffness: 400, damping: 30` — tune in implementation).
- Active label text color transitions **150ms**.

### 10. Submit button

- **Tap:** `scale: 1 → 0.97 → 1` over **~150ms** total.
- **Ripple:** optional CSS or motion ripple — keep subtle; skip if it clashes with shadcn button styles.

---

## Testing checklist

- [ ] Toggle `prefers-reduced-motion` in OS and verify no stagger/pulse.
- [ ] Run a **long** compliance job — skeletons remain stable, no layout thrash.
- [ ] Rapidly switch modes — no overlapping `AnimatePresence` glitches.

---

## References

- [v3-design-system.md](v3-design-system.md)
- [v3-component-tree.md](v3-component-tree.md) (`PageTransition.jsx`, `FindingCard.jsx`, `SubmitButton.jsx`)
