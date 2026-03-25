"""Unit tests for the agent system."""

import pytest

from src.agents import (
    Agent,
    AgentBiology,
    AgentCognition,
    AgentEconomy,
    AgentGoals,
    AgentIdentity,
    AgentNeeds,
    AgentPersonality,
    AgentSkills,
    AgentSocial,
    Goal,
    Plan,
    PlanStep,
    SkillSystem,
)
from src.agents.cognition import Action
from src.agents.factory import create_founder_population


class TestAgentNeeds:
    def test_decay_reduces_needs(self) -> None:
        needs = AgentNeeds(
            food=1.0, water=1.0, shelter=1.0, rest=1.0, health=1.0,
            safety=1.0, belonging=1.0, esteem=1.0, self_actualization=1.0,
        )
        decayed = needs.decay_one_tick()
        assert decayed.food < 1.0
        assert decayed.water < 1.0
        assert decayed.rest < 1.0

    def test_most_urgent_returns_lowest(self) -> None:
        needs = AgentNeeds(
            food=0.1, water=0.5, shelter=0.8, rest=0.9, health=1.0,
            safety=1.0, belonging=1.0, esteem=1.0, self_actualization=1.0,
        )
        assert needs.most_urgent() == "food"

    def test_satisfy_increases_need(self) -> None:
        needs = AgentNeeds(
            food=0.3, water=0.5, shelter=0.8, rest=0.9, health=1.0,
            safety=1.0, belonging=1.0, esteem=1.0, self_actualization=1.0,
        )
        satisfied = needs.satisfy("food", 0.5)
        assert satisfied.food == pytest.approx(0.8)

    def test_satisfy_clamps_to_one(self) -> None:
        needs = AgentNeeds(
            food=0.9, water=1.0, shelter=1.0, rest=1.0, health=1.0,
            safety=1.0, belonging=1.0, esteem=1.0, self_actualization=1.0,
        )
        satisfied = needs.satisfy("food", 0.5)
        assert satisfied.food == 1.0

    def test_satisfy_invalid_need_raises(self) -> None:
        needs = AgentNeeds(
            food=0.5, water=0.5, shelter=0.5, rest=0.5, health=0.5,
            safety=0.5, belonging=0.5, esteem=0.5, self_actualization=0.5,
        )
        with pytest.raises(ValueError, match="Unknown need"):
            needs.satisfy("nonexistent", 0.5)

    def test_min_need(self) -> None:
        needs = AgentNeeds(
            food=0.3, water=0.5, shelter=0.8, rest=0.1, health=1.0,
            safety=1.0, belonging=1.0, esteem=1.0, self_actualization=1.0,
        )
        assert needs.min_need() == pytest.approx(0.1)

    def test_to_vector_length(self) -> None:
        needs = AgentNeeds(
            food=0.5, water=0.5, shelter=0.5, rest=0.5, health=0.5,
            safety=0.5, belonging=0.5, esteem=0.5, self_actualization=0.5,
        )
        vec = needs.to_vector()
        assert len(vec) == 9
        assert all(v == pytest.approx(0.5) for v in vec)

    def test_validation_rejects_out_of_range(self) -> None:
        with pytest.raises(ValueError):
            AgentNeeds(
                food=1.5, water=0.5, shelter=0.5, rest=0.5, health=0.5,
                safety=0.5, belonging=0.5, esteem=0.5, self_actualization=0.5,
            )


class TestPersonality:
    def test_random_generates_valid(self) -> None:
        p = AgentPersonality.random()
        assert 0 <= p.openness <= 1
        assert 0 <= p.conscientiousness <= 1
        assert 0 <= p.extraversion <= 1
        assert 0 <= p.agreeableness <= 1
        assert 0 <= p.neuroticism <= 1

    def test_inherit_produces_midpoint_with_noise(self) -> None:
        a = AgentPersonality(
            openness=0.8, conscientiousness=0.8, extraversion=0.8,
            agreeableness=0.8, neuroticism=0.2,
        )
        b = AgentPersonality(
            openness=0.2, conscientiousness=0.2, extraversion=0.2,
            agreeableness=0.2, neuroticism=0.8,
        )
        child = AgentPersonality.inherit(a, b)
        # Should be roughly in the middle
        assert 0.1 < child.openness < 0.9

    def test_risk_tolerance_derived(self) -> None:
        p = AgentPersonality(
            openness=0.8, conscientiousness=0.5, extraversion=0.5,
            agreeableness=0.5, neuroticism=0.2,
        )
        # risk_tolerance = openness * (1 - neuroticism) = 0.8 * 0.8 = 0.64
        assert p.risk_tolerance == pytest.approx(0.64)

    def test_ambition_derived(self) -> None:
        p = AgentPersonality(
            openness=0.5, conscientiousness=0.8, extraversion=0.5,
            agreeableness=0.5, neuroticism=0.5,
        )
        # ambition = conscientiousness * (1 - agreeableness * 0.3) = 0.8 * 0.85 = 0.68
        assert p.ambition == pytest.approx(0.68)


