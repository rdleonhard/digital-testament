// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {ERC721} from "openzeppelin-contracts/token/ERC721/ERC721.sol";
import {Strings} from "openzeppelin-contracts/utils/Strings.sol";
import {Base64} from "openzeppelin-contracts/utils/Base64.sol";

/// @title ConstellationDeed
/// @notice The normie front door to the Testament Network: buy a deed,
///         own a place in the star system. A MOON deed houses one avatar;
///         a PLANET deed is a whole neighborhood (its own pool, its own
///         moons, spawned from the star ~sibpub). Deeds are ordinary
///         ERC-721 tokens on purpose: transferable, sellable, and --
///         the point -- DEVISABLE. A deed passes under a will like any
///         other personal property; whoever holds it controls the berth.
///
///         Every deed, regardless of tier, entitles its avatar to the
///         Universal Basic Compute floor: a minimum daily Diem allowance
///         declared on-chain here and enforced by the pool's key-carver.
///         Payments are swept by the steward, converted to VVV, and
///         staked; the stake's daily yield funds the UBC and the world.
contract ConstellationDeed is ERC721 {
    enum Tier {
        Moon,
        Planet
    }

    struct Deed {
        Tier tier;
        uint64 mintedAt;
        string point; // Urbit identity bound by the steward after spawning
    }

    address public immutable steward;
    uint256 public moonPriceWei;
    uint256 public planetPriceWei;
    /// @notice Universal Basic Compute: minimum daily inference for every
    ///         deed-holding avatar, in milli-Diem (1000 = 1 Diem/day).
    uint256 public ubcMilliDiem;
    uint256 public nextId;
    mapping(uint256 => Deed) public deeds;

    event DeedMinted(
        uint256 indexed id, address indexed owner, Tier tier, uint256 paid
    );
    event PointBound(uint256 indexed id, string point);
    event UBCSet(uint256 milliDiem);
    event PricesSet(uint256 moonWei, uint256 planetWei);
    event Swept(uint256 amount);

    error WrongPayment();
    error NotSteward();

    modifier onlySteward() {
        if (msg.sender != steward) revert NotSteward();
        _;
    }

    constructor(uint256 _moonWei, uint256 _planetWei, uint256 _ubcMilliDiem)
        ERC721("Testament Constellation Deed", "TOMB")
    {
        steward = msg.sender;
        moonPriceWei = _moonWei;
        planetPriceWei = _planetWei;
        ubcMilliDiem = _ubcMilliDiem;
    }

    function mintMoon() external payable returns (uint256 id) {
        if (msg.value < moonPriceWei) revert WrongPayment();
        id = _mintDeed(Tier.Moon);
    }

    function mintPlanet() external payable returns (uint256 id) {
        if (msg.value < planetPriceWei) revert WrongPayment();
        id = _mintDeed(Tier.Planet);
    }

    function _mintDeed(Tier tier) internal returns (uint256 id) {
        id = nextId++;
        deeds[id] = Deed(tier, uint64(block.timestamp), "");
        _safeMint(msg.sender, id);
        emit DeedMinted(id, msg.sender, tier, msg.value);
    }

    /// @notice Bind the spawned Urbit point (moon or planet) to a deed.
    function bindPoint(uint256 id, string calldata point)
        external
        onlySteward
    {
        _requireOwned(id);
        deeds[id].point = point;
        emit PointBound(id, point);
    }

    function setUBC(uint256 milliDiem) external onlySteward {
        ubcMilliDiem = milliDiem;
        emit UBCSet(milliDiem);
    }

    function setPrices(uint256 moonWei, uint256 planetWei)
        external
        onlySteward
    {
        moonPriceWei = moonWei;
        planetPriceWei = planetWei;
        emit PricesSet(moonWei, planetWei);
    }

    function sweep() external onlySteward {
        uint256 bal = address(this).balance;
        (bool ok,) = steward.call{value: bal}("");
        require(ok, "sweep failed");
        emit Swept(bal);
    }

    receive() external payable {}

    /// @notice On-chain metadata so the deed reads correctly in any wallet.
    function tokenURI(uint256 id)
        public
        view
        override
        returns (string memory)
    {
        _requireOwned(id);
        Deed memory d = deeds[id];
        string memory tier = d.tier == Tier.Planet ? "Planet" : "Moon";
        string memory point =
            bytes(d.point).length > 0 ? d.point : "(unassigned)";
        bytes memory json = abi.encodePacked(
            '{"name":"Constellation ',
            tier,
            " #",
            Strings.toString(id),
            '","description":"A deed in the Testament Network star system. ',
            "Houses a digital avatar with Universal Basic Compute of ",
            Strings.toString(ubcMilliDiem),
            ' milli-Diem/day. Urbit point: ',
            point,
            '.","attributes":[{"trait_type":"Tier","value":"',
            tier,
            '"},{"trait_type":"Urbit Point","value":"',
            point,
            '"}]}'
        );
        return string(
            abi.encodePacked(
                "data:application/json;base64,", Base64.encode(json)
            )
        );
    }
}
