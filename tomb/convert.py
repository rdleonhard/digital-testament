"""USD -> VVV -> Diem endowment calculator.

Models the Persona Endowment (will Article, Section 4): a one-time USD amount
is converted to VVV, staked, and thereafter yields a daily Diem allocation of

    diem_per_day = (staked_vvv / total_active_staked_vvv) * network_capacity

The staked principal is never spent; the allocation refreshes at midnight UTC.
Network parameters float (stakers enter and exit, capacity grows), so they are
inputs here, with documented point-in-time defaults that MUST be overridden
with current chain data for real planning.
"""

import json
import urllib.request
from dataclasses import dataclass

from . import ssl_context

COINGECKO_PRICE_URL = (
    "https://api.coingecko.com/api/v3/simple/price"
    "?ids=venice-token&vs_currencies=usd"
)

# Point-in-time estimates (mid-2026). Override with current values:
# capacity from Venice's published network stats, total active stake from
# the staking contract / venicestats.com. "Active" stakers are those that
# made an API call in the trailing 7 days -- see heartbeat.py.
DEFAULT_NETWORK_CAPACITY_DIEM = 18_148.0
DEFAULT_TOTAL_ACTIVE_STAKED_VVV = 10_000_000.0
# Diem is the standardized daily inference unit; treat 1 Diem ~= 1 USD of
# metered API usage for planning unless you have a better current figure.
DEFAULT_USD_PER_DIEM = 1.0


@dataclass
class EndowmentPlan:
    usd_in: float
    vvv_price_usd: float
    vvv_acquired: float
    total_active_staked_vvv: float
    network_capacity_diem: float
    stake_share: float
    diem_per_day: float
    usd_inference_per_day: float
    usd_inference_per_year: float

    def summary(self) -> str:
        lines = [
            "Persona Endowment plan",
            "----------------------",
            f"Endowment amount:        ${self.usd_in:,.2f}",
            f"VVV price:               ${self.vvv_price_usd:,.4f}",
            f"VVV acquired & staked:   {self.vvv_acquired:,.2f} VVV",
            f"Share of active stake:   {self.stake_share * 100:.6f}%",
            f"  (of {self.total_active_staked_vvv:,.0f} VVV active, "
            f"{self.network_capacity_diem:,.0f} Diem/day capacity)",
            f"Daily Diem allocation:   {self.diem_per_day:,.2f} Diem/day",
            f"~Inference value:        ${self.usd_inference_per_day:,.2f}/day "
            f"(${self.usd_inference_per_year:,.2f}/yr), principal untouched",
            "",
            "Network parameters float; re-run with current --total-staked and",
            "--capacity before relying on this. Not investment advice.",
        ]
        return "\n".join(lines)


def fetch_vvv_price_usd(timeout: float = 10.0) -> float:
    """Spot VVV/USD from CoinGecko."""
    req = urllib.request.Request(
        COINGECKO_PRICE_URL, headers={"User-Agent": "digital-testament/0.1"}
    )
    with urllib.request.urlopen(req, timeout=timeout,
                                context=ssl_context()) as resp:
        data = json.load(resp)
    return float(data["venice-token"]["usd"])


def plan_endowment(
    usd: float,
    vvv_price_usd: float,
    total_active_staked_vvv: float = DEFAULT_TOTAL_ACTIVE_STAKED_VVV,
    network_capacity_diem: float = DEFAULT_NETWORK_CAPACITY_DIEM,
    usd_per_diem: float = DEFAULT_USD_PER_DIEM,
) -> EndowmentPlan:
    if usd <= 0:
        raise ValueError("endowment must be positive")
    if vvv_price_usd <= 0:
        raise ValueError("VVV price must be positive")
    vvv = usd / vvv_price_usd
    # Your own stake joins the active pool.
    share = vvv / (total_active_staked_vvv + vvv)
    diem = share * network_capacity_diem
    usd_day = diem * usd_per_diem
    return EndowmentPlan(
        usd_in=usd,
        vvv_price_usd=vvv_price_usd,
        vvv_acquired=vvv,
        total_active_staked_vvv=total_active_staked_vvv,
        network_capacity_diem=network_capacity_diem,
        stake_share=share,
        diem_per_day=diem,
        usd_inference_per_day=usd_day,
        usd_inference_per_year=usd_day * 365,
    )
