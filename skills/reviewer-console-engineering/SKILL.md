---
name: reviewer-console-engineering
description: Guides development of the React Reviewer Console, EvidencePlayer synchronized canvas overlays, Recharts timelines, keyboard accessibility, and copy compliance.
---

# Reviewer Console Engineering Skill

This skill guides the frontend engineering of the SENTINEL-V Reviewer Console SPA (`web/`), adhering to SPEC §14.

## UI Copy Principles (SPEC §14.13)

### Forbidden Strings (Enforced by `web/src/copy/forbidden.ts`)
- Never use bare **"FAKE"** or **"REAL"** stamps.
- Never use **"100%"**, **"guaranteed"**, or **"AI-certified"**.
- Never use **"proof"** except inside the exact mandatory disclaimer:
  > *"Screening aid — not proof. Human review required for consequential action."*

### Standard Copy Terms
- `likely_authentic`: **"Likely authentic"** (with `ShieldCheck` icon)
- `needs_review`: **"Needs review"** (with `Eye` icon)
- `likely_manipulated`: **"Likely manipulated"** (with `ShieldAlert` icon)
- `inconclusive`: **"Inconclusive"** (with `HelpCircle` icon)

---

## EvidencePlayer Implementation (`EvidencePlayer.tsx`)

The video player synchronizes the underlying HTML5 `<video>` element with an HTML5 `<canvas>` rendering warped patch heat-maps:

```typescript
// Use requestVideoFrameCallback for frame-accurate canvas drawing
const onFrame = (now: DOMHighResTimeStamp, metadata: VideoFrameMetadata) => {
    drawHeatmapForTimestamp(metadata.mediaTime);
    videoRef.current?.requestVideoFrameCallback(onFrame);
};
```

### Keyboard Shortcuts
| Key | Action |
|---|---|
| `Space` | Play / Pause video |
| `Left` / `Right` | Step backward / forward one frame |
| `P` | Jump immediately to peak suspicious clip |
| `H` | Toggle heat-map overlay visibility |
| `1` | Select decision: Authentic |
| `2` | Select decision: Manipulated |
| `3` | Select decision: Cannot tell |
| `R` | Focus reason codes checklist |
| `Enter` | Submit review and automatically claim next queue item |
| `S` | Skip current item |

---

## Accessibility & Performance Standards
- **WCAG 2.2 AA Compliance:** Color must never be the sole carrier of meaning. Contrast ratio $\ge 4.5:1$.
- **Bundle Budget:** Initial JS bundle $\le 250$ KB gzipped.
- **Automated Verification:** Run Vitest and Playwright with Axe checks:
  ```bash
  cd web && npm test
  ```
