"""Tests for engraver_ctrl.sim_time (run from LaserCtrl root:
python -m unittest engraver_ctrl.test_sim_time)."""

import unittest

from engraver_ctrl.sim_time import (
    DEFAULT_FEED_MM_MIN, RAPID_RATE_MM_MIN, StepTimes, format_duration,
    step_seconds,
)


def seg(kind, x1, y1, x2, y2, feed=None):
    return {"type": kind, "x1": x1, "y1": y1, "x2": x2, "y2": y2, "feed": feed}


class SimTimeTests(unittest.TestCase):
    def test_mm_per_min_conversion(self):
        # 100 mm at F600 mm/min = 10 s
        self.assertAlmostEqual(step_seconds(seg("cut", 0, 0, 100, 0, 600)), 10.0)

    def test_rapid_ignores_feed(self):
        s = seg("travel", 0, 0, 30, 40, feed=1)  # 50 mm
        self.assertAlmostEqual(step_seconds(s), 50 / RAPID_RATE_MM_MIN * 60)

    def test_missing_feed_assumed_and_flagged(self):
        times = StepTimes([seg("cut", 0, 0, 10, 0, None)])
        self.assertAlmostEqual(times.total, 10 / DEFAULT_FEED_MM_MIN * 60)
        self.assertEqual(times.assumed_feed_steps, 1)

    def test_zero_length_and_empty(self):
        self.assertEqual(step_seconds(seg("cut", 5, 5, 5, 5, 0)), 0.0)
        empty = StepTimes([])
        self.assertEqual(empty.total, 0.0)
        self.assertEqual(empty.through(0), 0.0)
        self.assertEqual(empty.step_time(1), 0.0)

    def test_cumulative_inclusive_and_final(self):
        steps = [seg("travel", 0, 0, 0, 50),
                 seg("cut", 0, 50, 60, 50, 1200),   # 3 s
                 seg("cut", 60, 50, 60, 50, 1200)]  # 0 s
        t = StepTimes(steps)
        self.assertEqual(t.through(0), 0.0)
        self.assertAlmostEqual(t.through(1), 1.0)       # 50 mm @3000
        self.assertAlmostEqual(t.through(2), 4.0)
        self.assertAlmostEqual(t.step_time(2), 3.0)
        self.assertAlmostEqual(t.through(3), t.total)
        self.assertEqual(t.cumulative, sorted(t.cumulative))

    def test_modal_feed_from_parser(self):
        import tkinter  # noqa: F401  parser lives on the Tk tab class
        from engraver_ctrl.tab_simulate import TabSimulate
        g = "F600\nG1 X100\nG0 X0 Y0\nG1 X0 Y60 F1200\nG1 Y120\n"
        steps = TabSimulate.parse_gcode(TabSimulate.__new__(TabSimulate), g)
        self.assertEqual([s["feed"] for s in steps], [600, 600, 1200, 1200])
        t = StepTimes(steps)
        self.assertAlmostEqual(t.step_time(1), 10.0)
        self.assertAlmostEqual(t.step_time(4), 3.0)

    def test_format(self):
        self.assertEqual(format_duration(4.25), "4.2 s")
        self.assertEqual(format_duration(125), "2:05")
        self.assertEqual(format_duration(3725), "1:02:05")


if __name__ == "__main__":
    unittest.main()
