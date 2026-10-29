import hashlib

from sv_receipts.merkle import MerkleTree, verify_merkle_proof


def test_merkle_tree_proof_verification():
    # 4 synthetic receipt sha256 hashes
    hashes = [hashlib.sha256(f"receipt_{i}".encode()).hexdigest() for i in range(4)]
    tree = MerkleTree(hashes)
    root = tree.root_hex
    assert len(root) == 64

    # Verify proof for each leaf
    for i in range(4):
        proof = tree.get_proof(i)
        assert verify_merkle_proof(hashes[i], proof, root) is True


def test_merkle_tree_odd_leaves():
    # 3 leaves (odd count test - duplicates last leaf)
    hashes = [hashlib.sha256(f"receipt_odd_{i}".encode()).hexdigest() for i in range(3)]
    tree = MerkleTree(hashes)
    root = tree.root_hex
    for i in range(3):
        proof = tree.get_proof(i)
        assert verify_merkle_proof(hashes[i], proof, root) is True
