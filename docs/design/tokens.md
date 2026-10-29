# VeriFrame design tokens

Defined in `web/src/index.css` as RGB channels (so Tailwind opacity modifiers like `bg-accent/10` work) and mapped in `web/tailwind.config.js`.

| Token | Light | Dark | Use |
|---|---|---|---|
| `--bg` | `#F7F9FB` | `#070B12` | page |
| `--surface` | `#FFFFFF` | `#0D141F` | cards |
| `--surface-2` | `#F1F4F8` | `#121B29` | wells, table headers |
| `--border` | `#E3E8EF` | `#1E2A3B` | dividers |
| `--text` | `#0B1220` | `#E7EDF5` | body |
| `--muted` | `#566173` | `#93A1B5` | secondary text |
| `--accent` | `#0B7A85` | `#2CC7C0` | actions, links, focus ring |
| `--violet` | `#6D5BD0` | `#9B8CFF` | marketing gradients only |
| `--band-authentic` | `#21744A` | `#5CC992` | with ShieldCheck icon + text |
| `--band-review` | `#8F5F00` | `#E9B949` | with Eye icon + text |
| `--band-manipulated` | `#B42318` | `#FF7A6E` | with ShieldAlert icon + text |
| `--band-inconclusive` | `#566173` | `#93A1B5` | with HelpCircle icon + text |

Bands always combine colour, icon and words. Evidence heat uses an approximation of the
perceptually uniform, colour-blind-safe *magma* map with the same 0.15 alpha floor as
`sv_engine/evidence.py`.

Typography: Inter Variable (UI) and JetBrains Mono (ids, hashes, scores), both self-hosted via
`@fontsource`.

## Contrast (WCAG 2.x ratios, computed from the hex values above)

| Pair | Light | Dark |
|---|---|---|
| text on bg | 17.74 | 16.73 |
| muted on bg | 5.93 | 7.51 |
| muted on surface-2 | 5.68 | 6.59 |
| accent on bg | 4.81 | 9.42 |
| accent-contrast on accent (primary button) | 5.08 | 8.08 |
| band-authentic on its 10% tint | 4.99 | 7.62 |
| band-review on its 10% tint | 4.82 | 8.53 |
| band-manipulated on its 10% tint | 5.58 | 6.39 |

All pairs meet AA (≥ 4.5:1) for normal text. Re-run an automated check (e.g. axe) when tokens change.
