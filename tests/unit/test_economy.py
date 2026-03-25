"""Unit tests for the economy module."""

from __future__ import annotations

import uuid

import pytest

from src.economy.indicators import EconomicIndicators, compute_indicators
from src.economy.labor import Firm, JobPosting, LaborMarket
from src.economy.ledger import Ledger, Transaction
from src.economy.market import Order, OrderBookMarket


# ===================================================================
# Fixtures
# ===================================================================

@pytest.fixture
def ledger() -> Ledger:
    return Ledger()


@pytest.fixture
def market() -> OrderBookMarket:
    return OrderBookMarket()


@pytest.fixture
def labor_market() -> LaborMarket:
    return LaborMarket()


@pytest.fixture
def sample_firm() -> Firm:
    return Firm(
        firm_id="firm-1",
        name="Test Workshop",
        owner_id="agent-owner",
        type="workshop",
        building_id="bld-1",
        employees=("agent-w1", "agent-w2"),
        cash=1000.0,
        inventory={"iron": 50.0, "timber": 30.0},
        wage_budget=10.0,
        is_hiring=True,
        products=("tools",),
    )


# ===================================================================
# Ledger tests
# ===================================================================

class TestLedger:
    def test_ledger_transfer(self, ledger: Ledger) -> None:
        """A valid transfer debits the sender and credits the receiver."""
        # Seed balance via system transfer
        ledger.transfer("system", "alice", 100.0, "transfer", tick=0)
        assert ledger.get_balance("alice") == 100.0

        # alice -> bob
        tx = ledger.transfer("alice", "bob", 40.0, "purchase", tick=1, item="bread", quantity=10)
        assert tx is not None
        assert isinstance(tx, Transaction)
        assert tx.amount == 40.0
        assert tx.from_entity == "alice"
        assert tx.to_entity == "bob"
        assert ledger.get_balance("alice") == pytest.approx(60.0)
        assert ledger.get_balance("bob") == pytest.approx(40.0)

    def test_ledger_insufficient_funds(self, ledger: Ledger) -> None:
        """A transfer returns None when the sender lacks funds."""
        ledger.transfer("system", "alice", 10.0, "transfer", tick=0)
        tx = ledger.transfer("alice", "bob", 50.0, "purchase", tick=1)
        assert tx is None
        # Balances unchanged
        assert ledger.get_balance("alice") == pytest.approx(10.0)
        assert ledger.get_balance("bob") == pytest.approx(0.0)

    def test_ledger_system_unlimited(self, ledger: Ledger) -> None:
        """The 'system' entity can always send money (money creation)."""
        tx = ledger.transfer("system", "alice", 1_000_000.0, "transfer", tick=0)
        assert tx is not None
        assert ledger.get_balance("alice") == pytest.approx(1_000_000.0)

    def test_ledger_history(self, ledger: Ledger) -> None:
        """get_history returns recent transactions for an entity."""
        ledger.transfer("system", "alice", 100.0, "transfer", tick=0)
        ledger.transfer("alice", "bob", 25.0, "purchase", tick=1)
        ledger.transfer("alice", "carol", 15.0, "wage", tick=2)

        history = ledger.get_history("alice", last_n=10)
        assert len(history) == 3
        assert all(
            t.from_entity == "alice" or t.to_entity == "alice" for t in history
        )

    def test_ledger_zero_or_negative_amount(self, ledger: Ledger) -> None:
        """Transfers of zero or negative amount are rejected."""
        ledger.transfer("system", "alice", 100.0, "transfer", tick=0)
        assert ledger.transfer("alice", "bob", 0.0, "transfer", tick=1) is None
        assert ledger.transfer("alice", "bob", -5.0, "transfer", tick=2) is None
        assert ledger.get_balance("alice") == pytest.approx(100.0)


# ===================================================================
# Market tests
# ===================================================================

