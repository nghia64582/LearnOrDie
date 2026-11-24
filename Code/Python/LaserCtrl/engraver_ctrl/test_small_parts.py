"""Tests for Small parts packing, cut plan, text/card format, and G-code.

Run from LaserCtrl root:
  python -m unittest engraver_ctrl.test_small_parts
"""

from __future__ import annotations

import os
import tempfile
import unittest

from engraver_ctrl.cut_handler import (
    cut_bfd,
    cut_ffd,
    pack_pieces,
)
from engraver_ctrl.cut_plan_builder import (
    CUT_EXTRA_MARGIN,
    Part,
    arrange_bin,
    build_cut_plan,
    format_parts_text,
    parse_hole_field,
    parse_parts_text,
)
from engraver_ctrl.extended_cut_export import export_gcode_extended


def P(length, down=False, up=False, holes=None):
    return Part(length, down, up, list(holes or []))


class ParseFormatTests(unittest.TestCase):
    def test_parse_basic_and_comments(self):
        txt = """
# a comment
50, 1, 0, 10, 30
70, 0, 1, 20

30, 1, 1
90, 0, 0, 45
"""
        parts = parse_parts_text(txt)
        self.assertEqual(len(parts), 4)
        self.assertEqual(parts[0].length, 50)
        self.assertTrue(parts[0].is_cut_down)
        self.assertFalse(parts[0].is_cut_up)
        self.assertEqual(parts[0].hole_centers, [10.0, 30.0])
        self.assertEqual(parts[2].is_cut_down, True)
        self.assertEqual(parts[2].is_cut_up, True)
        self.assertEqual(parts[2].hole_centers, [])

    def test_roundtrip(self):
        parts = [
            P(50, True, False, [10, 30]),
            P(70.5, False, True, [20]),
            P(30, True, True),
        ]
        text = format_parts_text(parts)
        again = parse_parts_text(text)
        self.assertEqual(len(again), 3)
        self.assertAlmostEqual(again[1].length, 70.5)
        self.assertEqual(again[0].hole_centers, [10.0, 30.0])
        self.assertTrue(again[2].is_cut_down and again[2].is_cut_up)

    def test_parse_errors(self):
        with self.assertRaises(ValueError):
            parse_parts_text("50, 1")
        with self.assertRaises(ValueError):
            parse_parts_text("50, 2, 0")
        with self.assertRaises(ValueError):
            parse_parts_text("0, 0, 0")
        with self.assertRaises(ValueError):
            parse_parts_text("abc, 0, 1")

    def test_hole_field(self):
        self.assertEqual(parse_hole_field("10, 30"), [10.0, 30.0])
        self.assertEqual(parse_hole_field("10 20 30"), [10.0, 20.0, 30.0])
        self.assertEqual(parse_hole_field("  "), [])


class PackingTests(unittest.TestCase):
    def test_ffd_returns_original_indices(self):
        # Same length, different identity: order in a bin may change
        # because of decreasing sort, but indices must be preserved.
        lengths = [40.0, 40.0, 30.0]
        bins = cut_ffd(70.0, lengths)
        flat = [i for b in bins for i in b]
        self.assertEqual(sorted(flat), [0, 1, 2])
        # 40+30 fits, two 40s do not: 2 sticks.
        self.assertEqual(len(bins), 2)

    def test_float_capacity(self):
        bins, unplaced = pack_pieces(21.0, [10.5, 10.5], method="heuristic")
        self.assertEqual(unplaced, [])
        self.assertEqual(len(bins), 1)
        self.assertEqual(sorted(bins[0]), [0, 1])

    def test_unplaced_too_long(self):
        bins, unplaced = pack_pieces(114.0, [50.0, 200.0, 60.0], method="heuristic")
        self.assertEqual(unplaced, [1])
        placed = sorted(i for b in bins for i in b)
        self.assertEqual(placed, [0, 2])

    def test_ffd_vs_bfd_known(self):
        # 6,6,5,5 into 10: both need 3 sticks (5+5, 6, 6).
        lengths = [6, 6, 5, 5]
        self.assertEqual(len(cut_ffd(10, lengths)), 3)
        self.assertEqual(len(cut_bfd(10, lengths)), 3)
        bins, unplaced = pack_pieces(10, [5, 5, 5, 5], method="heuristic")
        self.assertEqual(unplaced, [])
        self.assertEqual(len(bins), 2)

    def test_exact_if_available(self):
        try:
            from ortools.sat.python import cp_model  # noqa: F401
        except ImportError:
            self.skipTest("ortools not installed")
        bins, unplaced = pack_pieces(
            10, [6, 6, 5, 5, 4, 4], method="exact", time_limit=2.0,
        )
        self.assertEqual(unplaced, [])
        self.assertEqual(len(bins), 3)  # e.g. 6+4, 6+4, 5+5


