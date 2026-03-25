"""Tests for Event System."""

import sys
sys.path.insert(0, "..")

from engine.events import Event, EventManager


def test_event_creation():
    e = Event(type="weather", name="Rain", tick_start=10, duration=5, effects={"mood": -0.1})
    assert e.tick_end == 15
    assert e.is_active(12)
    assert not e.is_active(16)


def test_event_area():
    e = Event(type="disaster", name="Drought", tick_start=0, duration=10,
              affected_area=(25, 25, 5), effects={"food_regen": 0.0})
    assert e.affects_position(25, 25)
    assert e.affects_position(28, 28)
    assert not e.affects_position(40, 40)


def test_global_event():
    e = Event(type="economic", name="Boom", tick_start=0, duration=10,
              affected_area=None, effects={"price_multiplier": 1.5})
    assert e.affects_position(0, 0)
    assert e.affects_position(99, 99)


def test_event_manager_random():
    em = EventManager(seed=42)
    events = []
    for tick in range(1000):
        events.extend(em.check_random_events(tick, 50, 50))
    assert len(events) > 0  # should have generated some events over 1000 ticks


def test_event_manager_active():
    em = EventManager(seed=42)
    e = Event(type="test", name="Test", tick_start=5, duration=3, effects={})
    em.active_events.append(e)
    assert len(em.get_active_events(6)) == 1
    assert len(em.get_active_events(10)) == 0


def test_event_effects_at():
    em = EventManager()
    e1 = Event(type="weather", name="Rain", tick_start=0, duration=10,
               affected_area=None, effects={"mood": -0.1})
    e2 = Event(type="economic", name="Boom", tick_start=0, duration=10,
               affected_area=None, effects={"mood": 0.2, "trade_bonus": 0.1})
    em.active_events = [e1, e2]
    effects = em.get_effects_at(5, 0, 0)
    assert effects["mood"] == 0.1  # -0.1 + 0.2
    assert effects["trade_bonus"] == 0.1
