"""World clock with tick-based time, day/night cycles."""

from __future__ import annotations


class WorldClock:
    def __init__(self, ticks_per_day: int = 24):
        self.tick: int = 0
        self.ticks_per_day = ticks_per_day

    @property
    def day(self) -> int:
        return self.tick // self.ticks_per_day

    @property
    def hour(self) -> int:
        return self.tick % self.ticks_per_day

    @property
    def is_daytime(self) -> bool:
        return 6 <= self.hour < 20

    @property
    def is_morning(self) -> bool:
        return 6 <= self.hour < 12

    @property
    def is_night(self) -> bool:
        return not self.is_daytime

    @property
    def time_of_day(self) -> str:
        h = self.hour
        if 6 <= h < 12:
            return "morning"
        elif 12 <= h < 17:
            return "afternoon"
        elif 17 <= h < 20:
            return "evening"
        else:
            return "night"

    def advance(self) -> int:
        self.tick += 1
        return self.tick

    def is_new_day(self) -> bool:
        return self.hour == 0

    def __repr__(self) -> str:
        return f"Day {self.day}, {self.hour:02d}:00 ({self.time_of_day})"
