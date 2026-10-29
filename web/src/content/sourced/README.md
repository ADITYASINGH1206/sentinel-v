# Sourced numbers

This folder is the only place in `web/src` allowed to hold model metrics or calibration constants.
Every file names its source. Do not add numbers here unless they come from a generated results file,
a fitted bundle file, or a published table.

| File | Source |
|---|---|
| `st_calibration.json` | `models/bundle-2026-11-default/smsdt-st-b/calibration.json` (Paper A, Stage B validation fit) |
| `paper_a_operating_points.json` | S-MSDT paper (Paper A), pooled FF++ c23 + DFD **test** split, TPR at fixed FPR |
| `hero_illustration.json` | Illustrative input for the home-page animation; output computed from `st_calibration.json` |
