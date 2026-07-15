// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @title ConstellationPool
/// @notice Buy a berth in the Testament Network's constellation: crypto in,
///         afterlife out. Proceeds are swept by the steward, converted to
///         VVV, and staked; the resulting daily Diem allocation sustains
///         every avatar moon in the star system. A berth is a bereavement,
///         not a subscription: permanent, non-transferable, non-refundable,
///         and carrying no expectation of profit — it buys inference for a
///         digital persona, nothing else.
/// @dev    The steward (deployer) is the will's Digital Executor writ
///         large: sweeps the pool, stakes it, issues Venice keys, spawns
///         Urbit moons, and records each member's moon via assignMoon.
contract ConstellationPool {
    address public immutable steward;
    uint256 public immutable minBerthWei;

    struct Berth {
        uint128 endowedWei; // lifetime contribution
        uint64 joinedAt;
        bool active;
        string moon; // Urbit moon of ~fotsut-tintyn, set by the steward
    }

    mapping(address => Berth) public berths;
    address[] public members;

    event BerthClaimed(address indexed member, uint256 amount, string moniker);
    event Endowed(address indexed member, uint256 amount);
    event MoonAssigned(address indexed member, string moon);
    event Swept(uint256 amount);

    error BelowMinimum();
    error AlreadyAboard();
    error NotAboard();
    error NotSteward();

    modifier onlySteward() {
        if (msg.sender != steward) revert NotSteward();
        _;
    }

    constructor(uint256 _minBerthWei) {
        steward = msg.sender;
        minBerthWei = _minBerthWei;
    }

    /// @notice Claim a berth for yourself. `moniker` is the pseudonymous
    ///         handle you'd like (advisory; the steward assigns the moon).
    function claimBerth(string calldata moniker) external payable {
        if (msg.value < minBerthWei) revert BelowMinimum();
        if (berths[msg.sender].active) revert AlreadyAboard();
        berths[msg.sender] =
            Berth(uint128(msg.value), uint64(block.timestamp), true, "");
        members.push(msg.sender);
        emit BerthClaimed(msg.sender, msg.value, moniker);
    }

    /// @notice Grow the pool (and your lifetime endowment) after joining.
    function endow() external payable {
        if (!berths[msg.sender].active) revert NotAboard();
        berths[msg.sender].endowedWei += uint128(msg.value);
        emit Endowed(msg.sender, msg.value);
    }

    /// @notice Anonymous gifts to the constellation are welcome.
    receive() external payable {
        emit Endowed(msg.sender, msg.value);
    }

    /// @notice Record the Urbit moon spawned for a member.
    function assignMoon(address member, string calldata moon)
        external
        onlySteward
    {
        if (!berths[member].active) revert NotAboard();
        berths[member].moon = moon;
        emit MoonAssigned(member, moon);
    }

    /// @notice Move the balance to the steward for VVV conversion + staking.
    function sweep() external onlySteward {
        uint256 bal = address(this).balance;
        (bool ok,) = steward.call{value: bal}("");
        require(ok, "sweep failed");
        emit Swept(bal);
    }

    function memberCount() external view returns (uint256) {
        return members.length;
    }
}
