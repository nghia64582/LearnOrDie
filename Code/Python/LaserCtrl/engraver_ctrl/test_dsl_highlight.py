#!/usr/bin/env python3
"""Preview-only JM/JF highlight helper, plus G-code unchanged check."""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

_HERE = Path(__file__).resolve().parent
_ROOT = _HERE.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

SAMPLE_PATH = _HERE / "testdata" / "jmjf_highlight_sample.dsl"
GOLDEN_GCODE = _HERE / "testdata" / "jmjf_highlight_sample.gcode"


def _sample_dsl():
    return SAMPLE_PATH.read_text(encoding="utf-8")


def _almost_pts(a, b, places=6):
    if len(a) != len(b):
        return False
    return all(
        round(x1, places) == round(x2, places)
        and round(y1, places) == round(y2, places)
        for (x1, y1), (x2, y2) in zip(a, b)
    )


class HighlightHelperTests(unittest.TestCase):
    def test_jf_tooth_rectangles(self):
        from engraver_ctrl.dsl_highlight import joint_highlights

        hls = joint_highlights("JF 10 0 3 100 10 0\n")
        self.assertEqual(len(hls), 5)
        self.assertTrue(all(h.kind == "JF" for h in hls))
        self.assertTrue(_almost_pts(
            hls[0].polygon,
            ((10.0, 0.0), (10.0, 10.0), (13.0, 10.0), (13.0, 0.0)),
        ))

    def test_jm_closed_comb(self):
        from engraver_ctrl.dsl_highlight import joint_highlights

        hls = joint_highlights("JM 17 0 3 100 10 0 out\n")
        self.assertEqual(len(hls), 1)
        self.assertEqual(hls[0].kind, "JM")
        poly = hls[0].polygon
        self.assertGreaterEqual(len(poly), 4)
        self.assertTrue(_almost_pts(poly[:4], (
            (17.0, 0.0), (20.0, 0.0), (20.0, 10.0), (17.0, 10.0),
        )))
        # Closed comb ends on the base at the far end of the strip.
        self.assertAlmostEqual(poly[-1][0], 17.0, places=6)
        self.assertAlmostEqual(poly[-1][1], 100.0, places=6)

    def test_add_rotate90_transforms_footprint(self):
        from engraver_ctrl.dsl_highlight import joint_highlights

        dsl = "ADD 80 20 blockA\nROTATE 90\nJF 0 0 80 3 8 4\nEND\nEND\n"
        hls = joint_highlights(dsl)
        self.assertGreaterEqual(len(hls), 1)
        self.assertEqual(hls[0].kind, "JF")
        # Clockwise 90 about origin, then + (80, 20): (4, 0) -> (80, 16)
        self.assertTrue(_almost_pts(
            hls[0].polygon[:2],
            ((80.0, 16.0), (80.0, 8.0)),
        ))

    def test_helper_matches_segment_rebuild(self):
        from engraver_ctrl.dsl_highlight import (
            joint_highlights,
            polygons_from_joint_segments,
        )
        from engraver_ctrl.dsl_parse import parse_text

        dsl = _sample_dsl()
        from_text = joint_highlights(dsl)
        from_segs = []
        for cmd, segs in parse_text(dsl)["shapes"]:
            if cmd not in ("JM", "JF"):
                continue
            for poly in polygons_from_joint_segments(cmd, segs):
                from_segs.append((cmd, poly))
        self.assertEqual(len(from_text), len(from_segs))
        for hl, (cmd, poly) in zip(from_text, from_segs):
            self.assertEqual(hl.kind, cmd)
            self.assertTrue(_almost_pts(hl.polygon, poly), (hl.polygon, poly))

    def test_colors_configured_in_ui(self):
        from common.ui import JF_HIGHLIGHT, JM_HIGHLIGHT

        self.assertTrue(JM_HIGHLIGHT.startswith("#"))
        self.assertTrue(JF_HIGHLIGHT.startswith("#"))
        self.assertNotEqual(JM_HIGHLIGHT, JF_HIGHLIGHT)

    def test_jf_holes_bbox_matches_rectangle(self):
        from engraver_ctrl.dsl_highlight import joint_highlights
        from engraver_ctrl.dsl_parse import parse_text, segments_bbox

        # One tooth filling the whole strip: union bbox == the rectangle.
        cases = [
            ("JF 0 0 20 3 20 0\n", 0, 0, 20, 3),
            ("JF 5 8 3 40 40 0\n", 5, 8, 3, 40),
        ]
        for dsl, x, y, w, h in cases:
            with self.subTest(dsl=dsl.strip()):
                hls = joint_highlights(dsl)
                self.assertTrue(hls)
                xs = [px for hl in hls for px, _py in hl.polygon]
                ys = [py for hl in hls for _px, py in hl.polygon]
                self.assertAlmostEqual(min(xs), x, places=6)
                self.assertAlmostEqual(max(xs), x + w, places=6)
                self.assertAlmostEqual(min(ys), y, places=6)
                self.assertAlmostEqual(max(ys), y + h, places=6)
                segs = parse_text(dsl)["shapes"][0][1]
                bbox = segments_bbox(segs)
                self.assertAlmostEqual(bbox[0], x, places=6)
                self.assertAlmostEqual(bbox[1], y, places=6)
                self.assertAlmostEqual(bbox[2], x + w, places=6)
                self.assertAlmostEqual(bbox[3], y + h, places=6)

        # Typical multi-hole strip: every vertex stays inside the rectangle
        # and the holes span the full short side (thickness).
        dsl = "JF 10 20 50 3 10 5\n"
        hls = joint_highlights(dsl)
        self.assertGreaterEqual(len(hls), 1)
        xs = [px for hl in hls for px, _py in hl.polygon]
        ys = [py for hl in hls for _px, py in hl.polygon]
        self.assertGreaterEqual(min(xs), 10 - 1e-9)
        self.assertLessEqual(max(xs), 60 + 1e-9)
        self.assertAlmostEqual(min(ys), 20, places=6)
        self.assertAlmostEqual(max(ys), 23, places=6)

    def test_jf_jm_same_params_share_rectangle(self):
        from engraver_ctrl.dsl_highlight import joint_highlights

        jf = joint_highlights("JF 0 0 20 3 10 5\n")
        jm = joint_highlights("JM 0 0 20 3 10 5 out\n")
        self.assertEqual(len(jf), 1)
        self.assertEqual(len(jm), 1)
        jfx = [p[0] for p in jf[0].polygon]
        jfy = [p[1] for p in jf[0].polygon]
        jmx = [p[0] for p in jm[0].polygon]
        jmy = [p[1] for p in jm[0].polygon]
        self.assertAlmostEqual(min(jfx), 5, places=6)
        self.assertAlmostEqual(max(jfx), 15, places=6)
        self.assertAlmostEqual(min(jfy), 0, places=6)
        self.assertAlmostEqual(max(jfy), 3, places=6)
        # JM comb occupies the same rectangle as the JF holes.
        self.assertAlmostEqual(min(jmx), 0, places=6)
        self.assertAlmostEqual(max(jmx), 20, places=6)
        self.assertAlmostEqual(min(jmy), 0, places=6)
        self.assertAlmostEqual(max(jmy), 3, places=6)

    def test_invalid_and_non_joint_ignored(self):
        from engraver_ctrl.dsl_highlight import joint_highlights

        self.assertEqual(joint_highlights("R 0 0 10 10\nC 1 1 2\n"), [])
        self.assertEqual(joint_highlights("JF 10 0 3 100\n"), [])
        self.assertEqual(joint_highlights("JM 17 0 3 100 10 0 sideways\n"), [])


class GcodeUnchangedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import tkinter as tk
        from common.ui import enable_dpi_awareness, init_fonts

        enable_dpi_awareness()
        cls.root = tk.Tk()
        cls.root.withdraw()
        init_fonts(cls.root, size=10)

    @classmethod
    def tearDownClass(cls):
        try:
            cls.root.destroy()
        except Exception:
            pass

    def _make_tab(self):
        import tkinter as tk
        from tkinter import ttk
        from engraver_ctrl.tab_designer import DesignerTab

        class Host:
            font = None
            ser = None

        win = tk.Toplevel(self.root)
        win.withdraw()
        nb = ttk.Notebook(win)
        tab = DesignerTab(nb, Host())
        return win, tab

    def test_gcode_byte_identical_to_pre_highlight_golden(self):
        import tempfile
        from engraver_ctrl import tab_designer as td

        win, tab = self._make_tab()
        try:
            tab.text_input.delete("1.0", "end")
            tab.text_input.insert("1.0", _sample_dsl())
            with tempfile.TemporaryDirectory() as tmp:
                out = os.path.join(tmp, "cut_plan.gcode")
                with patch.object(td, "CUT_PLAN_GCODE_PATH", out), \
                     patch.object(td.messagebox, "showinfo"), \
                     patch.object(td.messagebox, "showerror"):
                    tab.generate_gcode()
                got = Path(out).read_bytes()
            golden = GOLDEN_GCODE.read_bytes()
            self.assertEqual(got, golden)
        finally:
            win.destroy()

    def test_custom_canvas_fills_sit_under_paths(self):
        win, tab = self._make_tab()
        try:
            tab.text_input.delete("1.0", "end")
            tab.text_input.insert("1.0", _sample_dsl())
            tab.preview()
            self.root.update_idletasks()
            items = list(tab.canvas.find_all())
            hl = [i for i in items if "jmjf_hl" in tab.canvas.gettags(i)]
            lines = [
                i for i in items
                if tab.canvas.type(i) == "line"
                and any(t.startswith("shape") for t in tab.canvas.gettags(i))
            ]
            self.assertTrue(hl, "expected JM/JF highlight polygons")
            self.assertTrue(lines, "expected G-code path lines")
            # find_all is bottom-to-top stacking order.
            self.assertLess(
                max(items.index(i) for i in hl),
                min(items.index(i) for i in lines),
            )
            fills = {tab.canvas.itemcget(i, "fill") for i in hl}
            from common.ui import JF_HIGHLIGHT, JM_HIGHLIGHT
            self.assertEqual(fills, {JM_HIGHLIGHT, JF_HIGHLIGHT})
        finally:
            win.destroy()

    def test_nesting_preview_draws_highlights_under_paths(self):
        import tkinter as tk
        from dsl_nesting.gui import DSLNestingPanel
        from engraver_ctrl.dsl_parse import parse_text

        win = tk.Toplevel(self.root)
        win.withdraw()
        try:
            panel = DSLNestingPanel(win)
            panel.pack(fill="both", expand=True)
            # A already-nested DSL (no need to run the solver).
            dsl = _sample_dsl()
            panel.last_dsl = dsl
            # Sheet bounds from geometry so redraw actually paints.
            xs, ys = [], []
            for _cmd, segs in parse_text(dsl)["shapes"]:
                for x1, y1, x2, y2 in segs:
                    xs.extend((x1, x2))
                    ys.extend((y1, y2))
            panel.last_dsl_W = max(xs) + 5
            panel.last_dsl_H = max(ys) + 5
            panel.dsl_canvas.config(width=640, height=420)
            self.root.update()
            panel.redraw_dsl()
            self.root.update_idletasks()
            items = list(panel.dsl_canvas.find_all())
            hl = [i for i in items if "jmjf_hl" in panel.dsl_canvas.gettags(i)]
            # Path lines are untagged; take non-grid colored lines after fills.
            lines = [
                i for i in items
                if panel.dsl_canvas.type(i) == "line"
                and panel.dsl_canvas.itemcget(i, "fill") not in ("#e2e8ee",)
            ]
            self.assertTrue(hl)
            self.assertTrue(lines)
            self.assertLess(
                max(items.index(i) for i in hl),
                min(items.index(i) for i in lines),
            )
        finally:
            win.destroy()


if __name__ == "__main__":
    unittest.main()
