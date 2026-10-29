# Blockers and Open Questions (SPEC §17)

This document tracks items requiring human intervention or external access, along with active fallbacks.

| Blocker ID | Description | Needed From | Impact | Fallback Implemented | Status |
|---|---|---|---|---|---|
| **B1** | Stage C (v3) modules (`ResidualStream`, `EvidenceReadoutV3`, landmark prior function) not in upstream commit `11587f5` | S-MSDT team | Cannot serve Full variant | Adapter raises `NotImplementedError`; cascade uses ST as decider with a notice banner | OPEN |
| **B2** | Exact Stage A test-time evaluation protocol ($K$ and $T$) | S-MSDT team | Stage A calibration precision | Default assumption: $K=8$ clips with $T=1$ spaced over track | OPEN |
| **B3** | Production model checkpoints (.pt / EMA weights) for CNN, S, ST, Full | S-MSDT team (on GPU reference box) | Real-score serving | `SV_ENGINE_MODE=mock` provides deterministic hashing & synthetic heatmaps | OPEN |
| **B4** | Datasets & manifests for DFDC, WildDeepfake, FFIW-10K, DeeperForensics | Research team | Extended cross-dataset evaluation | Mark corresponding Paper B experiments skipped with reason | OPEN |
| **B5** | Commercial license validation for weights trained on FF++, Celeb-DF, DFD | Legal / PI | Commercial deployment restriction | Guard startup with `SV_LICENSE_ACK=research-only` requirement | OPEN |
| **B6** | Ethics board approval & reviewer recruitment for E10 human study | PI / Institution | Reviewer trial execution | Build full study mode into console; defer live participant execution | OPEN |
| **B7** | Testnet deployer private key & RPC endpoint (Sepolia / Amoy) | DevOps / Web3 team | Live chain anchoring | Run local Anvil node in CI; disable live anchor worker if unset | OPEN |
| **B8** | Formal permission from SENTINEL repository maintainers | SENTINEL maintainers | Upstream pull request | All integration code kept self-contained in `integrations/sentinel/` as a patch | OPEN |
| **B9** | Rename the GitHub repository to `veriframe` (Settings → Rename), then update `web/src/brand.ts` `repoUrl` and the README clone URL | Repository owner | Old URL keeps redirecting | Links point at the current repository URL | OPEN |
| **B10** | Trademark / name-availability check for "VeriFrame" before any public launch | Team / legal | Public launch | Name is set in `web/src/brand.ts` and ADR 007 so it can be changed in one place | OPEN |
