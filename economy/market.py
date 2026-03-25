"""Economy system: marketplace, trading, supply/demand pricing."""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class TradeOffer:
    seller_id: str
    item: str
    quantity: int
    price_per_unit: int  # in coins

    @property
    def total_price(self) -> int:
        return self.quantity * self.price_per_unit


@dataclass
class TradeRecord:
    tick: int
    buyer_id: str
    seller_id: str
    item: str
    quantity: int
    price_per_unit: int

    @property
    def total(self) -> int:
        return self.quantity * self.price_per_unit


class PriceEngine:
    """Supply/demand pricing — prices emerge from scarcity."""

    def __init__(self, base_prices: dict[str, int], elasticity: float = 0.1):
        self.base_prices = dict(base_prices)
        self.current_prices: dict[str, float] = {k: float(v) for k, v in base_prices.items()}
        self.supply: dict[str, int] = {k: 0 for k in base_prices}
        self.demand: dict[str, int] = {k: 0 for k in base_prices}
        self.elasticity = elasticity
        self.price_history: dict[str, list[float]] = {k: [float(v)] for k, v in base_prices.items()}

    def record_supply(self, item: str, quantity: int):
        self.supply[item] = self.supply.get(item, 0) + quantity

    def record_demand(self, item: str, quantity: int):
        self.demand[item] = self.demand.get(item, 0) + quantity

    def update_prices(self):
        """Adjust prices based on supply vs demand."""
        for item in self.current_prices:
            s = max(1, self.supply.get(item, 1))
            d = max(1, self.demand.get(item, 1))
            ratio = d / s
            # Price moves toward equilibrium
            target = self.base_prices[item] * ratio
            self.current_prices[item] += self.elasticity * (target - self.current_prices[item])
            # Floor price at 1
            self.current_prices[item] = max(1.0, self.current_prices[item])
            self.price_history[item].append(round(self.current_prices[item], 1))

        # Reset supply/demand counters for next period
        self.supply = {k: 0 for k in self.current_prices}
        self.demand = {k: 0 for k in self.current_prices}

    def get_price(self, item: str) -> int:
        return max(1, round(self.current_prices.get(item, 10)))

    def get_all_prices(self) -> dict[str, int]:
        return {k: self.get_price(k) for k in self.current_prices}


class Marketplace:
    """Centralized market where agents post and fill trade offers."""

    def __init__(self, price_engine: PriceEngine, seed: int = 42):
        self.price_engine = price_engine
        self.offers: list[TradeOffer] = []
        self.trade_history: list[TradeRecord] = []
        self._rng = random.Random(seed)
        self.total_volume: int = 0
        self.total_coins_traded: int = 0

    def post_offer(self, seller_id: str, item: str, quantity: int, price_per_unit: Optional[int] = None):
        """Seller posts an item for sale."""
        if price_per_unit is None:
            price_per_unit = self.price_engine.get_price(item)
        offer = TradeOffer(seller_id=seller_id, item=item, quantity=quantity, price_per_unit=price_per_unit)
        self.offers.append(offer)
        self.price_engine.record_supply(item, quantity)

    def find_offers(self, item: str, max_price: Optional[int] = None) -> list[TradeOffer]:
        """Find available offers for an item."""
        results = [o for o in self.offers if o.item == item and o.quantity > 0]
        if max_price is not None:
            results = [o for o in results if o.price_per_unit <= max_price]
        results.sort(key=lambda o: o.price_per_unit)
        return results

    def execute_trade(self, buyer_id: str, offer: TradeOffer, quantity: int, tick: int) -> Optional[TradeRecord]:
        """Execute a trade between buyer and an existing offer."""
        if offer not in self.offers or offer.quantity < quantity:
            return None

        actual_qty = min(quantity, offer.quantity)
        record = TradeRecord(
            tick=tick,
            buyer_id=buyer_id,
            seller_id=offer.seller_id,
            item=offer.item,
            quantity=actual_qty,
            price_per_unit=offer.price_per_unit,
        )
        offer.quantity -= actual_qty
        if offer.quantity <= 0:
            self.offers.remove(offer)

        self.trade_history.append(record)
        self.total_volume += actual_qty
        self.total_coins_traded += record.total
        self.price_engine.record_demand(offer.item, actual_qty)
        return record

    def clear_stale_offers(self, max_age: int, current_tick: int):
        """Remove offers that have been sitting too long."""
        # For simplicity, remove all offers with 0 quantity
        self.offers = [o for o in self.offers if o.quantity > 0]

    def get_stats(self) -> dict:
        return {
            "active_offers": len(self.offers),
            "total_trades": len(self.trade_history),
            "total_volume": self.total_volume,
            "total_coins_traded": self.total_coins_traded,
            "current_prices": self.price_engine.get_all_prices(),
        }


