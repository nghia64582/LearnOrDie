"""Tests for G2/G3 interpolation and Simulate parsing of arcs."""

from __future__ import annotations

import math
import os
import tempfile
import unittest

from engraver_ctrl.gcode_arcs import (
    center_from_r,
    interpolate_arc,
    interpolate_g2g3,
    arc_length,
)


class InterpolateArcTests(unittest.TestCase):
    def test_ij_semicircle_ccw_bulges_down(self):
        # Start (0, 5), end (10, 5), centre (5, 5): G3 / CCW through (5, 0).
        pts = interpolate_g2g3(
            0, 5, 10, 5, clockwise=False, i=5, j=0, max_chord=0.3,
        )
        self.assertAlmostEqual(pts[-1][0], 10.0)
        self.assertAlmostEqual(pts[-1][1], 5.0)
        mid = min(pts, key=lambda p: p[1])
        self.assertAlmostEqual(mid[0], 5.0, delta=0.25)
        self.assertAlmostEqual(mid[1], 0.0, delta=0.25)
        self.assertTrue(all(p[1] <= 5.0 + 1e-8 for p in pts))

    def test_ij_semicircle_cw_bulges_up(self):
        pts = interpolate_g2g3(
            0, 5, 10, 5, clockwise=True, i=5, j=0, max_chord=0.3,
        )
        mid = max(pts, key=lambda p: p[1])
        self.assertAlmostEqual(mid[0], 5.0, delta=0.25)
        self.assertAlmostEqual(mid[1], 10.0, delta=0.25)
        self.assertTrue(all(p[1] >= 5.0 - 1e-8 for p in pts))

    def test_full_circle_ij(self):
        # Start = end, I=-5: centre 5 units left of (10, 0) => (5, 0).
        pts = interpolate_g2g3(
            10, 0, 10, 0, clockwise=True, i=-5, j=0, max_chord=0.5,
        )
        self.assertGreaterEqual(len(pts), 16)
        self.assertAlmostEqual(pts[-1][0], 10.0)
        self.assertAlmostEqual(pts[-1][1], 0.0)
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        self.assertAlmostEqual(min(xs), 0.0, places=1)
        self.assertAlmostEqual(max(xs), 10.0, places=1)
        self.assertAlmostEqual(min(ys), -5.0, places=1)
        self.assertAlmostEqual(max(ys), 5.0, places=1)

    def test_r_positive_is_minor_arc(self):
        # (0,0) -> (10,0), R=+5: semicircle, unique centre (5, 0).
        cx, cy = center_from_r(0, 0, 10, 0, 5, clockwise=False)
        self.assertAlmostEqual(cx, 5.0, places=6)
        self.assertAlmostEqual(cy, 0.0, places=6)
        pts = interpolate_g2g3(0, 0, 10, 0, clockwise=False, r=5, max_chord=0.3)
        mid = min(pts, key=lambda p: p[1])
        self.assertAlmostEqual(mid[1], -5.0, places=2)

        pts_cw = interpolate_g2g3(0, 0, 10, 0, clockwise=True, r=5, max_chord=0.3)
        mid = max(pts_cw, key=lambda p: p[1])
        self.assertAlmostEqual(mid[1], 5.0, places=2)

    def test_r_negative_is_major_arc(self):
        # Quarter-ish: (0,5) -> (5,0), |R|=5. Minor CCW goes through ~45 deg
        # in the lower-right of centre (0,0); major would go the long way.
        pts_minor = interpolate_g2g3(0, 5, 5, 0, clockwise=True, r=5, max_chord=0.3)
        # CW minor from (0,5) to (5,0) around (0,0): through (5,5)?
        # Centre of R=5 from (0,5) to (5,0): (0,0) is one candidate (h).
        # CW from 90 deg to 0 deg is 90 deg (minor) through nothing in Q1...
        # 90 CW to 0: 90 -> 0 decreasing, through... 90 to 0 CW is 90->0
        # in Y-up: from +Y to +X going through Q1? CW from 90 to 0 is
        # 90 -> 0 directly (decreasing), which is the short arc in Q1,
        # midpoint 45 deg = (5/sqrt(2), 5/sqrt(2)).
        mid = max(pts_minor, key=lambda p: p[0] + p[1])
        self.assertGreater(mid[0], 2.0)
        self.assertGreater(mid[1], 2.0)

        pts_major = interpolate_g2g3(0, 5, 5, 0, clockwise=True, r=-5, max_chord=0.4)
        xs, ys = [p[0] for p in pts_major], [p[1] for p in pts_major]
        # Long CW around (5, 5) goes through (5, 10) and (10, 5).
        self.assertGreater(max(xs), 8.0)
        self.assertGreater(max(ys), 8.0)

    def test_chord_length_near_true_arc(self):
        pts = interpolate_g2g3(0, 5, 10, 5, clockwise=False, i=5, j=0, max_chord=0.3)
        chord = 0.0
        prev = (0.0, 5.0)
        for p in pts:
            chord += math.hypot(p[0] - prev[0], p[1] - prev[1])
            prev = p
        self.assertAlmostEqual(chord, math.pi * 5, places=2)


