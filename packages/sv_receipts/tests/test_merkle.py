import hashlib

import pytest
from sv_receipts.crypto import generate_keypair
from sv_receipts.merkle import (
    MerkleTree,
    create_merkle_batch,
    verify_merkle_proof,
)
from sv_receipts.schema import build_detection_receipt


def test_merkle_tree_proof_verification():
    hashes = [hashlib.sha256(f"receipt_{i}".encode()).hexdigest() for i in range(4)]
    tree = MerkleTree(hashes)
    root = tree.root_hex
    assert len(root) == 64

    for i in range(4):
        proof = tree.get_proof(i)
        assert verify_merkle_proof(hashes[i], proof, root) is True


def test_merkle_tree_odd_leaves():
    for count in [1, 3, 5, 7, 9]:
        hashes = [
            hashlib.sha256(f"receipt_odd_{count}_{i}".encode()).hexdigest() for i in range(count)
        ]
        tree = MerkleTree(hashes)
        root = tree.root_hex
        for i in range(count):
            proof = tree.get_proof(i)
            assert verify_merkle_proof(hashes[i], proof, root) is True


def test_merkle_tree_empty_fails():
    with pytest.raises(ValueError, match="Cannot construct empty Merkle tree"):
        MerkleTree([])


def test_merkle_proof_out_of_bounds():
    tree = MerkleTree([hashlib.sha256(b"r").hexdigest()])
    with pytest.raises(IndexError):
        tree.get_proof(1)
    with pytest.raises(IndexError):
        tree.get_proof(-1)


def test_merkle_tampering_detection():
    hashes = [hashlib.sha256(f"r_{i}".encode()).hexdigest() for i in range(4)]
    tree = MerkleTree(hashes)
    root = tree.root_hex

    proof = tree.get_proof(0)

    # 1. Correct proof passes
    assert verify_merkle_proof(hashes[0], proof, root) is True

    # 2. Corrupted leaf hash fails
    fake_leaf = hashlib.sha256(b"fake").hexdigest()
    assert verify_merkle_proof(fake_leaf, proof, root) is False

    # 3. Corrupted sibling data in proof fails
    tampered_proof = [dict(p) for p in proof]
    tampered_proof[0]["data"] = "0" * 64
    assert verify_merkle_proof(hashes[0], tampered_proof, root) is False

    # 4. Swapped sibling position fails
    swapped_proof = [dict(p) for p in proof]
    swapped_proof[0]["position"] = "left" if swapped_proof[0]["position"] == "right" else "right"
    assert verify_merkle_proof(hashes[0], swapped_proof, root) is False

    # 5. Wrong expected root fails
    assert verify_merkle_proof(hashes[0], proof, "f" * 64) is False


def test_create_merkle_batch():
    priv, pub = generate_keypair()
    receipts = [
        build_detection_receipt(
            analysis_id=f"an_batch_{i}",
            content_sha256=hashlib.sha256(f"video_{i}".encode()).hexdigest(),
            size_bytes=1000 * (i + 1),
            duration_s=10.0 + i,
            container="mp4",
            decision_band="likely_authentic" if i % 2 == 0 else "needs_review",
            p_bal=0.1 * (i + 1),
            p_prior=0.01,
            prior_prevalence=0.01,
            private_key=priv,
        )
        for i in range(5)
    ]

    batch_id = "batch_test_20261029_001"
    tree, batched_receipts = create_merkle_batch(receipts, batch_id)

    assert len(batched_receipts) == 5
    assert tree.root_hex is not None

    for i, b_receipt in enumerate(batched_receipts):
        assert "merkle" in b_receipt
        merkle_block = b_receipt["merkle"]
        assert merkle_block["root"] == tree.root_hex
        assert merkle_block["leaf_index"] == i
        assert merkle_block["batch_id"] == batch_id

        # Compute receipt hash before merkle block was added
        original_r = receipts[i]
        from sv_core.jcs import canonicalize_json

        orig_hash = hashlib.sha256(canonicalize_json(original_r)).hexdigest()
        assert verify_merkle_proof(orig_hash, merkle_block["proof"], merkle_block["root"]) is True
