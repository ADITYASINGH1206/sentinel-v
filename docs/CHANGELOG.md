# Changelog — SENTINEL-V

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased] - 2026-10-28

### Added
- Monorepo directory structure across `packages/`, `services/`, `web/`, `contracts/`, `eval/`, and `infra/`.
- Full project specification in `docs/SPEC.md` and agent instructions in `AGENTS.md`.
- Architecture decision records in `docs/DECISIONS.md`.
- Blocker tracking log in `docs/QUESTIONS.md`.
- Milestone tracking templates under `docs/milestones/`.
- Foundational packages:
  - `sv_core`: Settings via pydantic-settings, domain schemas, error classes, RFC 8785 canonical JSON serializer.
  - `sv_engine`: Preprocessing interfaces, model adapter protocols, deterministic mock engine.
  - `sv_fusion`: Multi-signal fusion interfaces (C2PA, SwinV2 AI image detector).
  - `sv_receipts`: Cryptographic detection receipt generation, Ed25519 signing, Merkle trees.
- API service scaffold with FastAPI endpoints, CORS, health checks, and SSE streams.
- Reviewer console web application scaffold (React, TypeScript, Vite, Tailwind).
- Solidity contract `ReceiptAnchor.sol` and Foundry suite for EVM anchoring.
- Docker compose orchestration and Makefile automation.
