# Economy System — Complete Technical Blueprint

## Design Philosophy

The economy is NOT decorative. It is the primary driver of agent behavior. Every
resource is produced by labor, transported at cost, sold at market-discovered prices,
consumed to satisfy needs, and taxed by government. Scarcity is real. Inflation is
possible. Unemployment causes suffering. This is agent-based computational economics.

## Currency and Accounting

```python
# Single currency unit: "credits" (₵)
# All transactions are double-entry bookkeeping

@dataclass(frozen=True)
class Transaction:
    tx_id: str
    tick: int
    from_entity: str     # Agent ID or firm ID or "government" or "system"
    to_entity: str
    amount: float
    category: str        # "wage" | "purchase" | "rent" | "tax" | "investment" | "transfer"
    description: str
    item: str | None     # Resource name if purchase
    quantity: float | None

class Ledger:
    """Append-only transaction log. The source of truth for all money flows."""

    def __init__(self):
        self._transactions: list[Transaction] = []
        self._balances: dict[str, float] = {}

    def transfer(self, from_entity: str, to_entity: str, amount: float,
                 category: str, tick: int, description: str = "",
                 item: str | None = None, quantity: float | None = None) -> Transaction | None:
        """Execute a transfer. Returns None if insufficient funds (except system)."""
        if from_entity != "system" and self._balances.get(from_entity, 0) < amount:
            return None  # Insufficient funds

        tx = Transaction(
            tx_id=uuid(), tick=tick, from_entity=from_entity, to_entity=to_entity,
            amount=amount, category=category, description=description,
            item=item, quantity=quantity,
        )

        self._transactions.append(tx)
        if from_entity != "system":
            self._balances[from_entity] = self._balances.get(from_entity, 0) - amount
        self._balances[to_entity] = self._balances.get(to_entity, 0) + amount
        return tx

    def get_balance(self, entity_id: str) -> float:
        return self._balances.get(entity_id, 0)

    def get_history(self, entity_id: str, last_n: int = 50) -> list[Transaction]:
        return [t for t in self._transactions[-1000:]
                if t.from_entity == entity_id or t.to_entity == entity_id][-last_n:]
```

## Market System — Order Book

Markets discover prices through supply and demand. No admin-set prices.

