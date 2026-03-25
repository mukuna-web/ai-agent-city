"""Append-only double-entry ledger for all money flows."""

from __future__ import annotations

import uuid as _uuid
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Transaction:
    """An immutable record of a single monetary transfer."""

    tx_id: str
    tick: int
    from_entity: str
    to_entity: str
    amount: float
    category: str          # "wage" | "purchase" | "rent" | "tax" | "investment" | "transfer"
    description: str = ""
    item: str | None = None
    quantity: float | None = None


class Ledger:
    """Append-only transaction log.

    The ledger is the single source of truth for all money flows.  Balances
    are cached for O(1) lookups but can always be recomputed from the log.
    """

    def __init__(self) -> None:
        self._transactions: list[Transaction] = []
        self._balances: dict[str, float] = {}

    # -- Core operations ----------------------------------------------------

    def transfer(
        self,
        from_entity: str,
        to_entity: str,
        amount: float,
        category: str,
        tick: int,
        description: str = "",
        item: str | None = None,
        quantity: float | None = None,
    ) -> Transaction | None:
        """Execute a transfer.

        Returns ``None`` if the sender has insufficient funds (the special
        entity ``"system"`` has unlimited funds).
        """
        if amount <= 0:
            return None

        if from_entity != "system" and self._balances.get(from_entity, 0.0) < amount:
            return None

        tx = Transaction(
            tx_id=str(_uuid.uuid4()),
            tick=tick,
            from_entity=from_entity,
            to_entity=to_entity,
            amount=amount,
            category=category,
            description=description,
            item=item,
            quantity=quantity,
        )

        self._transactions.append(tx)

        if from_entity != "system":
            self._balances[from_entity] = self._balances.get(from_entity, 0.0) - amount
        self._balances[to_entity] = self._balances.get(to_entity, 0.0) + amount

        return tx

    # -- Query helpers ------------------------------------------------------

    def get_balance(self, entity_id: str) -> float:
        return self._balances.get(entity_id, 0.0)

    def set_balance(self, entity_id: str, amount: float) -> None:
        """Force-set a balance (used for system initialisation)."""
        self._balances[entity_id] = amount

    def get_history(self, entity_id: str, last_n: int = 50) -> list[Transaction]:
        """Return the last *last_n* transactions involving *entity_id*."""
        relevant = [
            t for t in self._transactions[-1000:]
            if t.from_entity == entity_id or t.to_entity == entity_id
        ]
        return relevant[-last_n:]

    def get_recent_transactions(self, last_n: int = 100) -> list[Transaction]:
        """Return the last *last_n* transactions globally."""
        return list(self._transactions[-last_n:])

    @property
    def total_money_supply(self) -> float:
        """Sum of all positive balances (money in circulation)."""
        return sum(b for b in self._balances.values() if b > 0)

    @property
    def transaction_count(self) -> int:
        return len(self._transactions)