class TestOrderBookMarket:
    def test_market_order_matching(self, market: OrderBookMarket) -> None:
        """A buy order matching an existing sell order produces a transaction."""
        sell = Order(
            order_id=str(uuid.uuid4()),
            agent_id="seller",
            resource="wheat",
            side="sell",
            quantity=10.0,
            price=2.0,
            tick_created=0,
        )
        market.place_order(sell)

        buy = Order(
            order_id=str(uuid.uuid4()),
            agent_id="buyer",
            resource="wheat",
            side="buy",
            quantity=5.0,
            price=2.5,  # willing to pay up to 2.5
            tick_created=1,
        )
        txns = market.place_order(buy)

        assert len(txns) == 1
        tx = txns[0]
        assert tx.from_entity == "buyer"
        assert tx.to_entity == "seller"
        assert tx.quantity == pytest.approx(5.0)
        assert tx.amount == pytest.approx(10.0)  # 5 units * 2.0 (seller's price)

        # Remaining sell order should have 5 units left
        state = market.markets["wheat"]
        assert len(state.sell_orders) == 1
        assert state.sell_orders[0].quantity == pytest.approx(5.0)
        # No resting buy orders
        assert len(state.buy_orders) == 0

    def test_market_price_discovery(self, market: OrderBookMarket) -> None:
        """After trades, get_price reflects the last trade price."""
        # Initial price should be base value
        assert market.get_price("wheat") == pytest.approx(1.0)

        sell = Order(
            order_id=str(uuid.uuid4()),
            agent_id="seller",
            resource="wheat",
            side="sell",
            quantity=20.0,
            price=3.0,
            tick_created=0,
        )
        market.place_order(sell)

        buy = Order(
            order_id=str(uuid.uuid4()),
            agent_id="buyer",
            resource="wheat",
            side="buy",
            quantity=10.0,
            price=3.0,
            tick_created=1,
        )
        market.place_order(buy)

        assert market.get_price("wheat") == pytest.approx(3.0)
        state = market.markets["wheat"]
        assert len(state.price_history) >= 2  # base + trade

    def test_market_no_match_resting(self, market: OrderBookMarket) -> None:
        """Orders that don't cross the spread remain as resting orders."""
        sell = Order(
            order_id=str(uuid.uuid4()),
            agent_id="seller",
            resource="iron",
            side="sell",
            quantity=5.0,
            price=10.0,
            tick_created=0,
        )
        buy = Order(
            order_id=str(uuid.uuid4()),
            agent_id="buyer",
            resource="iron",
            side="buy",
            quantity=5.0,
            price=8.0,  # below the ask
            tick_created=1,
        )
        market.place_order(sell)
        txns = market.place_order(buy)
        assert len(txns) == 0

        state = market.markets["iron"]
        assert len(state.buy_orders) == 1
        assert len(state.sell_orders) == 1

    def test_market_expire_old_orders(self, market: OrderBookMarket) -> None:
        """Orders past their TTL are removed by expire_old_orders."""
        order = Order(
            order_id=str(uuid.uuid4()),
            agent_id="seller",
            resource="tools",
            side="sell",
            quantity=3.0,
            price=15.0,
            tick_created=0,
            ttl=100,
        )
        market.place_order(order)
        assert len(market.markets["tools"].sell_orders) == 1

        market.expire_old_orders(current_tick=200)
        assert len(market.markets["tools"].sell_orders) == 0

    def test_market_sell_matches_buy(self, market: OrderBookMarket) -> None:
        """A sell order matching an existing buy order produces a transaction."""
        buy = Order(
            order_id=str(uuid.uuid4()),
            agent_id="buyer",
            resource="bread",
            side="buy",
            quantity=8.0,
            price=5.0,
            tick_created=0,
        )
        market.place_order(buy)

        sell = Order(
            order_id=str(uuid.uuid4()),
            agent_id="seller",
            resource="bread",
            side="sell",
            quantity=3.0,
            price=4.0,
            tick_created=1,
        )
        txns = market.place_order(sell)

        assert len(txns) == 1
        tx = txns[0]
        assert tx.from_entity == "buyer"
        assert tx.to_entity == "seller"
        assert tx.quantity == pytest.approx(3.0)
        assert tx.amount == pytest.approx(15.0)  # 3 * 5.0 (buyer's price = maker)