class ParseGcodeArcTests(unittest.TestCase):
    def parse(self, g):
        from engraver_ctrl.tab_simulate import TabSimulate
        return TabSimulate.parse_gcode(TabSimulate.__new__(TabSimulate), g)

    def test_g0_g1_unchanged(self):
        steps = self.parse("G0 X10 Y0\nG1 X10 Y20 F600\n")
        self.assertEqual(len(steps), 2)
        self.assertEqual(steps[0]["type"], "travel")
        self.assertEqual(steps[1]["type"], "cut")
        self.assertFalse(steps[0].get("arc"))
        self.assertFalse(steps[1].get("arc"))
        self.assertEqual(steps[1]["feed"], 600)
        self.assertAlmostEqual(steps[1]["y2"], 20)

    def test_g2_ij_hole_and_g3_cap(self):
        # Typical Small parts hole (two G2 halves) plus a G3 bottom cap.
        g = (
            "G0 X6.5 Y40\n"
            "G2 X3.5 Y40 I-1.5 J0 F250\n"
            "G2 X6.5 Y40 I1.5 J0\n"
            "G0 X0 Y5\n"
            "G3 X10 Y5 I5 J0\n"
        )
        steps = self.parse(g)
        cuts = [s for s in steps if s["type"] == "cut"]
        self.assertTrue(all(s.get("arc") for s in cuts))
        self.assertTrue(all(s["feed"] == 250 for s in cuts))
        # Hole, first half, should pass near (5, 38.5).
        first_hole = [s for s in cuts if s["line"] == 2]
        ys = [s["y2"] for s in first_hole] + [s["y1"] for s in first_hole]
        self.assertLess(min(ys), 39.0)
        # Cap should pass near (5, 0).
        cap = [s for s in cuts if s["command"].startswith("G3")]
        cap_ys = [s["y2"] for s in cap] + [s["y1"] for s in cap]
        self.assertLess(min(cap_ys), 0.6)
        # Path stays continuous.
        for a, b in zip(steps, steps[1:]):
            if a["type"] == "travel":
                continue
            if b["x1"] == a["x2"] and b["y1"] == a["y2"]:
                continue
            # travel may jump; cuts in one command must be chained
        for group_line in (2, 3, 5):
            segs = [s for s in cuts if s["line"] == group_line]
            for a, b in zip(segs, segs[1:]):
                self.assertAlmostEqual(a["x2"], b["x1"])
                self.assertAlmostEqual(a["y2"], b["y1"])

    def test_r_word_parsed(self):
        steps = self.parse("G0 X0 Y0\nG2 X10 Y0 R5 F100\n")
        cuts = [s for s in steps if s.get("arc")]
        self.assertGreater(len(cuts), 4)
        ys = [s["y2"] for s in cuts]
        self.assertGreater(max(ys), 4.5)

    def test_arc_time_uses_interpolated_length(self):
        from engraver_ctrl.sim_time import StepTimes
        steps = self.parse("G0 X0 Y5\nG3 X10 Y5 I5 J0 F300\n")
        t = StepTimes(steps)
        # Semicircle length 5*pi at 300 mm/min, plus a short G0.
        arc_s = (5 * math.pi) / 300 * 60
        # G0 is 5 mm at rapid; just check the cut portion is close.
        cut_time = sum(
            t.per_step[i] for i, s in enumerate(steps) if s["type"] == "cut"
        )
        self.assertAlmostEqual(cut_time, arc_s, places=2)

    def test_small_parts_export_has_visible_arcs_and_holes(self):
        from engraver_ctrl.cut_plan_builder import Part, build_cut_plan
        from engraver_ctrl.extended_cut_export import export_gcode_extended

        parts = [
            Part(50, True, False, [20]),
            Part(40, False, True, []),
        ]
        plan = build_cut_plan(114, parts, 10, 5, 1.5, method="heuristic")
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "cut_plan.gcode")
            export_gcode_extended(plan, path, feedrate=250, power=1000)
            with open(path, encoding="utf-8") as fh:
                text = fh.read()
        self.assertIn("G2 ", text)
        self.assertIn("G3 ", text)
        self.assertIn("I-1.500", text)
        steps = self.parse(text)
        arc_steps = [s for s in steps if s.get("arc")]
        self.assertGreater(len(arc_steps), 10)
        # At least one interpolated point leaves the diameter line of a cap
        # or goes around a hole (Y varies on an I/J move that started
        # with equal Y).
        y_span = max(s["y2"] for s in arc_steps) - min(s["y2"] for s in arc_steps)
        self.assertGreater(y_span, 1.0)



