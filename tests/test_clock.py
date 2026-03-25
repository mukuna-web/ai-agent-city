"""Tests for WorldClock."""

import sys
sys.path.insert(0, "..")

from engine.clock import WorldClock


def test_clock_initial():
    clock = WorldClock()
    assert clock.tick == 0
    assert clock.day == 0
    assert clock.hour == 0


def test_clock_advance():
    clock = WorldClock()
    clock.advance()
    assert clock.tick == 1
    assert clock.hour == 1


def test_clock_day_cycle():
    clock = WorldClock(ticks_per_day=24)
    for _ in range(24):
        clock.advance()
    assert clock.day == 1
    assert clock.hour == 0


def test_clock_daytime():
    clock = WorldClock()
    clock.tick = 12  # noon
    assert clock.is_daytime
    clock.tick = 3  # 3am
    assert not clock.is_daytime
    assert clock.is_night


def test_clock_time_of_day():
    clock = WorldClock()
    clock.tick = 8
    assert clock.time_of_day == "morning"
    clock.tick = 14
    assert clock.time_of_day == "afternoon"
    clock.tick = 18
    assert clock.time_of_day == "evening"
    clock.tick = 22
    assert clock.time_of_day == "night"


def test_clock_is_new_day():
    clock = WorldClock(ticks_per_day=24)
    assert clock.is_new_day()  # tick 0 is hour 0
    clock.advance()
    assert not clock.is_new_day()
    for _ in range(23):
        clock.advance()
    assert clock.is_new_day()  # tick 24, hour 0


def test_clock_repr():
    clock = WorldClock()
    clock.tick = 30
    s = repr(clock)
    assert "Day 1" in s
    assert "06:00" in s