# ===================================================================
# Labor market tests
# ===================================================================

class TestLaborMarket:
    def test_labor_market_wage(
        self, labor_market: LaborMarket, sample_firm: Firm,
    ) -> None:
        """calculate_market_wage returns the average wage for a profession."""
        labor_market.post_job(sample_firm, "crafting", wage=2.0, skill_req=0.1, tick=0)
        labor_market.post_job(sample_firm, "crafting", wage=4.0, skill_req=0.3, tick=0)
        labor_market.post_job(sample_firm, "farming", wage=1.5, skill_req=0.0, tick=0)

        assert labor_market.calculate_market_wage("crafting") == pytest.approx(3.0)
        assert labor_market.calculate_market_wage("farming") == pytest.approx(1.5)
        # Unknown profession falls back to 0.5
        assert labor_market.calculate_market_wage("unknown") == pytest.approx(0.5)

    def test_find_jobs_skill_filter(
        self, labor_market: LaborMarket, sample_firm: Firm,
    ) -> None:
        """find_jobs only returns postings the agent qualifies for."""
        labor_market.post_job(sample_firm, "crafting", wage=3.0, skill_req=0.5, tick=0)
        labor_market.post_job(sample_firm, "crafting", wage=5.0, skill_req=0.9, tick=0)
        labor_market.post_job(sample_firm, "farming", wage=1.0, skill_req=0.0, tick=0)

        agent_skills = {"crafting": 0.6, "farming": 0.3}
        jobs = labor_market.find_jobs(agent_skills)

        # Should qualify for crafting@0.5 and farming@0.0, not crafting@0.9
        assert len(jobs) == 2
        assert jobs[0].wage == pytest.approx(3.0)  # highest qualifying wage first
        assert jobs[1].wage == pytest.approx(1.0)

    def test_fill_posting(
        self, labor_market: LaborMarket, sample_firm: Firm,
    ) -> None:
        """fill_posting marks a posting as filled and excludes it from searches."""
        posting = labor_market.post_job(sample_firm, "crafting", wage=2.0, skill_req=0.0, tick=0)
        assert labor_market.fill_posting(posting.posting_id) is True

        jobs = labor_market.find_jobs({"crafting": 1.0})
        assert len(jobs) == 0

    def test_unemployment_rate(self, labor_market: LaborMarket) -> None:
        """get_unemployment_rate computes correctly."""
        agents = [
            {"lifecycle_stage": "adult", "employer_id": "firm-1"},
            {"lifecycle_stage": "adult", "employer_id": None},
            {"lifecycle_stage": "adult", "employer_id": "firm-2"},
            {"lifecycle_stage": "child", "employer_id": None},  # excluded
        ]
        rate = labor_market.get_unemployment_rate(agents)
        # 1 unemployed out of 3 adults = 33.3%
        assert rate == pytest.approx(1 / 3)


# ===================================================================
# Indicators test
# ===================================================================

class TestEconomicIndicators:
    def test_compute_basic_indicators(self, ledger: Ledger) -> None:
        """compute_indicators returns a well-formed snapshot."""
        # Seed some transactions
        ledger.transfer("system", "a1", 200.0, "transfer", tick=0)
        ledger.transfer("system", "a2", 50.0, "transfer", tick=0)
        ledger.transfer("a1", "a2", 30.0, "purchase", tick=5, item="bread", quantity=10)

        ind = compute_indicators(
            tick=10,
            ledger=ledger,
            agent_cash=[170.0, 80.0],
            agent_wages=[5.0, 0.0],
            agent_employed=[True, False],
            active_firms=1,
        )

        assert isinstance(ind, EconomicIndicators)
        assert ind.tick == 10
        assert ind.unemployment_rate == pytest.approx(0.5)
        assert ind.average_wage == pytest.approx(5.0)
        assert ind.median_wealth == pytest.approx(170.0)  # sorted [170, 80] -> index 1
        assert ind.active_firms == 1
        assert ind.gini_coefficient >= 0.0
        assert ind.gini_coefficient <= 1.0
        assert ind.total_money_supply > 0
