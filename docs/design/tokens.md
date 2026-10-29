# VeriFrame design tokens

Defined in `web/src/index.css` as RGB channels (so Tailwind opacity modifiers like `bg-accent/10` work) and mapped in `web/tailwind.config.js`.

| Token | Light | Dark | Use |
|---|---|---|---|
| `--bg` | `#F4EFE6` | `#14110E` | page |
| `--surface` | `#FFFBF4` | `#1E1A16` | cards |
| `--surface-2` | `#EBE4D6` | `#282319` | wells, table headers |
| `--border` | `#D8CFBE` | `#3E362E` | dividers |
| `--text` | `#16130F` | `#F4EFE6` | body |
| `--muted` | `#635A4E` | `#B2A898` | secondary text |
| `--accent` | `#A6400E` | `#F2994F` | actions, links, focus ring |
| `--violet` | `#4F56BE` | `#A5ACFF` | marketing gradients only |
| `--band-authentic` | `#1E6844` | `#68CD96` | with ShieldCheck icon + text |
| `--band-review` | `#8A5A00` | `#ECBE50` | with Eye icon + text |
| `--band-manipulated` | `#B2221E` | `#FF7D70` | with ShieldAlert icon + text |
| `--band-inconclusive` | `#635A4E` | `#B2A898` | with HelpCircle icon + text |

Bands always combine colour, icon and words. Evidence heat uses an approximation of the
perceptually uniform, colour-blind-safe *magma* map with the same 0.15 alpha floor as
`sv_engine/evidence.py`.

Palette direction: warm paper and ink with a burnt-orange accent (references: the Decision Archaeologist paper palette and Sarvam's sunset-gradient hero). Primary buttons are ink pills; the accent is for links, focus and highlights.

Typography: Fraunces Variable (display: h1/h2), Inter Variable (UI) and JetBrains Mono (ids, hashes, scores), both self-hosted via
`@fontsource`.

## Contrast (WCAG 2.x ratios, computed from the hex values above; the band-on-tint rows below are from the previous palette and were not re-measured, bands on bg/surface are 5.2–5.9 light, 7.5–10.8 dark)

| Pair | Light | Dark |
|---|---|---|
| text on bg | 16.17 | 16.43 |
| muted on bg | 5.91 | 8.02 |
| muted on surface-2 | 5.35 | 6.64 |
| accent on bg | 5.4 | 8.46 |
| accent-contrast on accent | 6.06 | 8.30 |
| band-authentic on its 10% tint | 4.99 | 7.62 |
| band-review on its 10% tint | 4.82 | 8.53 |
| band-manipulated on its 10% tint | 5.58 | 6.39 |

All pairs meet AA (≥ 4.5:1) for normal text. Re-run an automated check (e.g. axe) when tokens change.