class TestBiology:
    def test_age_one_tick_increments_age(self) -> None:
        bio = AgentBiology(
            age_ticks=5000, lifecycle_stage="adult", health=1.0,
            max_health=1.0, fertility=0.8, is_alive=True, cause_of_death=None,
        )
        new_bio = bio.age_one_tick()
        assert new_bio.age_ticks == 5001

    def test_elder_health_decay(self) -> None:
        bio = AgentBiology(
            age_ticks=16000, lifecycle_stage="elder", health=0.5,
            max_health=0.5, fertility=0.3, is_alive=True, cause_of_death=None,
        )
        new_bio = bio.age_one_tick()
        assert new_bio.health < 0.5
        assert new_bio.max_health < 0.5

    def test_dead_agent_does_not_age(self) -> None:
        bio = AgentBiology(
            age_ticks=20000, lifecycle_stage="elder", health=0.0,
            max_health=0.1, fertility=0.0, is_alive=False,
            cause_of_death="old_age",
        )
        new_bio = bio.age_one_tick()
        assert new_bio.age_ticks == 20000  # No change

    def test_lifecycle_transitions(self) -> None:
        from src.agents.biology import get_lifecycle_stage
        assert get_lifecycle_stage(0) == "child"
        assert get_lifecycle_stage(1999) == "child"
        assert get_lifecycle_stage(2000) == "adolescent"
        assert get_lifecycle_stage(3999) == "adolescent"
        assert get_lifecycle_stage(4000) == "adult"
        assert get_lifecycle_stage(15999) == "adult"
        assert get_lifecycle_stage(16000) == "elder"
        assert get_lifecycle_stage(50000) == "elder"


class TestSkillSystem:
    def test_practice_improves_skill(self) -> None:
        skills = AgentSkills(
            skills={"farming": 0.3}, experience={"farming": 0},
            talent={"farming": 0.7},
        )
        system = SkillSystem()
        improved = system.practice(skills, "farming")
        assert improved.skills["farming"] > 0.3

    def test_practice_increments_experience(self) -> None:
        skills = AgentSkills(
            skills={"farming": 0.3}, experience={"farming": 10},
            talent={"farming": 0.7},
        )
        system = SkillSystem()
        improved = system.practice(skills, "farming")
        assert improved.experience["farming"] == 11

    def test_diminishing_returns(self) -> None:
        skills_low = AgentSkills(
            skills={"farming": 0.1}, experience={}, talent={"farming": 0.7},
        )
        skills_high = AgentSkills(
            skills={"farming": 0.9}, experience={}, talent={"farming": 0.7},
        )
        system = SkillSystem()
        gain_low = system.practice(skills_low, "farming").skills["farming"] - 0.1
        gain_high = system.practice(skills_high, "farming").skills["farming"] - 0.9
        assert gain_low > gain_high  # Lower skill = faster improvement

    def test_decay_unused(self) -> None:
        skills = AgentSkills(
            skills={"farming": 0.5, "mining": 0.5},
            experience={}, talent={},
        )
        system = SkillSystem()
        decayed = system.decay_unused(skills, active_skill="farming")
        assert decayed.skills["farming"] == 0.5  # Active, no decay
        assert decayed.skills["mining"] < 0.5     # Inactive, decayed

    def test_teach_faster_than_practice(self) -> None:
        teacher = AgentSkills(
            skills={"farming": 0.9}, experience={}, talent={"farming": 0.7},
        )
        student = AgentSkills(
            skills={"farming": 0.2}, experience={}, talent={"farming": 0.7},
        )
        system = SkillSystem()
        taught = system.teach(teacher, student, "farming")
        practiced = system.practice(student, "farming")
        taught_gain = taught.skills["farming"] - 0.2
        practice_gain = practiced.skills["farming"] - 0.2
        assert taught_gain > practice_gain  # Teaching is faster

    def test_teach_cannot_exceed_teacher(self) -> None:
        teacher = AgentSkills(
            skills={"farming": 0.3}, experience={}, talent={"farming": 0.7},
        )
        student = AgentSkills(
            skills={"farming": 0.5}, experience={}, talent={"farming": 0.7},
        )
        system = SkillSystem()
        result = system.teach(teacher, student, "farming")
        assert result.skills["farming"] == 0.5  # No change


