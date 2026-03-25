"""Labor market -- job postings, matching, and wage discovery."""

from __future__ import annotations

import uuid as _uuid
from dataclasses import dataclass, replace


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class JobPosting:
    """A single job listing from a firm."""

    posting_id: str
    firm_id: str
    profession: str
    wage: float              # per tick
    skill_requirement: float # minimum skill level 0-1
    tick_posted: int
    filled: bool = False


@dataclass(frozen=True, slots=True)
class Firm:
    """An immutable snapshot of a firm (business entity)."""

    firm_id: str
    name: str
    owner_id: str
    type: str                # "farm" | "workshop" | "factory" | "shop" | "service"
    building_id: str
    employees: tuple[str, ...] = ()
    cash: float = 0.0
    inventory: dict[str, float] = None  # type: ignore[assignment]
    wage_budget: float = 0.0
    revenue_history: tuple[float, ...] = ()
    expense_history: tuple[float, ...] = ()
    is_hiring: bool = False
    job_postings: tuple[JobPosting, ...] = ()
    products: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.inventory is None:
            object.__setattr__(self, "inventory", {})


# ---------------------------------------------------------------------------
# LaborMarket
# ---------------------------------------------------------------------------

class LaborMarket:
    """Matches workers to jobs based on skills, wages, and availability."""

    def __init__(self) -> None:
        self._postings: list[JobPosting] = []

    @property
    def postings(self) -> list[JobPosting]:
        return list(self._postings)

    # -- Posting management -------------------------------------------------

    def post_job(
        self,
        firm: Firm,
        profession: str,
        wage: float,
        skill_req: float,
        tick: int,
    ) -> JobPosting:
        """Create a new job posting and register it on the market."""
        posting = JobPosting(
            posting_id=str(_uuid.uuid4()),
            firm_id=firm.firm_id,
            profession=profession,
            wage=wage,
            skill_requirement=skill_req,
            tick_posted=tick,
            filled=False,
        )
        self._postings.append(posting)
        return posting

    def fill_posting(self, posting_id: str) -> bool:
        """Mark a posting as filled. Returns ``False`` if not found."""
        for i, p in enumerate(self._postings):
            if p.posting_id == posting_id and not p.filled:
                self._postings[i] = replace(p, filled=True)
                return True
        return False

    def remove_expired(self, current_tick: int, max_age: int = 1000) -> int:
        """Remove unfilled postings older than *max_age* ticks. Returns count removed."""
        before = len(self._postings)
        self._postings = [
            p for p in self._postings
            if p.filled or (current_tick - p.tick_posted < max_age)
        ]
        return before - len(self._postings)

    # -- Job search ---------------------------------------------------------

    def find_jobs(
        self,
        agent_skills: dict[str, float],
    ) -> list[JobPosting]:
        """Return unfilled postings the agent qualifies for, sorted by wage (desc)."""
        suitable: list[JobPosting] = []
        for posting in self._postings:
            if posting.filled:
                continue
            skill_level = agent_skills.get(posting.profession, 0.0)
            if skill_level >= posting.skill_requirement:
                suitable.append(posting)
        return sorted(suitable, key=lambda p: -p.wage)

    # -- Aggregate stats ----------------------------------------------------

    def calculate_market_wage(self, profession: str) -> float:
        """Average offered wage for unfilled postings of *profession*."""
        active = [
            p for p in self._postings
            if p.profession == profession and not p.filled
        ]
        if not active:
            return 0.5  # default fallback
        return sum(p.wage for p in active) / len(active)

    def get_unemployment_rate(
        self,
        agents: list[dict],
    ) -> float:
        """Percentage of adult agents without employment.

        Each *agent* dict is expected to have keys:
        - ``"lifecycle_stage"``: ``"adult"`` | ``"elder"`` | ...
        - ``"employer_id"``: ``str | None``
        """
        adults = [a for a in agents if a.get("lifecycle_stage") in ("adult", "elder")]
        if not adults:
            return 0.0
        unemployed = [a for a in adults if a.get("employer_id") is None]
        return len(unemployed) / len(adults)

    def get_open_positions_count(self, profession: str | None = None) -> int:
        """Count unfilled postings, optionally filtered by profession."""
        return sum(
            1 for p in self._postings
            if not p.filled and (profession is None or p.profession == profession)
        )
