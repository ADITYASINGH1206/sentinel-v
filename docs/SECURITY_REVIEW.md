# Security Review & Hardening Audit — SENTINEL-V

**Document Version:** 1.0.0  
**Target Milestone:** M11: Security Hardening & Release (SPEC §12, §21, §23)  
**Security Classification:** Public / Auditable  

---

## 1. Executive Summary

SENTINEL-V is a calibrated and auditable video deepfake screening system. Because the platform ingests untrusted media from arbitrary public and partner URLs, processes computationally heavy video decompression, issues digitally signed detection receipts, and triggers Web3/Supabase moderation actions, robust defense-in-depth security is paramount.

This document details the threat model, mitigation controls, container isolation, cryptographic assurances, and empirical fuzzing verification conducted during Milestone M11.

---

## 2. Threat Modeling & Attack Surfaces

| Attack Vector | Impact | Mitigation Strategy | Verification Status |
| :--- | :--- | :--- | :---: |
| **Server-Side Request Forgery (SSRF)** | Access to cloud metadata (`169.254.169.254`), internal cluster services, private VPC resources. | Strict DNS pre-resolution, loopback/private/link-local/metadata IP filtering, bounded redirects (max 3). | ✅ Verified |
| **Decompression Bomb / Malformed Video** | Memory exhaustion, OOM killer, worker process crash, infinite hang. | Dimension upper bounds ($\le 8192$), frame decode limits ($T \le 250$), structured error handling to `DECODE_FAILURE`. | ✅ Verified |
| **Receipt Forgery / Tampering** | Falsification of screening verdicts, altered probability scores. | RFC 8785 (JCS) canonical serialization, Ed25519 digital signatures, RFC 6962 Merkle batching, EVM on-chain anchoring. | ✅ Verified |
| **Replay & Timing Attacks on Webhooks** | Unauthorized post updates, timing leakage on HMAC signature verification. | Timestamp tolerance ($\le 300$s), timing-safe comparisons (`hmac.compare_digest`, `crypto.timingSafeEqual`). | ✅ Verified |
| **Container Breakout / Privilege Escalation** | Host takeover from malicious media decoding libraries. | Non-root worker execution (`svuser:1000`), read-only rootfs, tmpfs `/tmp`, cgroup limits, isolated internal network. | ✅ Verified |
| **Deceptive UI & Overconfidence** | Consequential moderation decisions based on uncalibrated or misleading labels. | Strict anti-deception copy guidelines: zero bare "FAKE"/"REAL" stamps, calibrated bands, mandatory disclaimers. | ✅ Verified |

---

## 3. Implemented Security Controls

### 3.1 SSRF Sandboxing (`services/api/src/sv_api/security.py`)
- **Scheme Validation:** Restricts input URLs strictly to `http://` and `https://`.
- **Blocked Hostnames:** Automatically blocks `localhost`, `metadata.google.internal`, `metadata.internal`, and `instance-data`.
- **Pre-Resolution DNS Resolution:** Resolves all IPv4 and IPv6 addresses via `socket.getaddrinfo` prior to opening HTTP connections.
- **Prohibited IP Ranges:**
  - RFC 1918 Private ranges: `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`
  - Loopback: `127.0.0.0/8`, `::1`
  - Link-local: `169.254.0.0/16`, `fe80::/10`
  - Cloud Metadata IPs: `169.254.169.254` (AWS, GCP, Azure, DigitalOcean), `100.100.100.200` (Alibaba)
  - IPv6-mapped IPv4 representations (e.g. `::ffff:127.0.0.1`, `::ffff:169.254.169.254`)
- **Redirect Bounds:** Maximum of 3 redirects; target URLs re-validated at each redirect hop before connection.
- **Streaming Limits:** Connect timeout 10s, total timeout 120s, maximum payload size capped at `SV_MAX_UPLOAD_MB=500` with early abort.

### 3.2 Worker Container Sandboxing (`infra/compose.yaml`, `infra/docker/worker-cpu.Dockerfile`)
- **Non-Root Execution:** Celery workers execute under unprivileged user `svuser` (UID `1000`, GID `1000`).
- **Read-Only Root Filesystem:** Container root filesystem is mounted read-only (`read_only: true`).
- **Scratch Space:** Temporary files restricted to ephemeral tmpfs mounts (`/tmp:size=2G,mode=1777`, `/run:size=64M,mode=1777`).
- **Network Isolation:** Workers attached exclusively to an un-routed `internal` Docker network (`internal: true`).
- **Cgroup Caps:** Hard limits enforced at 4.0 CPU cores and 8 GB RAM per worker container.

### 3.3 Media Parser Resilience (`packages/sv_engine/src/sv_engine/preprocess/decode.py`)
- **Extreme Dimensions:** Dimensions validated within $1 \le w, h \le 8192$; invalid or extreme dimensions raise `DecodeError`.
- **Frame Rate Normalization:** Zero or negative fps rates normalized to 30.0 fps default.
- **Pipeline Fault Tolerance:** Video decoding exceptions caught in `_async_preprocess`, classifying video safely as `inconclusive` (`DECODE_FAILURE`) without crashing worker queues.

### 3.4 Cryptographic Verification & Webhooks
- **Canonical JSON:** Strict key-ordering and whitespace normalization conforming to RFC 8785.
- **Digital Signatures:** Ed25519 digital signatures with JWKS export via `/.well-known/sv-keys.json`.
- **Merkle Batching:** RFC 6962 domain-separated tree (`0x00` leaf, `0x01` internal node).
- **On-Chain EVM Anchoring:** `ReceiptAnchor.sol` immutable registry preventing duplicate or unauthorized root anchoring.
- **Webhook HMAC:** Payloads signed with HMAC-SHA256 (`X-SV-Signature: t=<timestamp>,v1=<signature>`) and verified with constant-time equality comparisons.

---

## 4. Empirical Test Verification

1. **SSRF Suite (`tests/test_security_ssrf.py`):** 100% rejection rate across loopback, RFC 1918 subnets, cloud metadata targets, and IPv6-mapped addresses.
2. **Media Fuzzing Suite (`tests/test_media_fuzzing.py`):** 100% clean termination across truncated moov atoms, random bitflips, extreme dimensions ($16384 \times 16384$), and zero-byte containers.
3. **Locust Benchmark (`infra/locustfile.py`):** Validated sustained screening throughput exceeding the 100 videos/hour requirement.
4. **Zero Locked File Integrity (`tools/check_locked_files.py`):** Zero modifications to upstream code or locked SENTINEL modules.

---

## 5. Mandatory Screening Aid Disclaimer

> **Compliance Requirement (SPEC §14.13):**  
> *Screening aid — not proof. Human review required for consequential action.*

