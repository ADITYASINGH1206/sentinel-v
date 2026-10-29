---
name: receipts-and-anchoring
description: Guides canonical RFC 8785 JSON generation, Ed25519 signing, Merkle tree batching, and EVM smart contract anchoring via ReceiptAnchor.sol.
---

# Detection Receipts and Blockchain Anchoring Skill

This skill explains how detection receipts are cryptographically generated, canonicalized, signed, batched into Merkle trees, and anchored on EVM blockchains (SPEC §10).

## Receipt Lifecycle

1. **Analysis Completion:**
   - Inference yields final probability `p_bal`, prior-adjusted `p_prior`, decisive track, and `evidence_root`.
2. **Canonical JSON Serialization (RFC 8785):**
   - Keys are sorted lexicographically by UTF-16 code units.
   - Whitespace outside string literals is removed.
   - Floats are rounded to 4 decimals before serialization.
   - Signature field is omitted during signing input generation:
     $$\text{Signing Input} = \text{JCS}(\text{Receipt} \setminus \{\text{signature}\})$$
3. **Ed25519 Signing:**
   - Signed using service private key.
   - Result encoded as base64url string attached as `receipt.signature`.
   - Keys published at `/.well-known/sv-keys.json`.

---

## Merkle Batching Specification (SPEC §10.2)

- Receipts within a batch interval (`SV_ANCHOR_BATCH_SECONDS=600`) are aggregated.
- **Leaf Hash:**
  $$\text{Leaf} = \text{SHA256}(0x00 \mathbin{\Vert} \text{receipt\_sha256})$$
- **Internal Node Hash:**
  $$\text{Node} = \text{SHA256}(0x01 \mathbin{\Vert} \text{left} \mathbin{\Vert} \text{right})$$
- Odd nodes are duplicated on unbalanced levels.

---

## Smart Contract Interaction (`ReceiptAnchor.sol`)

Located at `contracts/src/ReceiptAnchor.sol`. Completely non-invasive to SENTINEL's contracts.

```solidity
function anchor(bytes32 root, uint32 count, string calldata batchId) external;
```

### Foundry Verification Commands
```bash
cd contracts
forge test -vvv     # Run full contract test suite
forge snapshot      # Record gas usage for paper experiment E12
```

---

## Zero-Trust Browser Verification (`web/src/routes/PublicVerify.tsx`)

The verification page executes 5 verification checks client-side:
1. **Signature:** WebCrypto Ed25519 verification against public key.
2. **Media Hash:** Streaming SHA-256 computed on dropped video in Web Worker (video is never uploaded).
3. **Merkle Inclusion:** Verification of proof path from leaf to batch root.
4. **On-Chain Anchor:** Direct JSON-RPC call to `anchoredAt(root) > 0` via ethers.js.
5. **Registry Check:** Check model weights SHA-256 and policy hash against `GET /v1/registry/hashes`.