@dataclass
class Job:
    building_name: str
    position: tuple[int, int]
    wage: int
    skill_required: str
    worker_id: Optional[str] = None

    @property
    def is_vacant(self) -> bool:
        return self.worker_id is None


class JobBoard:
    """Tracks available jobs at buildings."""

    def __init__(self):
        self.jobs: list[Job] = []

    def post_job(self, building_name: str, position: tuple[int, int], wage: int, skill: str):
        job = Job(building_name=building_name, position=position, wage=wage, skill_required=skill)
        self.jobs.append(job)

    def find_jobs(self, skill: Optional[str] = None, near: Optional[tuple[int, int]] = None, radius: int = 10) -> list[Job]:
        results = [j for j in self.jobs if j.is_vacant]
        if skill:
            results = [j for j in results if j.skill_required == skill]
        if near:
            results = [j for j in results if abs(j.position[0] - near[0]) <= radius and abs(j.position[1] - near[1]) <= radius]
        results.sort(key=lambda j: j.wage, reverse=True)
        return results

    def hire(self, job: Job, worker_id: str) -> bool:
        if not job.is_vacant:
            return False
        job.worker_id = worker_id
        return True

    def quit(self, worker_id: str):
        for job in self.jobs:
            if job.worker_id == worker_id:
                job.worker_id = None

    def get_worker_job(self, worker_id: str) -> Optional[Job]:
        for job in self.jobs:
            if job.worker_id == worker_id:
                return job
        return None

    def vacant_count(self) -> int:
        return sum(1 for j in self.jobs if j.is_vacant)


class EconomySystem:
    """Top-level economy manager tying together market, prices, and jobs."""

    def __init__(self, config: dict, seed: int = 42):
        base_prices = config.get("starting_prices", {
            "food": 5, "wood": 8, "stone": 12, "tools": 20, "luxury": 30
        })
        elasticity = config.get("price_elasticity", 0.1)
        self.price_engine = PriceEngine(base_prices, elasticity)
        self.marketplace = Marketplace(self.price_engine, seed=seed)
        self.job_board = JobBoard()
        self.wage_base = config.get("wage_base", 10)
        self.tick_count = 0

    def tick(self):
        """Called each simulation tick to update economy."""
        self.tick_count += 1
        # Update prices every 12 ticks (half a day)
        if self.tick_count % 12 == 0:
            self.price_engine.update_prices()
        # Clear stale offers daily
        if self.tick_count % 24 == 0:
            self.marketplace.clear_stale_offers(max_age=24, current_tick=self.tick_count)

    def agent_sell(self, agent_id: str, item: str, quantity: int):
        """Agent posts item for sale at market price."""
        self.marketplace.post_offer(agent_id, item, quantity)

    def agent_buy(self, agent_id: str, item: str, quantity: int, max_price: int) -> Optional[TradeRecord]:
        """Agent tries to buy item from market."""
        offers = self.marketplace.find_offers(item, max_price=max_price)
        if not offers:
            return None
        return self.marketplace.execute_trade(agent_id, offers[0], quantity, self.tick_count)

    def agent_work(self, agent_id: str) -> int:
        """Agent works at their job, returns wage earned."""
        job = self.job_board.get_worker_job(agent_id)
        if job:
            return job.wage
        return 0

    def get_summary(self) -> dict:
        return {
            "prices": self.price_engine.get_all_prices(),
            "market": self.marketplace.get_stats(),
            "jobs": {
                "total": len(self.job_board.jobs),
                "vacant": self.job_board.vacant_count(),
            },
        }
