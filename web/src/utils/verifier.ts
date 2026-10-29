import { ed25519 } from '@noble/curves/ed25519.js';
import { sha256 } from '@noble/hashes/sha2.js';

/**
 * RFC 8785 JSON Canonicalization Scheme (JCS)
 */
export function canonicalizeJson(obj: unknown): string {
  if (obj === null || typeof obj !== 'object') {
    return JSON.stringify(obj);
  }
  if (Array.isArray(obj)) {
    return '[' + obj.map((item) => canonicalizeJson(item)).join(',') + ']';
  }
  const keys = Object.keys(obj as Record<string, unknown>).sort();
  const pairs = keys.map((key) => {
    return JSON.stringify(key) + ':' + canonicalizeJson((obj as Record<string, unknown>)[key]);
  });
  return '{' + pairs.join(',') + '}';
}

export function fromB64Url(str: string): Uint8Array {
  let b64 = str.replace(/-/g, '+').replace(/_/g, '/');
  while (b64.length % 4 !== 0) b64 += '=';
  const binary = atob(b64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) {
    bytes[i] = binary.charCodeAt(i);
  }
  return bytes;
}

export function toB64Url(bytes: Uint8Array): string {
  let binary = '';
  for (let i = 0; i < bytes.length; i++) {
    binary += String.fromCharCode(bytes[i]);
  }
  return btoa(binary).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}

export function bytesToHex(bytes: Uint8Array): string {
  return Array.from(bytes)
    .map((b) => b.toString(16).padStart(2, '0'))
    .join('');
}

export function hexToBytes(hex: string): Uint8Array {
  const cleanHex = hex.startsWith('0x') ? hex.slice(2) : hex;
  const bytes = new Uint8Array(cleanHex.length / 2);
  for (let i = 0; i < bytes.length; i++) {
    bytes[i] = parseInt(cleanHex.substr(i * 2, 2), 16);
  }
  return bytes;
}

export async function sha256Bytes(data: Uint8Array): Promise<Uint8Array> {
  const hashBuffer = await crypto.subtle.digest('SHA-256', data as unknown as BufferSource);
  return new Uint8Array(hashBuffer);
}

/**
 * Streamed SHA-256 of a file: reads 8 MiB chunks so large videos are never loaded into memory at once.
 * WebCrypto has no incremental digest, so this uses @noble/hashes.
 */
export async function computeFileSha256(
  file: Blob,
  onProgress?: (fraction: number) => void,
  chunkSize = 8 * 1024 * 1024
): Promise<string> {
  const CHUNK = chunkSize;
  const hasher = sha256.create();
  for (let offset = 0; offset < file.size; offset += CHUNK) {
    const buf = new Uint8Array(await file.slice(offset, offset + CHUNK).arrayBuffer());
    hasher.update(buf);
    onProgress?.(Math.min(1, (offset + buf.length) / file.size));
  }
  if (file.size === 0) onProgress?.(1);
  return bytesToHex(hasher.digest());
}

/**
 * Verify Ed25519 digital signature over canonical JCS bytes.
 */
export function verifyEd25519Signature(
  receiptDict: Record<string, unknown>,
  publicKeyB64Url: string
): boolean {
  try {
    const receiptCopy = JSON.parse(JSON.stringify(receiptDict));
    const sigInfo = receiptCopy.signature;
    if (!sigInfo || sigInfo.alg !== 'Ed25519' || !sigInfo.value) {
      return false;
    }
    delete receiptCopy.signature;

    const canonicalJson = canonicalizeJson(receiptCopy);
    const messageBytes = new TextEncoder().encode(canonicalJson);

    const sigBytes = fromB64Url(sigInfo.value);
    const pubBytes = fromB64Url(publicKeyB64Url);

    return ed25519.verify(sigBytes, messageBytes, pubBytes);
  } catch {
    return false;
  }
}

/**
 * RFC 6962 Leaf Hash: sha256(0x00 || receipt_sha256_bytes)
 */
export async function hashLeaf(receiptSha256Hex: string): Promise<Uint8Array> {
  const valBytes = hexToBytes(receiptSha256Hex);
  const leafInput = new Uint8Array(1 + valBytes.length);
  leafInput[0] = 0x00;
  leafInput.set(valBytes, 1);
  return sha256Bytes(leafInput);
}

/**
 * RFC 6962 Internal Node Hash: sha256(0x01 || left || right)
 */
export async function hashInternal(left: Uint8Array, right: Uint8Array): Promise<Uint8Array> {
  const nodeInput = new Uint8Array(1 + left.length + right.length);
  nodeInput[0] = 0x01;
  nodeInput.set(left, 1);
  nodeInput.set(right, 1 + left.length);
  return sha256Bytes(nodeInput);
}

/**
 * Verify Merkle audit path from receipt leaf to expected root.
 */
export async function verifyClientMerkleProof(
  receiptSha256Hex: string,
  proof: Array<{ position: 'left' | 'right'; data: string }>,
  expectedRootHex: string
): Promise<boolean> {
  try {
    let current = await hashLeaf(receiptSha256Hex);
    for (const step of proof) {
      const sibling = hexToBytes(step.data);
      if (step.position === 'left') {
        current = await hashInternal(sibling, current);
      } else {
        current = await hashInternal(current, sibling);
      }
    }
    const cleanExpected = expectedRootHex.startsWith('0x') ? expectedRootHex.slice(2) : expectedRootHex;
    return bytesToHex(current).toLowerCase() === cleanExpected.toLowerCase();
  } catch {
    return false;
  }
}
