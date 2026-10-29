// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "../src/ReceiptAnchor.sol";

interface Vm {
    function prank(address) external;
    function expectEmit(bool, bool, bool, bool) external;
    function expectRevert(bytes calldata) external;
}

contract ReceiptAnchorTest {
    Vm internal constant vm = Vm(address(uint160(uint256(keccak256("hevm cheat code")))));

    ReceiptAnchor internal anchorContract;
    address internal owner;
    address internal alice;

    event Anchored(bytes32 indexed root, uint32 count, string batchId);

    function setUp() public {
        owner = address(this);
        alice = address(0xA11CE);
        anchorContract = new ReceiptAnchor();
    }

    function testInitialState() public view {
        assert(anchorContract.owner() == owner);
    }

    function testOwnerCanAnchor() public {
        bytes32 testRoot = keccak256("batch_root_1");
        uint32 count = 42;
        string memory batchId = "batch_2026_10_29_001";

        anchorContract.anchor(testRoot, count, batchId);
        assert(anchorContract.anchoredAt(testRoot) > 0);
    }

    function testNonOwnerCannotAnchor() public {
        bytes32 testRoot = keccak256("batch_root_unauthorized");
        vm.prank(alice);
        vm.expectRevert(bytes("not owner"));
        anchorContract.anchor(testRoot, 10, "batch_fail");
    }

    function testCannotAnchorDuplicateRoot() public {
        bytes32 testRoot = keccak256("batch_root_dup");
        anchorContract.anchor(testRoot, 5, "batch_first");

        vm.expectRevert(bytes("exists"));
        anchorContract.anchor(testRoot, 5, "batch_second");
    }

    function testEmitsAnchoredEvent() public {
        bytes32 testRoot = keccak256("batch_root_event");
        uint32 count = 15;
        string memory batchId = "batch_evt";

        vm.expectEmit(true, false, false, true);
        emit Anchored(testRoot, count, batchId);

        anchorContract.anchor(testRoot, count, batchId);
    }
}
