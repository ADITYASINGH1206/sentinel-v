# VeriFrame motion policy

Motion should explain change, never decorate data. Tokens live in `web/src/design/motion.ts`.

| Token | Value | Use |
|---|---|---|
| `dur.fast` | 140 ms | menus, dialogs, toggles |
| `dur.base` | 200 ms | list items, small reveals |
| `dur.page` | 240 ms | route transitions (console) |
| `dur.slow` | 320 ms | section reveals on the home page |
| `ease.standard` | cubic-bezier(0.2, 0, 0, 1) | default |
| `ease.emphasized` | cubic-bezier(0.3, 0, 0, 1) | count-ups, verdict pulse |

## Catalogue

| Where | Animation |
|---|---|
| Console route change | fade + 8 px rise (`AnimatePresence mode="wait"`) |
| Sidebar collapse | width 240 ↔ 72 px, active item indicator slides (`layoutId`) |
| Marketing nav | background blurs in on scroll; active section underline slides |
| Home hero | CSS scan line + patch cells revealed row by row; loop pauses off-screen |
| How it works | connector grows left→right, steps stagger in |
| Feature cards | lift 1 px on hover; mini illustrations animate on hover only |
| Base-rate calculator | numbers count up (≤ 350 ms) when inputs change |
| Verdict card | one-time band chip pulse per analysis |
| Stage progress | bar fill + checkmark draw, driven only by real progress |
| Clip timeline | area draws in once (Recharts), disabled under reduced motion |
| Verify checklist | icon morphs when each real check completes |
| Lists | first 12 rows stagger (25–30 ms) on first load only |

## Reduced motion

`Settings → Motion` offers System / Reduce / Full. Reduce (or the OS setting under System) sets
`<MotionConfig reducedMotion="always">` and `html[data-motion="reduce"]`, which stops CSS loops
(scan, shimmer, ping, drift), skips count-ups and disables chart animations.
