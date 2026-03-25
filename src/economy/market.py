"""Order-book market -- continuous double-auction price discovery."""

from __future__ import annotations

import uuid as _uuid
from dataclasses import dataclass, replace

from src.economy.ledger import Transaction
from src.world.resources import RESOURCES


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class Order:
    """A single buy or sell order on the market."""

    order_id: str
    agent_id: str
    resource: str
    side: str              # "buy" | "sell"
    quantity: float
    price: float           # price per unit
    tick_created: int
    ttl: int = 500         # expires after this many ticks


@dataclass(frozen=True, slots=True)
class MarketState:
    """Snapshot of one resource's order book."""

    resource: str
    buy_orders: tuple[Order, ...] = ()     # sorted price descending
    sell_orders: tuple[Order, ...] = ()    # sorted price ascending
    last_trade_price: float = 0.0
    volume_24h: float = 0.0                # last 2400 ticks
    price_history: tuple[float, ...] = ()  # last 100 trade prices


# ---------------------------------------------------------------------------
# OrderBookMarket
# ---------------------------------------------------------------------------

class OrderBookMarket:
    """Continuous double-auction market for every tradeable resource."""

    def __init__(self) -> None:
        self.markets: dict[str, MarketState] = {}

    # -- Order placement & matching -----------------------------------------

    def place_order(self, order: Order) -> list[Transaction]:
        """Place a buy or sell order. Returns immediate match transactions."""
        market = self._get_or_create_market(order.resource)

        if order.side == "buy":
            return self._match_buy(order, market)
        elif order.side == "sell":
            return self._match_sell(order, market)
        else:
            raise ValueError(f"Invalid order side: {order.side!r}")

    # -- Price query --------------------------------------------------------

    def get_price(self, resource: str) -> float:
        """Current market price (last trade, midpoint, or base value)."""
        market = self.markets.get(resource)
        if market is None:
            return RESOURCES.get(resource, {}).get("base_value", 1.0)
        if market.last_trade_price > 0:
            return market.last_trade_price
        if market.buy_orders and market.sell_orders:
            return (market.buy_orders[0].price + market.sell_orders[0].price) / 2
        return RESOURCES.get(resource, {}).get("base_value", 1.0)

    # -- Expiry -------------------------------------------------------------

    def expire_old_orders(self, current_tick: int) -> None:
        """Remove orders whose TTL has elapsed."""
        for resource, market in list(self.markets.items()):
            new_buys = tuple(
                o for o in market.buy_orders
                if current_tick - o.tick_created < o.ttl
            )
            new_sells = tuple(
                o for o in market.sell_orders
                if current_tick - o.tick_created < o.ttl
            )
            self.markets[resource] = replace(
                market, buy_orders=new_buys, sell_orders=new_sells,
            )

    # -- Internal matching --------------------------------------------------

    def _match_buy(self, order: Order, market: MarketState) -> list[Transaction]:
        transactions: list[Transaction] = []
        remaining_qty = order.quantity
        new_sells = list(market.sell_orders)

        for i, sell in enumerate(new_sells):
            if remaining_qty <= 0:
                break
            if sell.price <= order.price:
                trade_qty = min(remaining_qty, sell.quantity)
                trade_price = sell.price  # maker's price

                transactions.append(Transaction(
                    tx_id=str(_uuid.uuid4()),
                    tick=order.tick_created,
                    from_entity=order.agent_id,
                    to_entity=sell.agent_id,
                    amount=trade_price * trade_qty,
                    category="purchase",
                    description=f"Buy {trade_qty} {order.resource} @ {trade_price}",
                    item=order.resource,
                    quantity=trade_qty,
                ))

                remaining_qty -= trade_qty
                leftover = sell.quantity - trade_qty
                if leftover <= 0:
                    new_sells[i] = None  # type: ignore[assignment]
                else:
                    new_sells[i] = replace(sell, quantity=leftover)

        clean_sells = tuple(s for s in new_sells if s is not None)

        if remaining_qty > 0:
            resting = replace(order, quantity=remaining_qty)
            new_buys = tuple(sorted(
                list(market.buy_orders) + [resting],
                key=lambda o: -o.price,
            ))
        else:
            new_buys = market.buy_orders

        last_price = (
            transactions[-1].amount / transactions[-1].quantity
            if transactions and transactions[-1].quantity
            else market.last_trade_price
        )
        new_history = (
            (*market.price_history[-99:], last_price) if transactions
            else market.price_history
        )

        self.markets[order.resource] = replace(
            market,
            buy_orders=new_buys,
            sell_orders=clean_sells,
            last_trade_price=last_price,
            price_history=new_history,
        )
        return transactions

    def _match_sell(self, order: Order, market: MarketState) -> list[Transaction]:
        transactions: list[Transaction] = []
        remaining_qty = order.quantity
        new_buys = list(market.buy_orders)

        for i, buy in enumerate(new_buys):
            if remaining_qty <= 0:
                break
            if buy.price >= order.price:
                trade_qty = min(remaining_qty, buy.quantity)
                trade_price = buy.price  # maker's price

                transactions.append(Transaction(
                    tx_id=str(_uuid.uuid4()),
                    tick=order.tick_created,
                    from_entity=buy.agent_id,
                    to_entity=order.agent_id,
                    amount=trade_price * trade_qty,
                    category="purchase",
                    description=f"Sell {trade_qty} {order.resource} @ {trade_price}",
                    item=order.resource,
                    quantity=trade_qty,
                ))

                remaining_qty -= trade_qty
                leftover = buy.quantity - trade_qty
                if leftover <= 0:
                    new_buys[i] = None  # type: ignore[assignment]
                else:
                    new_buys[i] = replace(buy, quantity=leftover)

        clean_buys = tuple(b for b in new_buys if b is not None)

        if remaining_qty > 0:
            resting = replace(order, quantity=remaining_qty)
            new_sells = tuple(sorted(
                list(market.sell_orders) + [resting],
                key=lambda o: o.price,
            ))
        else:
            new_sells = market.sell_orders

        last_price = (
            transactions[-1].amount / transactions[-1].quantity
            if transactions and transactions[-1].quantity
            else market.last_trade_price
        )
        new_history = (
            (*market.price_history[-99:], last_price) if transactions
            else market.price_history
        )

        self.markets[order.resource] = replace(
            market,
            buy_orders=clean_buys,
            sell_orders=new_sells,
            last_trade_price=last_price,
            price_history=new_history,
        )
        return transactions

    # -- Helpers ------------------------------------------------------------

    def _get_or_create_market(self, resource: str) -> MarketState:
        if resource not in self.markets:
            base_price = RESOURCES.get(resource, {}).get("base_value", 1.0)
            self.markets[resource] = MarketState(
                resource=resource,
                buy_orders=(),
                sell_orders=(),
                last_trade_price=base_price,
                volume_24h=0.0,
                price_history=(base_price,),
            )
        return self.markets[resource]