class MachineEstimateTests(unittest.TestCase):
    def test_arc_length_semicircle(self):
        length = arc_length(0, 5, 10, 5, clockwise=False, i=5, j=0)
        self.assertAlmostEqual(length, math.pi * 5, places=6)

    def test_estimate_uses_arc_not_chord(self):
        from engraver_ctrl.tab_machine import estimate_gcode_times
        lines = [
            "G90",
            "G0 X0 Y5",
            "G3 X10 Y5 I5 J0 F300",
        ]
        times = estimate_gcode_times(lines)
        self.assertEqual(len(times), 3)
        # Semicircle 5*pi mm at 300 mm/min; must not use the 10 mm chord.
        expected = (5 * math.pi) / 300 * 60
        self.assertAlmostEqual(times[2], expected, places=5)
        chord_time = 10 / 300 * 60
        self.assertNotAlmostEqual(times[2], chord_time, places=3)

    def test_estimate_r_word_and_g1_still_chord(self):
        from engraver_ctrl.tab_machine import estimate_gcode_times, MIN_LINE_TIME
        lines = [
            "G0 X0 Y0",
            "G1 X10 Y0 F600",
            "G2 X0 Y0 R5",
        ]
        times = estimate_gcode_times(lines)
        self.assertAlmostEqual(times[1], 10 / 600 * 60, places=5)
        # G2 R5 back to origin: semicircle length 5*pi at last feed 600.
        self.assertAlmostEqual(times[2], (5 * math.pi) / 600 * 60, places=4)

    def test_machine_preview_loads_arcs(self):
        from engraver_ctrl.tab_machine import GcodePreviewRenderer
        import tkinter as tk
        try:
            root = tk.Tk()
            root.withdraw()
        except tk.TclError as e:
            self.skipTest(f"Tk not available: {e}")
        try:
            canvas = tk.Canvas(root, width=200, height=200)
            preview = GcodePreviewRenderer(canvas)
            g = (
                "G0 X0 Y5\n"
                "G3 X10 Y5 I5 J0 F250\n"
                "G0 X6.5 Y40\n"
                "G2 X3.5 Y40 I-1.5 J0\n"
            )
            preview.load(g)
            self.assertGreater(preview.current_step, 0)
            self.assertEqual(preview.current_step, len(preview.steps))
            arc_steps = [s for s in preview.steps if s.get("arc")]
            self.assertGreater(len(arc_steps), 8)
            ys = [s["y2"] for s in arc_steps]
            # The G3 cap bulges down toward Y=0; the hole has Y around 40.
            self.assertLess(min(ys), 1.0)
            self.assertGreater(max(ys), 38.0)
        finally:
            root.destroy()



if __name__ == "__main__":
    unittest.main()
