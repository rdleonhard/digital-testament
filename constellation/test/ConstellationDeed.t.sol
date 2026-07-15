// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Test} from "forge-std/Test.sol";
import {ConstellationDeed} from "../src/ConstellationDeed.sol";

contract ConstellationDeedTest is Test {
    ConstellationDeed deed;
    address alice = makeAddr("alice");
    address bob = makeAddr("bob");
    uint256 constant MOON = 0.005 ether;
    uint256 constant PLANET = 0.05 ether;

    receive() external payable {}

    function setUp() public {
        deed = new ConstellationDeed(MOON, PLANET, 100); // 0.1 Diem/day UBC
        vm.deal(alice, 1 ether);
        vm.deal(bob, 1 ether);
    }

    function test_mintMoon() public {
        vm.prank(alice);
        uint256 id = deed.mintMoon{value: MOON}();
        assertEq(deed.ownerOf(id), alice);
        (ConstellationDeed.Tier tier,,) = deed.deeds(id);
        assertEq(uint8(tier), uint8(ConstellationDeed.Tier.Moon));
    }

    function test_mintPlanet() public {
        vm.prank(alice);
        uint256 id = deed.mintPlanet{value: PLANET}();
        (ConstellationDeed.Tier tier,,) = deed.deeds(id);
        assertEq(uint8(tier), uint8(ConstellationDeed.Tier.Planet));
    }

    function test_mint_underpaid_reverts() public {
        vm.startPrank(alice);
        vm.expectRevert(ConstellationDeed.WrongPayment.selector);
        deed.mintMoon{value: MOON - 1}();
        vm.expectRevert(ConstellationDeed.WrongPayment.selector);
        deed.mintPlanet{value: PLANET - 1}();
        vm.stopPrank();
    }

    function test_deed_is_transferable_devisable() public {
        vm.prank(alice);
        uint256 id = deed.mintMoon{value: MOON}();
        // the estate passes the deed to the heir
        vm.prank(alice);
        deed.transferFrom(alice, bob, id);
        assertEq(deed.ownerOf(id), bob);
    }

    function test_bindPoint_stewardOnly() public {
        vm.prank(alice);
        uint256 id = deed.mintPlanet{value: PLANET}();
        deed.bindPoint(id, "~fotsut-tintyn");
        (,, string memory point) = deed.deeds(id);
        assertEq(point, "~fotsut-tintyn");

        vm.prank(bob);
        vm.expectRevert(ConstellationDeed.NotSteward.selector);
        deed.bindPoint(id, "~hijack");
    }

    function test_setUBC_and_prices_stewardOnly() public {
        deed.setUBC(250);
        assertEq(deed.ubcMilliDiem(), 250);
        deed.setPrices(0.01 ether, 0.1 ether);
        assertEq(deed.moonPriceWei(), 0.01 ether);

        vm.startPrank(bob);
        vm.expectRevert(ConstellationDeed.NotSteward.selector);
        deed.setUBC(1);
        vm.expectRevert(ConstellationDeed.NotSteward.selector);
        deed.setPrices(1, 2);
        vm.stopPrank();
    }

    function test_sweep() public {
        vm.prank(alice);
        deed.mintPlanet{value: PLANET}();
        uint256 before = address(this).balance;
        deed.sweep();
        assertEq(address(this).balance, before + PLANET);

        vm.prank(bob);
        vm.expectRevert(ConstellationDeed.NotSteward.selector);
        deed.sweep();
    }

    function test_tokenURI_onchain_metadata() public {
        vm.prank(alice);
        uint256 id = deed.mintMoon{value: MOON}();
        string memory uri = deed.tokenURI(id);
        assertEq(bytes(uri).length > 60, true);
        // starts with the data-URI scheme
        bytes memory prefix = bytes("data:application/json;base64,");
        for (uint256 i = 0; i < prefix.length; i++) {
            assertEq(bytes(uri)[i], prefix[i]);
        }
    }
}
