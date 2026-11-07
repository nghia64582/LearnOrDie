"""Pure time estimation for the Simulate tab's step model.

Each step is one straight segment from tab_simulate.parse_gcode:
  {"type": "travel"|"cut", "x1","y1","x2","y2", "feed": F or None}

Estimate = path length / rate (no acceleration, no controller overhead).
- "travel" (G0) uses RAPID_RATE_MM_MIN (F is ignored for G0, like GRBL).
- "cut" (G1) uses the modal F (mm/min) in effect on that line; if no F
  was seen yet, DEFAULT_FEED_MM_MIN is assumed and the step is flagged.
G2/G3 arcs and G4 dwell are not steps in the simulator, so they are not
counted here.
"""

from __future__ import annotations

import math

# Same assumptions as the Machine tab estimate (tab_machine.py).
RAPID_RATE_MM_MIN = 3000.0   # G0 speed; GRBL $110/$111
DEFAULT_FEED_MM_MIN = 1000.0  # used only for G1 before any F is seen


def step_length(step):
    return math.hypot(step["x2"] - step["x1"], step["y2"] - step["y1"])


def step_rate(step, rapid=RAPID_RATE_MM_MIN, default_feed=DEFAULT_FEED_MM_MIN):
    """Return (rate_mm_min, assumed_flag)."""
    if step.get("type") == "travel":
        return rapid, False
    feed = step.get("feed")
    if feed is None or feed <= 0:
        return default_feed, True
    return float(feed), False


def step_seconds(step, rapid=RAPID_RATE_MM_MIN, default_feed=DEFAULT_FEED_MM_MIN):
    length = step_length(step)
    if length <= 0:
        return 0.0
    rate, _ = step_rate(step, rapid, default_feed)
    if rate <= 0:
        return 0.0
    return length / rate * 60.0


class StepTimes:
    """Per-step and cumulative (inclusive) durations in seconds."""

    def __init__(self, steps, rapid=RAPID_RATE_MM_MIN,
                 default_feed=DEFAULT_FEED_MM_MIN):
        self.per_step = []
        self.cumulative = []
        self.assumed_feed_steps = 0
        total = 0.0
        for s in steps:
            t = step_seconds(s, rapid, default_feed)
            if s.get("type") != "travel" and step_rate(s, rapid, default_feed)[1] \
                    and step_length(s) > 0:
                self.assumed_feed_steps += 1
            total += t
            self.per_step.append(t)
            self.cumulative.append(total)
        self.total = total

    def step_time(self, current_step):
        """Duration of step N (1-based, as shown in the UI). 0 for N=0."""
        if current_step <= 0 or current_step > len(self.per_step):
            return 0.0
        return self.per_step[current_step - 1]

    def through(self, current_step):
        """Time from program start until step N finishes (inclusive)."""
        if current_step <= 0 or not self.cumulative:
            return 0.0
        return self.cumulative[min(current_step, len(self.cumulative)) - 1]


def format_duration(seconds):
    if seconds < 60:
        return f"{seconds:.1f} s"
    s = int(round(seconds))
    h, rem = divmod(s, 3600)
    m, sec = divmod(rem, 60)
    if h:
        return f"{h}:{m:02d}:{sec:02d}"
    return f"{m}:{sec:02d}"