class ArrangeAndPlanTests(unittest.TestCase):
    def test_identity_not_length_match(self):
        # Two 40 mm pieces with different holes must keep their holes.
        parts = [
            P(40, False, False, [5]),
            P(40, False, False, [15]),
            P(80, False, False, [40]),
        ]
        plan = build_cut_plan(114, parts, width=10, gap=5, hole_radius=1.5,
                              method="heuristic")
        holes_by_part = {}
        for stick in plan.sticks:
            for p in stick.placements:
                holes_by_part[p.part_index] = [
                    (round(h[0], 6), round(h[1] - p.y_start, 6))
                    for h in plan.holes
                    if abs(h[1] - (p.y_start + 5)) < 1e-6
                    or abs(h[1] - (p.y_start + 15)) < 1e-6
                    or abs(h[1] - (p.y_start + 40)) < 1e-6
                ]
        # Direct check: relative hole offsets survive.
        found = {p.part_index: list(p.hole_centers)
                 for s in plan.sticks for p in s.placements}
        self.assertEqual(found[0], [5])
        self.assertEqual(found[1], [15])
        self.assertEqual(found[2], [40])
        # Absolute hole Y = y_start + relative.
        abs_holes = {(round(x, 5), round(y, 5)) for x, y in plan.holes}
        for stick in plan.sticks:
            for p in stick.placements:
                cx = stick.x_left + stick.width / 2.0
                for rel in p.hole_centers:
                    self.assertIn((round(cx, 5), round(p.y_start + rel, 5)), abs_holes)

    def test_waste_at_top_when_round_bottom(self):
        parts = [P(40, down=True, up=False), P(30, False, False)]
        plan = build_cut_plan(100, parts, 10, 5, 1.5, method="heuristic")
        self.assertEqual(len(plan.sticks), 1)
        stick = plan.sticks[0]
        self.assertAlmostEqual(stick.placements[0].y_start, 0.0)
        self.assertTrue(stick.placements[0].is_cut_down)
        self.assertEqual(stick.waste, [(70.0, 100.0)])

    def test_waste_at_bottom_when_only_round_top(self):
        parts = [P(40, down=False, up=True), P(30, False, False)]
        plan = build_cut_plan(100, parts, 10, 5, 1.5, method="heuristic")
        stick = plan.sticks[0]
        # First piece starts at leftover 30; last piece ends at 100.
        self.assertAlmostEqual(stick.placements[-1].y_end, 100.0)
        self.assertTrue(any(p.is_cut_up for p in stick.placements
                            if abs(p.y_end - 100.0) < 1e-9))
        self.assertEqual(stick.waste, [(0.0, 30.0)])

    def test_arrange_both_flags_waste_stays_top(self):
        parts = [P(20, True, False), P(20, False, True)]
        ordered, y0 = arrange_bin([0, 1], parts, 60)
        self.assertEqual(y0, 0.0)
        self.assertEqual(ordered[0], 0)
        self.assertEqual(ordered[-1], 1)

    def test_layout_and_end_cuts(self):
        parts = [P(50), P(50)]
        plan = build_cut_plan(100, parts, width=10, gap=5, hole_radius=1.5,
                              include_end_cut=True, method="heuristic")
        # One stick, left edge at 0, cuts start at -1, length 12.
        self.assertEqual(len(plan.sticks), 1)
        self.assertAlmostEqual(plan.sticks[0].x_left, 0.0)
        cut_ys = sorted(y for _x, y, _l in plan.cuts)
        self.assertTrue(any(abs(y - 0.0) < 1e-9 for y in cut_ys))
        self.assertTrue(any(abs(y - 50.0) < 1e-9 for y in cut_ys))
        self.assertTrue(any(abs(y - 100.0) < 1e-9 for y in cut_ys))
        for sx, _y, length in plan.cuts:
            self.assertAlmostEqual(sx, -CUT_EXTRA_MARGIN)
            self.assertAlmostEqual(length, 10 + 2 * CUT_EXTRA_MARGIN)

    def test_second_stick_x_position(self):
        parts = [P(80), P(80)]
        plan = build_cut_plan(100, parts, width=10, gap=5, hole_radius=1.5,
                              method="heuristic")
        self.assertEqual(len(plan.sticks), 2)
        self.assertAlmostEqual(plan.sticks[1].x_left, 15.0)

    def test_stats_waste(self):
        parts = [P(80)]
        plan = build_cut_plan(100, parts, 10, 5, 1.5, method="heuristic")
        self.assertAlmostEqual(plan.waste_length(), 20.0)
        self.assertAlmostEqual(plan.waste_percent(), 20.0)
        self.assertAlmostEqual(plan.used_length(), 80.0)

    def test_arch_positions(self):
        parts = [P(50, down=True, up=True)]
        plan = build_cut_plan(50, parts, width=10, gap=5, hole_radius=1.5,
                              method="heuristic")
        # Lower arch center at y=5, upper at y=45, x=5.
        self.assertEqual(len(plan.arches), 2)
        ups = {(round(x, 5), round(y, 5), u) for x, y, u in plan.arches}
        self.assertIn((5.0, 5.0, True), ups)
        self.assertIn((5.0, 45.0, False), ups)


