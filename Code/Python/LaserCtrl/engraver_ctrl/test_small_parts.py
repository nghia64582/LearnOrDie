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
    arch_apex_y,
    arch_polyline,
    arrange_bin,
    build_cut_plan,
    format_parts_text,
    parse_hole_field,
    parse_parts_text,
    piece_polygon,
    rounded_end_arches,
    stadium_slice_polygon,
    stick_y_bounds,
    usable_length,
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
        self.assertAlmostEqual(plan.usable_length, 95.0)
        self.assertAlmostEqual(stick.placements[0].y_start, 0.0)
        self.assertTrue(stick.placements[0].is_cut_down)
        # Bottom cap [-r, 0] is always waste; leftover sits at the
        # top of the usable span [0, L-r] = [0, 95].
        self.assertEqual(stick.waste, [(-5.0, 0.0), (70.0, 95.0)])

    def test_waste_at_bottom_when_only_round_top(self):
        parts = [P(40, down=False, up=True), P(30, False, False)]
        plan = build_cut_plan(100, parts, 10, 5, 1.5, method="heuristic")
        stick = plan.sticks[0]
        # Usable = 95; leftover 25 sits at the bottom of the usable
        # span so the last piece ends at the factory top y = L-r.
        self.assertAlmostEqual(stick.placements[-1].y_end, 95.0)
        self.assertTrue(any(p.is_cut_up for p in stick.placements
                            if abs(p.y_end - 95.0) < 1e-9))
        # Bottom cap merges with leftover in [0, 25].
        self.assertEqual(stick.waste, [(-5.0, 25.0)])

    def test_arrange_round_top_reuses_factory_top(self):
        # Even when a rounded-bottom piece is also present, leftover
        # is placed at the bottom of the usable span so the rounded
        # top can sit on the factory tip at y = usable.
        parts = [P(20, True, False), P(20, False, True)]
        ordered, y0 = arrange_bin([0, 1], parts, 60)
        self.assertAlmostEqual(y0, 20.0)
        self.assertEqual(ordered[-1], 1)

    def test_layout_and_end_cuts(self):
        # Stock 105, width 10 => usable 100, two 50 mm pieces fill it.
        parts = [P(50), P(50)]
        plan = build_cut_plan(105, parts, width=10, gap=5, hole_radius=1.5,
                              include_end_cut=True, method="heuristic")
        # One stick, left edge at 0, cuts start at -1, length 12.
        self.assertEqual(len(plan.sticks), 1)
        self.assertAlmostEqual(plan.usable_length, 100.0)
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
        # Bottom cap 5 mm + leftover 15 mm in the 95 mm usable span.
        self.assertAlmostEqual(plan.waste_length(), 20.0)
        self.assertAlmostEqual(plan.waste_percent(), 20.0)
        self.assertAlmostEqual(plan.used_length(), 80.0)
        self.assertEqual(plan.sticks[0].waste, [(-5.0, 0.0), (80.0, 95.0)])

    def test_arch_positions_and_convex_direction(self):
        # Stock 55, width 10 => usable 50, so a 50 mm piece fills
        # the usable span and reuses the factory top tip at y=50.
        parts = [P(50, down=True, up=True)]
        plan = build_cut_plan(55, parts, width=10, gap=5, hole_radius=1.5,
                              method="heuristic")
        # Bottom cap centre at y0+W/2=5, bulge down; top centre at 45, bulge up.
        self.assertEqual(len(plan.arches), 2)
        arches = {(round(x, 5), round(y, 5), b) for x, y, b in plan.arches}
        self.assertIn((5.0, 5.0, False), arches)
        self.assertIn((5.0, 45.0, True), arches)
        # Apex of each cap sits on the nearest end cut.
        by_flag = {b: (cx, cy) for cx, cy, b in plan.arches}
        self.assertAlmostEqual(arch_apex_y(by_flag[False][1], False, 10), 0.0)
        self.assertAlmostEqual(arch_apex_y(by_flag[True][1], True, 10), 50.0)

    def test_arch_polyline_bulges_toward_the_cut(self):
        # Midpoint of the polyline is the apex.
        down = arch_polyline(5, 15, 5, bulge_up=False, n=18)
        self.assertAlmostEqual(down[0][0], 0.0)
        self.assertAlmostEqual(down[0][1], 15.0)
        self.assertAlmostEqual(down[-1][0], 10.0)
        self.assertAlmostEqual(down[-1][1], 15.0)
        mid = down[len(down) // 2]
        self.assertAlmostEqual(mid[0], 5.0, places=5)
        self.assertAlmostEqual(mid[1], 10.0, places=5)  # y0 = 10, bulges down

        up = arch_polyline(5, 35, 5, bulge_up=True, n=18)
        mid = up[len(up) // 2]
        self.assertAlmostEqual(mid[0], 5.0, places=5)
        self.assertAlmostEqual(mid[1], 40.0, places=5)  # y1 = 40, bulges up
        # Every interior point stays on the bulge side (not a notch).
        self.assertTrue(all(pt[1] <= 15.0 + 1e-9 for pt in down))
        self.assertTrue(all(pt[1] >= 35.0 - 1e-9 for pt in up))

    def test_interior_rounded_end_omits_straight_cut(self):
        # Two rounded-bottom pieces: the first starts at y=0 (the
        # mandatory cut that severs the factory cap), the second has
        # an interior rounded bottom at Y=30 whose arc must replace
        # the straight cut (a line at 30 would clip the tip).
        parts = [P(30, down=True), P(30, down=True), P(20)]
        plan = build_cut_plan(100, parts, width=10, gap=5, hole_radius=1.5,
                              include_end_cut=True, method="heuristic")
        cut_ys = sorted(y for _x, y, _l in plan.cuts)
        self.assertTrue(any(abs(y - 0.0) < 1e-9 for y in cut_ys), cut_ys)
        self.assertTrue(any(abs(y - 60.0) < 1e-9 for y in cut_ys), cut_ys)
        self.assertFalse(any(abs(y - 30.0) < 1e-9 for y in cut_ys), cut_ys)
        interior = [
            (cy, bulge)
            for cx, cy, bulge in plan.arches
            if abs(arch_apex_y(cy, bulge, 10) - 30.0) < 1e-9
        ]
        self.assertEqual(len(interior), 1)
        self.assertFalse(interior[0][1])
        self.assertAlmostEqual(interior[0][0], 35.0)

    def test_y0_cut_always_kept(self):
        # The y=0 cut is mandatory even when a rounded-bottom apex
        # sits on that line: it severs the factory bottom cap.
        parts = [P(50, down=True)]
        plan = build_cut_plan(114, parts, width=10, gap=5, hole_radius=1.5,
                              include_end_cut=True, method="heuristic")
        cut_ys = [y for _x, y, _l in plan.cuts]
        self.assertTrue(any(abs(y - 0.0) < 1e-9 for y in cut_ys))
        self.assertTrue(any(abs(y - 50.0) < 1e-9 for y in cut_ys))
        cx, cy, bulge_up = plan.arches[0]
        self.assertFalse(bulge_up)
        self.assertAlmostEqual(cy, 5.0)
        self.assertAlmostEqual(arch_apex_y(cy, bulge_up, 10), 0.0)
        self.assertEqual(plan.sticks[0].waste[0], (-5.0, 0.0))

    def test_piece_polygon_has_convex_caps(self):
        poly = piece_polygon(0, 10, 20, 60, True, True, n=16)
        ys = [y for x, y in poly]
        self.assertAlmostEqual(min(ys), 20.0, places=5)
        self.assertAlmostEqual(max(ys), 60.0, places=5)
        # Apex of each cap is on the centreline, not a square corner.
        bottom = min(poly, key=lambda p: p[1])
        top = max(poly, key=lambda p: p[1])
        self.assertAlmostEqual(bottom[0], 5.0, places=5)
        self.assertAlmostEqual(top[0], 5.0, places=5)

    def test_rounded_end_helper_matches_plan(self):
        arches = rounded_end_arches(5, 20, 70, 10, True, True)
        self.assertEqual(arches, [(5, 25.0, False), (5, 65.0, True)])



    def test_usable_length_and_capacity(self):
        self.assertAlmostEqual(usable_length(114, 10), 109.0)
        y_lo, y_hi = stick_y_bounds(114, 10)
        self.assertAlmostEqual(y_lo, -5.0)
        self.assertAlmostEqual(y_hi, 109.0)
        # A 109 mm piece fills the usable span; 110 mm does not fit.
        plan_ok = build_cut_plan(114, [P(109)], 10, 5, 1.5, method="heuristic")
        self.assertEqual(len(plan_ok.sticks), 1)
        self.assertEqual(plan_ok.unplaced, [])
        self.assertAlmostEqual(plan_ok.waste_length(), 5.0)
        self.assertAlmostEqual(plan_ok.waste_percent(), 100.0 * 5.0 / 114.0)
        plan_long = build_cut_plan(114, [P(110)], 10, 5, 1.5, method="heuristic")
        self.assertEqual(plan_long.unplaced, [0])
        self.assertEqual(plan_long.sticks, [])

    def test_two_57s_need_two_sticks_on_default_stock(self):
        # Previously 57+57=114 filled one stick. After cutting off
        # the 5 mm bottom cap, usable is 109, so two sticks are needed.
        parts = [P(57), P(57)]
        plan = build_cut_plan(114, parts, 10, 5, 1.5, method="heuristic")
        self.assertEqual(len(plan.sticks), 2)
        self.assertEqual(plan.unplaced, [])
        # Each stick: bottom cap 5 + leftover 109-57=52 => 57 mm waste.
        self.assertAlmostEqual(plan.waste_length(), 114.0)
        self.assertAlmostEqual(plan.waste_percent(), 50.0)

    def test_y0_cut_present_when_end_cuts_disabled(self):
        parts = [P(40)]
        plan = build_cut_plan(
            114, parts, 10, 5, 1.5,
            include_end_cut=False, method="heuristic",
        )
        cut_ys = [y for _x, y, _l in plan.cuts]
        self.assertTrue(any(abs(y - 0.0) < 1e-9 for y in cut_ys), cut_ys)
        # Leftover at the top of the usable span: no tip cut at L-r.
        self.assertFalse(any(abs(y - 109.0) < 1e-9 for y in cut_ys), cut_ys)

    def test_stadium_slice_extends_below_axis(self):
        poly = stadium_slice_polygon(0, 10, 114, -5, 109)
        ys = [y for x, y in poly]
        xs = [x for x, y in poly]
        self.assertAlmostEqual(min(ys), -5.0, places=5)
        self.assertAlmostEqual(max(ys), 109.0, places=5)
        # Apex of the bottom cap is on the centreline at y=-r.
        bottom = min(poly, key=lambda p: p[1])
        self.assertAlmostEqual(bottom[0], 5.0, places=5)
        self.assertAlmostEqual(bottom[1], -5.0, places=5)
        # At y=0 (cap diameter) the slice is full width.
        at_axis = [x for x, y in poly if abs(y) < 1e-8]
        self.assertTrue(any(abs(x - 0.0) < 1e-6 for x in at_axis))
        self.assertTrue(any(abs(x - 10.0) < 1e-6 for x in at_axis))
        # Waste slice of just the bottom cap stays below the axis.
        cap = stadium_slice_polygon(0, 10, 114, -5, 0)
        self.assertAlmostEqual(min(y for x, y in cap), -5.0, places=5)
        self.assertAlmostEqual(max(y for x, y in cap), 0.0, places=5)
        self.assertTrue(all(y <= 1e-9 for x, y in cap))


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
        self.assertIn("G2 ", text)  # hole
        self.assertIn("G3 ", text)  # rounded bottom bulges -Y
        self.assertTrue(text.strip().endswith("; END"))

    def _arch_moves(self, text, width=10.0):
        """Return (cmd, x0, y0, x1, y1, i, j) for rounded-cap G2/G3 moves."""
        lines = []
        for ln in text.splitlines():
            ln = ln.split(";", 1)[0].strip()
            if ln:
                lines.append(ln)
        out = []
        last_xy = (None, None)
        half = width / 2.0
        for ln in lines:
            parts = ln.replace("G0+", "G0 ").split()
            cmd = parts[0].upper()
            coords = {}
            for tok in parts[1:]:
                coords[tok[0].upper()] = float(tok[1:])
            if cmd in ("G0", "G00") and "X" in coords:
                last_xy = (coords.get("X", last_xy[0]), coords.get("Y", last_xy[1]))
            if cmd in ("G2", "G3", "G02", "G03") and abs(coords.get("I", 0) - half) < 1e-6:
                x1, y1 = coords["X"], coords["Y"]
                out.append((cmd[:2], last_xy[0], last_xy[1], x1, y1,
                            coords.get("I", 0.0), coords.get("J", 0.0)))
                last_xy = (x1, y1)
        return out

    def test_gcode_bottom_arc_bulges_down(self):
        # Interior piece with only a rounded bottom: G3 from left to right.
        parts = [P(40), P(40, down=True)]
        plan = build_cut_plan(100, parts, 10, 5, 1.5, method="heuristic")
        # Find the rounded piece placement.
        rounded = [p for s in plan.sticks for p in s.placements if p.is_cut_down]
        self.assertEqual(len(rounded), 1)
        y0 = rounded[0].y_start
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "cut_plan.gcode")
            export_gcode_extended(plan, path, feedrate=250, power=1000)
            with open(path, encoding="utf-8") as fh:
                text = fh.read()
        moves = self._arch_moves(text, width=10)
        self.assertEqual(len(moves), 1)
        cmd, x0, y0c, x1, y1, i, j = moves[0]
        self.assertEqual(cmd, "G3")
        self.assertAlmostEqual(y0c, y0 + 5.0)
        self.assertAlmostEqual(y1, y0 + 5.0)
        self.assertAlmostEqual(x1 - x0, 10.0)
        self.assertAlmostEqual(i, 5.0)
        self.assertAlmostEqual(j, 0.0)
        # CCW from left to right, Y up, bulges toward y0 (down).
        self.assertAlmostEqual(y0c - 5.0, y0)

    def test_gcode_top_arc_bulges_up(self):
        parts = [P(40, up=True), P(40)]
        plan = build_cut_plan(100, parts, 10, 5, 1.5, method="heuristic")
        rounded = [p for s in plan.sticks for p in s.placements if p.is_cut_up]
        self.assertEqual(len(rounded), 1)
        y1p = rounded[0].y_end
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "cut_plan.gcode")
            export_gcode_extended(plan, path, feedrate=250, power=1000)
            with open(path, encoding="utf-8") as fh:
                text = fh.read()
        moves = self._arch_moves(text, width=10)
        self.assertEqual(len(moves), 1)
        cmd, x0, yc, x1, y1, i, j = moves[0]
        self.assertEqual(cmd, "G2")
        self.assertAlmostEqual(yc, y1p - 5.0)
        self.assertAlmostEqual(y1, y1p - 5.0)
        self.assertAlmostEqual(x1 - x0, 10.0)
        self.assertAlmostEqual(i, 5.0)
        self.assertAlmostEqual(j, 0.0)


    def test_gcode_includes_y0_cut(self):
        parts = [P(50)]
        plan = build_cut_plan(114, parts, 10, 5, 1.5, method="heuristic")
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "cut_plan.gcode")
            export_gcode_extended(plan, path, feedrate=250, power=1000)
            with open(path, encoding="utf-8") as fh:
                text = fh.read()
        self.assertIn("G0 X-1.000 Y0.000", text)
        self.assertIn("G1 X11.000 Y0.000 F250", text)
        # Toolpaths stay at y >= 0; the factory cap below the axis
        # is severed by this cut rather than traced.
        for ln in text.splitlines():
            if " Y-" in ln.split(";", 1)[0]:
                self.fail(f"unexpected negative Y in G-code: {ln}")



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

    def test_compact_cards_single_row(self):
        import tkinter as tk
        from engraver_ctrl.tab_small_parts import SmallPartsTab

        class Host:
            font = None
            root = self.root

        tab = SmallPartsTab(self.root, Host())
        tab.pack(fill="both", expand=True)
        sample = "50, 1, 0, 10, 30\n70, 0, 1, 20\n40, 1, 1\n"
        tab.text_parts.delete("1.0", "end")
        tab.text_parts.insert("1.0", sample)
        tab.mode_var.set("cards")
        tab.on_mode_change()
        self.root.update_idletasks()

        self.assertFalse(hasattr(tab, "help_label"))
        self.assertEqual(len(tab._cards), 3)
        self.assertEqual(tab._cards[0].title.cget("text"), "#1")
        self.assertEqual(tab._cards[2].title.cget("text"), "#3")

        card = tab._cards[0]
        # Every field lives on one packed row.
        self.assertEqual(len(card.frame.winfo_children()), 1)
        labels = []
        for w in card.row.winfo_children():
            try:
                labels.append(str(w.cget("text")))
            except tk.TclError:
                pass
        self.assertIn("Len", labels)
        self.assertIn("Bot", labels)
        self.assertIn("Top", labels)
        self.assertIn("Holes", labels)
        self.assertIn("Dup", labels)
        self.assertIn("✕", labels)
        self.assertNotIn("Length (mm)", labels)
        self.assertNotIn("Round bottom", labels)
        tab.destroy()

    def test_duplicate_card_inserts_copy_and_syncs_text(self):
        from engraver_ctrl.tab_small_parts import SmallPartsTab

        class Host:
            font = None
            root = self.root

        tab = SmallPartsTab(self.root, Host())
        sample = "50, 1, 0, 10, 30\n70, 0, 1, 20\n40, 1, 1\n"
        tab.text_parts.delete("1.0", "end")
        tab.text_parts.insert("1.0", sample)
        tab.mode_var.set("cards")
        tab.on_mode_change()
        self.assertEqual(len(tab._cards), 3)

        tab._duplicate_card(tab._cards[0])
        self.assertEqual(len(tab._cards), 4)
        self.assertEqual(tab._cards[0].title.cget("text"), "#1")
        self.assertEqual(tab._cards[1].title.cget("text"), "#2")
        self.assertEqual(tab._cards[2].title.cget("text"), "#3")
        self.assertEqual(tab._cards[3].title.cget("text"), "#4")
        # Copy sits directly below the source and matches Len/Bot/Top/Holes.
        self.assertEqual(tab._cards[1].length_var.get(), "50")
        self.assertTrue(tab._cards[1].down_var.get())
        self.assertFalse(tab._cards[1].up_var.get())
        self.assertEqual(tab._cards[1].holes_var.get(), "10, 30")
        # Later cards shifted down and kept their values.
        self.assertEqual(tab._cards[2].length_var.get(), "70")
        self.assertEqual(tab._cards[3].length_var.get(), "40")
        # Text buffer stays in sync while still in Cards mode.
        again = parse_parts_text(tab.text_parts.get("1.0", "end"))
        self.assertEqual([p.length for p in again], [50.0, 50.0, 70.0, 40.0])
        self.assertTrue(again[1].is_cut_down and not again[1].is_cut_up)
        self.assertEqual(again[1].hole_centers, [10.0, 30.0])

        tab.mode_var.set("text")
        tab.on_mode_change()
        switched = parse_parts_text(tab.text_parts.get("1.0", "end"))
        self.assertEqual([p.length for p in switched], [50.0, 50.0, 70.0, 40.0])
        tab.destroy()

    def test_help_popup(self):
        from engraver_ctrl.tab_small_parts import (
            HELP_TEXT, SmallPartsTab,
        )

        class Host:
            font = None
            root = self.root

        tab = SmallPartsTab(self.root, Host())
        tab.pack(fill="both", expand=True)
        self.root.geometry("800x600+0+0")
        self.root.deiconify()
        self.root.update()
        self.assertFalse(hasattr(tab, "help_label"))
        self.assertIn("length, round_bottom, round_top", HELP_TEXT)
        self.assertIn("Cards mode", HELP_TEXT)
        self.assertIn("Stock Length", HELP_TEXT)
        self.assertIn("Kerf is ignored", HELP_TEXT)

        help_win = tab.show_help()
        self.root.update()
        self.root.update_idletasks()
        self.assertTrue(help_win.winfo_exists())
        self.assertEqual(help_win.title(), "Format Help")
        body = help_win.help_text.get("1.0", "end")
        self.assertIn("50, 1, 0, 10, 30", body)
        self.assertIn("Bot / Top", body)
        self.assertIn("Feedrate", body)
        self.assertEqual(str(help_win.help_text.cget("state")), "disabled")
        self.assertIn("yview", str(help_win.help_scroll.cget("command")))
        first = help_win.help_text.yview()
        help_win.help_text.configure(state="normal")
        help_win.help_text.yview_moveto(1.0)
        self.root.update_idletasks()
        after = help_win.help_text.yview()
        help_win.help_text.configure(state="disabled")
        self.assertNotEqual(first, after)
        geom = help_win.geometry()
        self.assertTrue(geom.startswith("520x360"), geom)
        self.assertTrue(help_win.resizable()[0] and help_win.resizable()[1])
        self.assertEqual(str(help_win.close_btn.cget("text")), "Close")
        again = tab.show_help()
        self.assertEqual(again, help_win)
        # Esc closes the popup
        help_win.event_generate("<Escape>")
        self.root.update_idletasks()
        self.assertFalse(help_win.winfo_exists())
        self.assertIsNone(tab._help_win)
        tab.destroy()
        self.root.withdraw()



