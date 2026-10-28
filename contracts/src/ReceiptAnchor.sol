// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/**
 * @title ReceiptAnchor
 * @notice Immutable EVM registry for SENTINEL-V Merkle batch roots.
 * @dev Separate from and non-invasive to SENTINEL's SentinelRegistry.sol.
 */
contract ReceiptAnchor {
    address public immutable owner;
    mapping(bytes32 => uint64) public anchoredAt; // Merkle root => block timestamp

    event Anchored(bytes32 indexed root, uint32 count, string batchId);

    constructor() {
        owner = msg.sender;
    }

    /**
     * @notice Anchor a Merkle batch root on-chain.
     * @param root The 32-byte Merkle root of the batch.
     * @param count Number of receipts included in this batch.
     * @param batchId Unique identifier for the batch.
     */
    function anchor(bytes32 root, uint32 count, string calldata batchId) external {
        require(msg.sender == owner, "not owner");
        require(anchoredAt[root] == 0, "exists");
        anchoredAt[root] = uint64(block.timestamp);
        emit Anchored(root, count, batchId);
    }
}

