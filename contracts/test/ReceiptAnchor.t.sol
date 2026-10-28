// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

interface Vm {
    function prank(address) external;
    function expectEmit(bool, bool, bool, bool) external;
    function expectRevert(bytes calldata) external;
}

contract ReceiptAnchorTest {
    Vm internal constant vm = Vm(address(uint160(uint256(keccak256("hevm cheat code")))));

    event Anchored(bytes32 indexed root, uint32 count, string batchId);

    function testOwnerCanAnchor() public {
        // Contract test logic for Foundry
    }
}