class SimulateNegativeYTests(unittest.TestCase):
    """Simulate/Machine preview must accept toolpaths with Y < 0."""

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

    def test_bounds_and_transform_include_negative_y(self):
        from engraver_ctrl.tab_simulate import TabSimulate
        from engraver_ctrl.sim_time import StepTimes

        class Host:
            font = None
            root = self.root

        tab = TabSimulate(self.root, Host())
        gcode = (
            "G21\nG90\nG0 X0 Y0\n"
            "G0 X0 Y-5\nM3 S1000\n"
            "G1 X10 Y-5 F250\nM5\n"
            "G0 X0 Y20\nM3 S1000\n"
            "G1 X10 Y20 F250\nM5\n"
            "G0 X0 Y0\n"
        )
        tab.steps = tab.parse_gcode(gcode)
        self.assertTrue(tab.steps)
        tab.calculate_bounds()
        self.assertLess(tab.min_y, 0)
        self.assertAlmostEqual(tab.min_y, -5.0)
        self.assertAlmostEqual(tab.max_y, 20.0)
        tab.recompute_transform()
        # Higher machine Y must appear higher (smaller canvas y).
        _sx0, sy_low = tab.transform(0, -5)
        _sx1, sy_high = tab.transform(0, 20)
        self.assertLess(sy_high, sy_low)
        seconds = StepTimes(tab.steps).total
        self.assertGreater(seconds, 0)
        tab.destroy()


if __name__ == "__main__":
    unittest.main()
