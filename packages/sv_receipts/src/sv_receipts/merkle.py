import hashlib
from typing import List, Tuple, Dict, Any


def hash_leaf(receipt_sha256_hex: str) -> bytes:
    """Leaf = sha256(0x00 || receipt_sha256_bytes)."""
    val_bytes = bytes.fromhex(receipt_sha256_hex)
    return hashlib.sha256(b"\x00" + val_bytes).digest()


def hash_internal(left: bytes, right: bytes) -> bytes:
    """Internal node = sha256(0x01 || left || right)."""
    return hashlib.sha256(b"\x01" + left + right).digest()


class MerkleTree:
    """Binary Merkle Tree for receipt batching conforming to SPEC §10.2."""

    def __init__(self, receipt_hashes_hex: List[str]):
        if not receipt_hashes_hex:
            raise ValueError("Cannot construct empty Merkle tree")
        self.leaves = [hash_leaf(h) for h in receipt_hashes_hex]
        self.levels: List[List[bytes]] = [self.leaves]
        self._build()

    def _build(self) -> None:
        current = self.leaves
        while len(current) > 1:
            next_level = []
            if len(current) % 2 != 0:
                current = current + [current[-1]]  # Duplicate last leaf
            for i in range(0, len(current), 2):
                next_level.append(hash_internal(current[i], current[i + 1]))
            self.levels.append(next_level)
            current = next_level

    @property
    def root(self) -> bytes:
        return self.levels[-1][0]

    @property
    def root_hex(self) -> str:
        return self.root.hex()

    def get_proof(self, leaf_index: int) -> List[Dict[str, str]]:
        """Generate audit path proof for a given leaf index."""
        if leaf_index < 0 or leaf_index >= len(self.leaves):
            raise IndexError("Leaf index out of bounds")
        
        proof = []
        idx = leaf_index
        for level in self.levels[:-1]:
            if len(level) % 2 != 0:
                level = level + [level[-1]]
            is_right = (idx % 2 == 1)
            sibling_idx = idx - 1 if is_right else idx + 1
            proof.append({
                "position": "left" if is_right else "right",
                "data": level[sibling_idx].hex()
            })
            idx //= 2
        return proof


def verify_merkle_proof(receipt_sha256_hex: str, proof: List[Dict[str, str]], expected_root_hex: str) -> bool:
    """Verify proof from leaf to root."""
    current = hash_leaf(receipt_sha256_hex)
    for p in proof:
        sibling = bytes.fromhex(p["data"])
        if p["position"] == "left":
            current = hash_internal(sibling, current)
        else:
            current = hash_internal(current, sibling)
    return current.hex() == expected_root_hex
