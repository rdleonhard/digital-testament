// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Test} from "forge-std/Test.sol";
import {ConstellationPool} from "../src/ConstellationPool.sol";

contract ConstellationPoolTest is Test {
    ConstellationPool pool;
    address steward = address(this);
    address alice = makeAddr("alice");
    address bob = makeAddr("bob");
    uint256 constant MIN = 0.01 ether;

    receive() external payable {} // steward must be able to receive sweep

    function setUp() public {
        pool = new ConstellationPool(MIN, "~fotsut-tintyn");
        vm.deal(alice, 1 ether);
        vm.deal(bob, 1 ether);
    }

    function test_planetRecorded() public view {
        assertEq(pool.planet(), "~fotsut-tintyn");
    }

    function test_claimBerth() public {
        vm.prank(alice);
        pool.claimBerth{value: MIN}("harbor-ghost");
        (uint128 endowed,, bool active, string memory moon) =
            pool.berths(alice);
        assertEq(endowed, MIN);
        assertTrue(active);
        assertEq(bytes(moon).length, 0);
        assertEq(pool.memberCount(), 1);
    }

    function test_claimBerth_belowMinimum_reverts() public {
        vm.prank(alice);
        vm.expectRevert(ConstellationPool.BelowMinimum.selector);
        pool.claimBerth{value: MIN - 1}("cheapskate");
    }

    function test_claimBerth_twice_reverts() public {
        vm.startPrank(alice);
        pool.claimBerth{value: MIN}("once");
        vm.expectRevert(ConstellationPool.AlreadyAboard.selector);
        pool.claimBerth{value: MIN}("twice");
        vm.stopPrank();
    }

    function test_endow_accumulates() public {
        vm.startPrank(alice);
        pool.claimBerth{value: MIN}("giver");
        pool.endow{value: 0.5 ether}();
        vm.stopPrank();
        (uint128 endowed,,,) = pool.berths(alice);
        assertEq(endowed, MIN + 0.5 ether);
    }

    function test_endow_nonMember_reverts() public {
        vm.prank(bob);
        vm.expectRevert(ConstellationPool.NotAboard.selector);
        pool.endow{value: MIN}();
    }

    function test_receive_gift() public {
        vm.prank(bob);
        (bool ok,) = address(pool).call{value: 0.2 ether}("");
        assertTrue(ok);
        assertEq(address(pool).balance, 0.2 ether);
    }

    function test_assignMoon_stewardOnly() public {
        vm.prank(alice);
        pool.claimBerth{value: MIN}("mooner");
        pool.assignMoon(alice, "~fotsut-tintyn-ridlur-figbud");
        (,,, string memory moon) = pool.berths(alice);
        assertEq(moon, "~fotsut-tintyn-ridlur-figbud");

        vm.prank(bob);
        vm.expectRevert(ConstellationPool.NotSteward.selector);
        pool.assignMoon(alice, "~hijack");
    }

    function test_assignMoon_nonMember_reverts() public {
        vm.expectRevert(ConstellationPool.NotAboard.selector);
        pool.assignMoon(bob, "~nobody");
    }

    function test_sweep_stewardOnly_transfers() public {
        vm.prank(alice);
        pool.claimBerth{value: 0.7 ether}("whale");
        uint256 before = address(this).balance;
        pool.sweep();
        assertEq(address(this).balance, before + 0.7 ether);
        assertEq(address(pool).balance, 0);

        vm.prank(bob);
        vm.expectRevert(ConstellationPool.NotSteward.selector);
        pool.sweep();
    }

    function testFuzz_claimBerth(uint96 amount) public {
        vm.assume(amount >= MIN);
        vm.deal(alice, amount);
        vm.prank(alice);
        pool.claimBerth{value: amount}("fuzz");
        (uint128 endowed,,,) = pool.berths(alice);
        assertEq(endowed, amount);
    }
}