```python
@dataclass(frozen=True)
class Order:
    order_id: str
    agent_id: str
    resource: str
    side: str            # "buy" | "sell"
    quantity: float
    price: float         # Price per unit
    tick_created: int
    ttl: int             # Expires after this many ticks

@dataclass(frozen=True)
class MarketState:
    resource: str
    buy_orders: tuple[Order, ...]   # Sorted by price descending (highest bid first)
    sell_orders: tuple[Order, ...]  # Sorted by price ascending (lowest ask first)
    last_trade_price: float
    volume_24h: float               # Last 2400 ticks (1 "day")
    price_history: tuple[float, ...]  # Last 100 trade prices

class OrderBookMarket:
    """Continuous double-auction market per resource."""

    def __init__(self):
        self.markets: dict[str, MarketState] = {}

    def place_order(self, order: Order) -> list[Transaction]:
        """Place a buy or sell order. Returns any immediate matches."""
        market = self._get_or_create_market(order.resource)
        transactions = []

        if order.side == "buy":
            # Match against sell orders (lowest price first)
            remaining_qty = order.quantity
            new_sells = list(market.sell_orders)

            for i, sell in enumerate(new_sells):
                if remaining_qty <= 0:
                    break
                if sell.price <= order.price:  # Match!
                    trade_qty = min(remaining_qty, sell.quantity)
                    trade_price = sell.price  # Maker's price

                    transactions.append(Transaction(
                        tx_id=uuid(), tick=order.tick_created,
                        from_entity=order.agent_id, to_entity=sell.agent_id,
                        amount=trade_price * trade_qty, category="purchase",
                        description=f"Buy {trade_qty} {order.resource} @ {trade_price}",
                        item=order.resource, quantity=trade_qty,
                    ))

                    remaining_qty -= trade_qty
                    remaining_sell = sell.quantity - trade_qty
                    if remaining_sell <= 0:
                        new_sells[i] = None  # Fully filled
                    else:
                        new_sells[i] = sell._replace(quantity=remaining_sell)

            # Remove filled sell orders
            new_sells = tuple(s for s in new_sells if s is not None)

            # Add remaining buy quantity as resting order
            if remaining_qty > 0:
                new_buys = tuple(sorted(
                    list(market.buy_orders) + [order._replace(quantity=remaining_qty)],
                    key=lambda o: -o.price
                ))
            else:
                new_buys = market.buy_orders

            # Update market state
            last_price = transactions[-1].amount / transactions[-1].quantity if transactions else market.last_trade_price
            self.markets[order.resource] = market._replace(
                buy_orders=new_buys,
                sell_orders=new_sells,
                last_trade_price=last_price,
                price_history=(*market.price_history[-99:], last_price) if transactions else market.price_history,
            )

        elif order.side == "sell":
            # Mirror logic for sell orders matching against buys
            remaining_qty = order.quantity
            new_buys = list(market.buy_orders)

            for i, buy in enumerate(new_buys):
                if remaining_qty <= 0:
                    break
                if buy.price >= order.price:
                    trade_qty = min(remaining_qty, buy.quantity)
                    trade_price = buy.price

                    transactions.append(Transaction(
                        tx_id=uuid(), tick=order.tick_created,
                        from_entity=buy.agent_id, to_entity=order.agent_id,
                        amount=trade_price * trade_qty, category="purchase",
                        description=f"Sell {trade_qty} {order.resource} @ {trade_price}",
                        item=order.resource, quantity=trade_qty,
                    ))

                    remaining_qty -= trade_qty
                    if buy.quantity - trade_qty <= 0:
                        new_buys[i] = None
                    else:
                        new_buys[i] = buy._replace(quantity=buy.quantity - trade_qty)

            new_buys = tuple(b for b in new_buys if b is not None)

            if remaining_qty > 0:
                new_sells = tuple(sorted(
                    list(market.sell_orders) + [order._replace(quantity=remaining_qty)],
                    key=lambda o: o.price
                ))
            else:
                new_sells = market.sell_orders

            last_price = transactions[-1].amount / transactions[-1].quantity if transactions else market.last_trade_price
            self.markets[order.resource] = market._replace(
                buy_orders=new_buys,
                sell_orders=new_sells,
                last_trade_price=last_price,
                price_history=(*market.price_history[-99:], last_price) if transactions else market.price_history,
            )

        return transactions

    def get_price(self, resource: str) -> float:
        """Current market price (last trade or midpoint of spread)."""
        market = self.markets.get(resource)
        if not market:
            return RESOURCES.get(resource, {}).get("base_value", 1.0)
        if market.last_trade_price > 0:
            return market.last_trade_price
        if market.buy_orders and market.sell_orders:
            return (market.buy_orders[0].price + market.sell_orders[0].price) / 2
        return RESOURCES.get(resource, {}).get("base_value", 1.0)

    def expire_old_orders(self, current_tick: int) -> None:
        """Remove expired orders from all markets."""
        for resource, market in self.markets.items():
            new_buys = tuple(o for o in market.buy_orders if current_tick - o.tick_created < o.ttl)
            new_sells = tuple(o for o in market.sell_orders if current_tick - o.tick_created < o.ttl)
            self.markets[resource] = market._replace(buy_orders=new_buys, sell_orders=new_sells)

    def _get_or_create_market(self, resource: str) -> MarketState:
        if resource not in self.markets:
            base_price = RESOURCES.get(resource, {}).get("base_value", 1.0)
            self.markets[resource] = MarketState(
                resource=resource, buy_orders=(), sell_orders=(),
                last_trade_price=base_price, volume_24h=0, price_history=(base_price,),
            )
        return self.markets[resource]
```

## Labor Market

```python
@dataclass(frozen=True)
class JobPosting:
    posting_id: str
    firm_id: str
    profession: str
    wage: float              # Per tick
    skill_requirement: float # Minimum skill level
    tick_posted: int
    filled: bool

@dataclass(frozen=True)
class Firm:
    firm_id: str
    name: str
    owner_id: str            # Agent who owns this firm
    type: str                # "farm" | "workshop" | "factory" | "shop" | "service"
    building_id: str
    employees: tuple[str, ...]
    cash: float
    inventory: dict[str, float]
    wage_budget: float       # Total wages per tick
    revenue_history: tuple[float, ...]  # Last 100 ticks
    expense_history: tuple[float, ...]
    is_hiring: bool
    job_postings: tuple[JobPosting, ...]
    products: tuple[str, ...]  # What this firm produces

class LaborMarket:
    """Matches workers to jobs based on skills, wages, and availability."""

    def __init__(self):
        self.postings: list[JobPosting] = []

    def post_job(self, firm: Firm, profession: str, wage: float,
                 skill_req: float, tick: int) -> JobPosting:
        posting = JobPosting(
            posting_id=uuid(), firm_id=firm.firm_id,
            profession=profession, wage=wage,
            skill_requirement=skill_req, tick_posted=tick, filled=False,
        )
        self.postings.append(posting)
        return posting

    def find_jobs(self, agent: Agent) -> list[JobPosting]:
        """Find suitable unfilled jobs for an agent."""
        suitable = []
        for posting in self.postings:
            if posting.filled:
                continue
            skill_level = agent.skills.skills.get(posting.profession, 0)
            if skill_level >= posting.skill_requirement:
                suitable.append(posting)
        # Sort by wage descending
        return sorted(suitable, key=lambda p: -p.wage)

    def accept_job(self, agent: Agent, posting: JobPosting,
                   ledger: Ledger) -> bool:
        """Agent accepts a job posting."""
        if posting.filled:
            return False
        posting = posting._replace(filled=True)
        # Update agent's employment
        return True

    def calculate_market_wage(self, profession: str) -> float:
        """Current market wage for a profession based on supply/demand."""
        active = [p for p in self.postings if p.profession == profession and not p.filled]
        if not active:
            return 0.5  # Default
        return sum(p.wage for p in active) / len(active)

    def get_unemployment_rate(self, agents: list[Agent]) -> float:
        """Percentage of adult agents without employment."""
        adults = [a for a in agents if a.biology.lifecycle_stage == "adult"]
        if not adults:
            return 0
        unemployed = [a for a in adults if a.economy.employer_id is None]
        return len(unemployed) / len(adults)
```