class TestEconomy:
    def test_net_worth_calculation(self) -> None:
        econ = AgentEconomy(
            cash=500, assets=("house_1", "tool_1"), employer_id=None,
            profession=None, wage=0, daily_expenses=0, savings_target=1000,
            debt=100, owned_firm_id=None,
        )
        # 500 + 2*100 - 100 = 600
        assert econ.net_worth() == pytest.approx(600.0)

    def test_can_afford(self) -> None:
        econ = AgentEconomy(
            cash=150, assets=(), employer_id=None, profession=None,
            wage=0, daily_expenses=0, savings_target=500, debt=0,
            owned_firm_id=None,
        )
        assert econ.can_afford(100) is True
        assert econ.can_afford(150) is True
        assert econ.can_afford(200) is False


class TestCognition:
    def test_reactive_returns_find_food_when_hungry(self) -> None:
        agent = create_founder_population(1)[0]
        # Set food to critical level
        new_needs = agent.needs.satisfy("food", -agent.needs.food + 0.05)
        agent = agent.with_needs(new_needs)
        cognition = AgentCognition()
        actions = cognition.tick(agent, tick=1)
        assert any(a.action_type == "find_food" for a in actions)

    def test_reactive_returns_flee_when_unsafe(self) -> None:
        agent = create_founder_population(1)[0]
        new_needs = agent.needs.satisfy("safety", -agent.needs.safety + 0.1)
        agent = agent.with_needs(new_needs)
        cognition = AgentCognition()
        actions = cognition.tick(agent, tick=1)
        assert any(a.action_type == "flee_danger" for a in actions)

    def test_default_wander_when_unemployed(self) -> None:
        agent = create_founder_population(1)[0]
        # Ensure all needs are above threshold so reactive doesn't fire
        full_needs = AgentNeeds(
            food=1.0, water=1.0, shelter=1.0, rest=1.0, health=1.0,
            safety=1.0, belonging=1.0, esteem=1.0, self_actualization=1.0,
        )
        agent = agent.with_needs(full_needs)
        cognition = AgentCognition()
        actions = cognition.tick(agent, tick=1)
        assert any(a.action_type == "wander" for a in actions)

    def test_execute_plan_step(self) -> None:
        agent = create_founder_population(1)[0]
        full_needs = AgentNeeds(
            food=1.0, water=1.0, shelter=1.0, rest=1.0, health=1.0,
            safety=1.0, belonging=1.0, esteem=1.0, self_actualization=1.0,
        )
        step = PlanStep(
            action="move_to", target="market_1",
            parameters={"speed": "walk"}, estimated_ticks=10,
        )
        plan = Plan(
            plan_id="plan_1", goal_id="goal_1",
            steps=(step,), current_step=0, status="executing",
        )
        goals = AgentGoals(
            immediate=[], short_term=[], long_term=[], active_plan=plan,
        )
        agent = agent.with_needs(full_needs).with_goals(goals)
        cognition = AgentCognition()
        actions = cognition.tick(agent, tick=1)
        assert any(a.action_type == "move_to" for a in actions)


class TestFactory:
    def test_creates_correct_count(self) -> None:
        agents = create_founder_population(50)
        assert len(agents) == 50

    def test_all_adults(self) -> None:
        agents = create_founder_population(10)
        for a in agents:
            assert a.biology.lifecycle_stage == "adult"

    def test_unique_ids(self) -> None:
        agents = create_founder_population(20)
        ids = [a.identity.agent_id for a in agents]
        assert len(ids) == len(set(ids))

    def test_all_alive(self) -> None:
        agents = create_founder_population(10)
        for a in agents:
            assert a.biology.is_alive is True

    def test_founders_have_skills(self) -> None:
        agents = create_founder_population(10)
        for a in agents:
            assert len(a.skills.skills) >= 1

    def test_founders_have_generation_zero(self) -> None:
        agents = create_founder_population(5)
        for a in agents:
            assert a.identity.generation == 0


class TestAgentImmutability:
    def test_with_needs_returns_new_agent(self) -> None:
        agents = create_founder_population(1)
        agent = agents[0]
        new_needs = agent.needs.satisfy("food", 0.5)
        new_agent = agent.with_needs(new_needs)
        assert new_agent is not agent
        assert new_agent.needs.food != agent.needs.food or agent.needs.food == 1.0

    def test_frozen_dataclass_prevents_mutation(self) -> None:
        agents = create_founder_population(1)
        agent = agents[0]
        with pytest.raises(AttributeError):
            agent.identity = None  # type: ignore[misc]

    def test_create_child_inherits_traits(self) -> None:
        agents = create_founder_population(2)
        parent_a, parent_b = agents[0], agents[1]
        child = Agent.create_child(parent_a, parent_b, tick=10000)
        assert child.biology.lifecycle_stage == "child"
        assert child.biology.age_ticks == 0
        assert child.identity.generation == 1
        assert child.identity.parent_ids == (
            parent_a.identity.agent_id,
            parent_b.identity.agent_id,
        )
        assert child.social.parent_ids == (
            parent_a.identity.agent_id,
            parent_b.identity.agent_id,
        )
