# AGENTS.md — SENTINEL-V

You are building **SENTINEL-V**, a calibrated and auditable video deepfake screening service plus a reviewer console, on top of the S-MSDT detector family.

## Read first
1. `docs/SPEC.md` (the full build specification; `SENTINEL-V_Build_Spec.md`). It is authoritative.
2. `docs/DECISIONS.md`, `docs/QUESTIONS.md`, `docs/CHANGELOG.md` (create them if missing).

## Working rules
- Build milestone by milestone (SPEC §16). Start a milestone only after the previous one meets all its acceptance criteria. At the end of each, write `docs/milestones/Mx.md` with what was built, what was deferred, and measured numbers.
- **Never invent results.** Metrics shown anywhere must come from generated files (`eval/results/*.csv`, bundle `calibration.json` / `operating_points.json`) or DB rows. Use `null` / `—` otherwise.
- **Parity before features:** the serving pipeline must match `smsdt/eval_cross.py` within SPEC §6.9 tolerances before UI work relies on real scores. Use `SV_ENGINE_MODE=mock` until then.
- **Import, don't re-implement,** the upstream S-MSDT preprocessing and calibration functions (SPEC Appendix A). The submodule lives at `third_party/smsdt`, pinned.
- **Never modify** upstream repos in place, and never modify SENTINEL's locked files (Web3, contracts, video and image-deepfake code). SENTINEL integration is additive only (SPEC §11).
- Items tagged **[BLOCKER Bx]** (SPEC §17): add an entry to `docs/QUESTIONS.md`, implement the documented fallback, and continue with other work.
- Every other ambiguity: make the conventional choice, record an ADR in `docs/DECISIONS.md`, and continue.
- Write tests first. Keep CI green: `make lint test`. GPU-only tests carry the `gpu` marker.
- UI copy rules (SPEC §14.13): never show bare "FAKE" or "REAL". Always show the calibrated score, the band, the model and policy versions, and the screening-aid disclaimer.
- Secrets never go in git, env dumps or logs.

## Commands (create them in M0)
```
make dev            # compose up with the mock engine + seeded users
make test           # unit + integration (mock)
make lint           # ruff, mypy, eslint, prettier, forbidden-copy lint
make parity         # GPU box: SPEC §6.9
make bundle CKPT=... VARIANT=st VAL_SCORES=...
make eval-<id>      # SPEC §15 experiments; make eval-all
```