## Production System

```python
class ProductionSystem:
    """Firms produce goods using labor + raw materials."""

    def produce(self, firm: Firm, workers: list[Agent], tick: int,
                world: WorldState) -> dict[str, float]:
        """Run one tick of production for a firm."""
        building = world.get_building(firm.building_id)
        if not building or not building.is_operational:
            return {}

        spec = BUILDING_TYPES.get(building.type, {})
        recipes = spec.get("recipes", [])
        output_direct = spec.get("output", {})

        produced = {}

        # Direct output (farms, power plants)
        for resource, rate in output_direct.items():
            total_skill = sum(
                w.skills.skills.get(self._get_profession_for_building(building.type), 0.1)
                for w in workers
            )
            amount = rate * total_skill * len(workers)
            produced[resource] = amount

        # Recipe-based production (workshops, factories)
        production_mult = spec.get("production_multiplier", 1.0)
        for recipe_name in recipes:
            recipe = RESOURCES.get(recipe_name, {}).get("recipe", {})
            if not recipe:
                continue

            # Check if firm has all ingredients
            max_batches = float('inf')
            for ingredient, amount_needed in recipe.items():
                available = firm.inventory.get(ingredient, 0)
                batches = available / amount_needed if amount_needed > 0 else float('inf')
                max_batches = min(max_batches, batches)

            if max_batches <= 0 or max_batches == float('inf'):
                continue

            # Produce limited by workers and ingredients
            worker_capacity = sum(
                w.skills.skills.get(self._get_profession_for_building(building.type), 0.1)
                for w in workers
            ) * production_mult

            batches = min(max_batches, worker_capacity)
            produced[recipe_name] = batches

            # Consume ingredients (returns new firm inventory)
            # This happens at the economic update step

        return produced

    def _get_profession_for_building(self, building_type: str) -> str:
        mapping = {
            "farm": "farming", "workshop": "crafting", "factory": "manufacturing",
            "power_plant": "engineering", "hospital": "medicine",
            "school": "teaching", "market": "trading",
        }
        return mapping.get(building_type, "general")
```

## Economic Indicators (computed every 100 ticks)

```python
@dataclass(frozen=True)
class EconomicIndicators:
    tick: int
    gdp: float                    # Sum of all production value
    unemployment_rate: float
    inflation_rate: float         # Price change vs 100 ticks ago
    average_wage: float
    median_wealth: float
    gini_coefficient: float       # Inequality measure (0=equal, 1=max inequality)
    poverty_rate: float           # % below poverty line
    poverty_line: float           # Adaptive: 50% of median income
    total_money_supply: float
    trade_volume: float
    housing_occupancy: float      # % of houses occupied
    food_price_index: float       # Weighted food prices vs baseline
    active_firms: int
    bankruptcies_this_period: int

def compute_indicators(world: WorldState, ledger: Ledger, tick: int) -> EconomicIndicators:
    agents = world.get_all_agents()
    adults = [a for a in agents if a.biology.lifecycle_stage in ("adult", "elder")]
    wealths = sorted([a.economy.cash for a in adults])
    wages = [a.economy.wage for a in adults if a.economy.wage > 0]

    # Gini coefficient
    n = len(wealths)
    if n == 0:
        gini = 0
    else:
        cumulative = sum((2 * (i + 1) - n - 1) * w for i, w in enumerate(wealths))
        gini = cumulative / (n * sum(wealths)) if sum(wealths) > 0 else 0

    median_income = wages[len(wages) // 2] if wages else 0
    poverty_line = median_income * 0.5

    return EconomicIndicators(
        tick=tick,
        gdp=sum(t.amount for t in ledger.get_recent_transactions(100) if t.category == "purchase"),
        unemployment_rate=len([a for a in adults if not a.economy.employer_id]) / max(len(adults), 1),
        inflation_rate=0,  # Computed from price history
        average_wage=sum(wages) / max(len(wages), 1),
        median_wealth=wealths[len(wealths) // 2] if wealths else 0,
        gini_coefficient=max(0, min(1, gini)),
        poverty_rate=len([a for a in adults if a.economy.cash < poverty_line]) / max(len(adults), 1),
        poverty_line=poverty_line,
        total_money_supply=sum(a.economy.cash for a in agents),
        trade_volume=0,
        housing_occupancy=0,
        food_price_index=0,
        active_firms=len(world.get_all_firms()),
        bankruptcies_this_period=0,
    )
```