class GcodeExportTests(unittest.TestCase):
    def test_header_and_defaults(self):
        parts = [P(50, down=True, holes=[10])]
        plan = build_cut_plan(114, parts, 10, 5, 1.5, method="heuristic")
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "cut_plan.gcode")
            export_gcode_extended(plan, path, feedrate=250, power=1000)
            with open(path, encoding="utf-8") as fh:
                text = fh.read()
        self.assertIn("G21", text)
        self.assertIn("G90", text)
        self.assertIn("M3 S1000", text)
        self.assertIn("F250", text)
        self.assertIn("G1 X", text)
        self.assertIn("G2 ", text)  # hole and/or upper arch
        self.assertIn("G3 ", text)  # lower arch
        self.assertTrue(text.strip().endswith("; END"))


class TabModeSyncTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import tkinter as tk
        try:
            cls.root = tk.Tk()
            cls.root.withdraw()
        except tk.TclError as e:
            raise unittest.SkipTest(f"Tk not available: {e}")

    @classmethod
    def tearDownClass(cls):
        try:
            cls.root.destroy()
        except Exception:
            pass

    def test_text_card_sync_and_defaults(self):
        from engraver_ctrl.tab_small_parts import SmallPartsTab

        class Host:
            font = None
            root = self.root

        tab = SmallPartsTab(self.root, Host())
        self.assertEqual(tab.entry_stock_length.get(), "114")
        self.assertEqual(tab.entry_width.get(), "10")
        self.assertEqual(tab.entry_feedrate.get(), "250")
        self.assertEqual(tab.entry_power.get(), "1000")

        sample = "50, 1, 0, 10, 30\n70, 0, 1, 20\n"
        tab.text_parts.delete("1.0", "end")
        tab.text_parts.insert("1.0", sample)
        tab.mode_var.set("cards")
        tab.on_mode_change()
        self.assertEqual(tab._mode, "cards")
        self.assertEqual(len(tab._cards), 2)
        self.assertEqual(tab._cards[0].length_var.get(), "50")
        self.assertTrue(tab._cards[0].down_var.get())
        self.assertFalse(tab._cards[0].up_var.get())
        self.assertEqual(tab._cards[0].holes_var.get(), "10, 30")
        self.assertEqual(tab._cards[1].length_var.get(), "70")
        self.assertTrue(tab._cards[1].up_var.get())

        # Edit a card, switch back, text must follow.
        tab._cards[1].length_var.set("72")
        tab._cards[1].holes_var.set("8 22")
        tab.mode_var.set("text")
        tab.on_mode_change()
        text = tab.text_parts.get("1.0", "end")
        again = parse_parts_text(text)
        self.assertEqual(again[1].length, 72)
        self.assertEqual(again[1].hole_centers, [8.0, 22.0])
        self.assertTrue(again[0].is_cut_down)
        tab.destroy()

    def test_preview_builds_plan(self):
        from engraver_ctrl.tab_small_parts import SmallPartsTab
        import tkinter as tk

        class Host:
            font = None

        tab = SmallPartsTab(self.root, Host())
        tab.text_parts.insert("1.0", "50, 1, 0, 10\n80, 0, 1\n")
        tab.on_preview()
        self.assertIsNotNone(tab._plan)
        self.assertGreaterEqual(len(tab._plan.sticks), 1)
        self.assertGreater(len(tab._plan.cuts), 0)
        # Canvas should have drawn something.
        self.assertTrue(tab.canvas.find_all())
        tab.destroy()


if __name__ == "__main__":
    unittest.main()
