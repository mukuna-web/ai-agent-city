"""Economic indicators -- aggregate statistics computed periodically."""

from __future__ import annotations

from dataclasses import dataclass

from src.economy.ledger import Ledger


@dataclass(frozen=True, slots=True)
class EconomicIndicators:
    """A snapshot of macro-economic health at a given tick."""

    tick: int
    gdp: float
    unemployment_rate: float
    inflation_rate: float
    average_wage: float
    median_wealth: float
    gini_coefficient: float
    poverty_rate: float
    poverty_line: float
    total_money_supply: float
    active_firms: int
    trade_volume: float = 0.0
    housing_occupancy: float = 0.0
    food_price_index: float = 0.0
    bankruptcies_this_period: int = 0


# ---------------------------------------------------------------------------
# Gini coefficient
# ---------------------------------------------------------------------------

def _gini(sorted_values: list[float]) -> float:
    """Compute the Gini coefficient from a **sorted** list of non-negative values."""
    n = len(sorted_values)
    if n == 0:
        return 0.0
    total = sum(sorted_values)
    if total <= 0:
        return 0.0
    cumulative = sum(
        (2 * (i + 1) - n - 1) * w for i, w in enumerate(sorted_values)
    )
    return max(0.0, min(1.0, cumulative / (n * total)))


# ---------------------------------------------------------------------------
# Compute
# ---------------------------------------------------------------------------

def compute_indicators(
    *,
    tick: int,
    ledger: Ledger,
    agent_cash: list[float],
    agent_wages: list[float],
    agent_employed: list[bool],
    active_firms: int,
    previous_prices: dict[str, float] | None = None,
    current_prices: dict[str, float] | None = None,
) -> EconomicIndicators:
    """Compute aggregate economic indicators.

    Parameters
    ----------
    tick:
        Current simulation tick.
    ledger:
        The global ledger (used for GDP / money supply).
    agent_cash:
        List of cash holdings for all adult agents.
    agent_wages:
        List of per-tick wages for all employed adult agents (>0 only).
    agent_employed:
        Boolean list parallel to *agent_cash* -- ``True`` if employed.
    active_firms:
        Count of operational firms.
    previous_prices / current_prices:
        Price dicts for computing inflation (resource -> price).
    """
    # Wages
    nonzero_wages = [w for w in agent_wages if w > 0]
    average_wage = sum(nonzero_wages) / len(nonzero_wages) if nonzero_wages else 0.0

    # Wealth distribution
    sorted_cash = sorted(agent_cash)
    n = len(sorted_cash)
    median_wealth = sorted_cash[n // 2] if n > 0 else 0.0
    gini = _gini(sorted_cash)

    # Poverty
    median_income = nonzero_wages[len(nonzero_wages) // 2] if nonzero_wages else 0.0
    poverty_line = median_income * 0.5
    poor_count = sum(1 for c in agent_cash if c < poverty_line)
    poverty_rate = poor_count / max(n, 1)

    # Unemployment
    total_adults = len(agent_employed)
    unemployed = sum(1 for e in agent_employed if not e)
    unemployment_rate = unemployed / max(total_adults, 1)

    # GDP: sum of purchase transactions in the last 100 ticks
    recent = ledger.get_recent_transactions(last_n=200)
    gdp = sum(t.amount for t in recent if t.category == "purchase" and t.tick > tick - 100)

    # Inflation
    inflation_rate = 0.0
    if previous_prices and current_prices:
        changes: list[float] = []
        for res, old_p in previous_prices.items():
            new_p = current_prices.get(res, old_p)
            if old_p > 0:
                changes.append((new_p - old_p) / old_p)
        if changes:
            inflation_rate = sum(changes) / len(changes)

    return EconomicIndicators(
        tick=tick,
        gdp=gdp,
        unemployment_rate=unemployment_rate,
        inflation_rate=inflation_rate,
        average_wage=average_wage,
        median_wealth=median_wealth,
        gini_coefficient=gini,
        poverty_rate=poverty_rate,
        poverty_line=poverty_line,
        total_money_supply=ledger.total_money_supply,
        active_firms=active_firms,
    )
