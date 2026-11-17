#!/usr/bin/env python3
"""Auto-joint J marks and Apply joints expansion."""

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

EXAMPLE = """ADD 0 0 p1
R 0 0 20 20
J 0 0 20 3 A
END
ADD 30 0 p2
R 0 0 20 40
J 0 18.5 20 3 A
END
"""

BOTH_EDGE = """ADD 0 0 p1
R 0 0 20 20
J 0 0 20 3 A
END
ADD 30 0 p2
R 0 0 20 20
J 0 17 20 3 A
END
"""

BOTH_INTERIOR = """ADD 0 0 p1
R 0 0 20 40
J 0 10 20 3 A
END
ADD 30 0 p2
R 0 0 20 40
J 0 18.5 20 3 A
END
"""

UNPAIRED = """ADD 0 0 p1
R 0 0 20 20
J 0 0 20 3 A
END
"""

ROTATE = """ADD 0 0 p1
R 0 0 20 20
J 0 0 20 3 A
END
ADD 40 0 p2
ROTATE 90
R 0 0 20 20
J 0 0 20 3 A
END
END
"""


class JointHelperTests(unittest.TestCase):
    def test_example_edge_interior_roles_and_rect(self):
        from engraver_ctrl.dsl_joint import (
            apply_joints, choose_teeth, classify_mark, parse_joint_file,
        )
        marks, outlines, _ = parse_joint_file(EXAMPLE)
        self.assertEqual(len(marks), 2)
        self.assertEqual(classify_mark(marks[0], outlines)[0], "edge")
        self.assertEqual(classify_mark(marks[1], outlines)[0], "interior")
        result = apply_joints(EXAMPLE)
        self.assertEqual(result.applied, 1)
        self.assertEqual(result.skipped, 0)
        self.assertIn("JM 0 0 20 3 4 4 in", result.text)
        # J region rect 0 18.5 20 3 is also the JF rectangle
        self.assertIn("JF 0 18.5 20 3 4 4", result.text)
        self.assertIn("# J 0 0 20 3 A", result.text)
        self.assertIn("# J 0 18.5 20 3 A", result.text)
        # Outlines stay; only J lines are commented and JM/JF inserted
        self.assertIn("R 0 0 20 20", result.text)
        self.assertIn("R 0 0 20 40", result.text)
        self.assertNotIn("# R 0 0 20 20", result.text)
        self.assertNotIn("\nL ", result.text)
        teeth, first_d = choose_teeth(20)
        self.assertEqual(teeth, 4.0)
        self.assertEqual(first_d, 4.0)
        self.assertFalse(any(w.level == "error" for w in result.warnings))

    def test_both_edge_defaults_first_male_second_female(self):
        from engraver_ctrl.dsl_joint import apply_joints
        result = apply_joints(BOTH_EDGE)
        self.assertEqual(result.applied, 1)
        # First mark (p1 bottom) -> JM; second (p2 top) -> JF at the J rect
        self.assertIn("JM 0 0 20 3 4 4 in", result.text)
        self.assertIn("JF 0 17 20 3 4 4", result.text)
        # Both outlines stay
        self.assertEqual(result.text.count("R 0 0 20 20"), 2)
        self.assertNotIn("# R ", result.text)
        self.assertNotIn("\nL ", result.text)

    def test_role_override_token(self):
        from engraver_ctrl.dsl_joint import apply_joints
        dsl = """ADD 0 0 p1
R 0 0 20 20
J 0 0 20 3 A F
END
ADD 30 0 p2
R 0 0 20 20
J 0 17 20 3 A
END
"""
        result = apply_joints(dsl)
        self.assertEqual(result.applied, 1)
        self.assertIn("JF 0 0 20 3 4 4", result.text)
        self.assertIn("JM 0 17 20 3 4 4 out", result.text)

    def test_both_interior_is_error_and_not_applied(self):
        from engraver_ctrl.dsl_joint import apply_joints
        result = apply_joints(BOTH_INTERIOR)
        self.assertEqual(result.applied, 0)
        self.assertEqual(result.skipped, 1)
        self.assertIn("J 0 10 20 3 A", result.text)
        self.assertNotIn("JM ", result.text)
        self.assertNotIn("JF ", result.text)
        self.assertTrue(any(w.level == "error" and "interior" in w.message
                            for w in result.warnings))

    def test_unpaired_warning(self):
        from engraver_ctrl.dsl_joint import apply_joints
        result = apply_joints(UNPAIRED)
        self.assertEqual(result.applied, 0)
        self.assertTrue(any("only one mark" in w.message for w in result.warnings))
        self.assertIn("J 0 0 20 3 A", result.text)
        self.assertNotIn("JM ", result.text)

    def test_rotate_warning_skips_mark(self):
        from engraver_ctrl.dsl_joint import apply_joints
        result = apply_joints(ROTATE)
        self.assertEqual(result.applied, 0)
        self.assertTrue(any("ROTATE" in w.message for w in result.warnings))
        # The un-rotated mark stays a J (pair incomplete because the other
        # sits in ROTATE).
        self.assertIn("J 0 0 20 3 A", result.text)
        self.assertNotIn("JM ", result.text)
        self.assertNotIn("JF ", result.text)

    def test_thickness_mismatch_warns_but_applies(self):
        from engraver_ctrl.dsl_joint import apply_joints
        dsl = """ADD 0 0 p1
R 0 0 20 20
J 0 0 20 4 A
END
ADD 30 0 p2
R 0 0 20 40
J 0 18 20 4 A
END
"""
        result = apply_joints(dsl)
        self.assertEqual(result.applied, 1)
        self.assertTrue(any("short side" in w.message and "4" in w.message
                            for w in result.warnings))
        self.assertIn("JF 0 18 20 4 4 4", result.text)

    def test_k_formula_default_and_custom(self):
        from engraver_ctrl.dsl_joint import (
            apply_joints, choose_teeth, normalize_teeth_divisions,
            tooth_spans, DEFAULT_TEETH_DIVISIONS,
        )
        self.assertEqual(DEFAULT_TEETH_DIVISIONS, 5)
        self.assertEqual(choose_teeth(20), (4.0, 4.0))
        self.assertEqual(choose_teeth(20, 5), (4.0, 4.0))
        self.assertEqual(choose_teeth(20, 3), (20 / 3, 20 / 3))
        self.assertEqual(choose_teeth(20, 7), (20 / 7, 20 / 7))
        self.assertIsNone(choose_teeth(0))
        self.assertIsNone(choose_teeth(20, 4))
        self.assertEqual(tooth_spans(20, 4, 4), [(4.0, 8.0), (12.0, 16.0)])
        # Symmetric: holes look the same from the other end.
        spans = tooth_spans(20, 4, 4)
        flipped = sorted((20 - b, 20 - a) for a, b in spans)
        self.assertEqual(list(spans), flipped)
        for raw, ok in (("5", 5), (5, 5), ("3", 3), (7.0, 7)):
            k, err = normalize_teeth_divisions(raw)
            self.assertEqual(k, ok)
            self.assertIsNone(err)
        for raw in ("4", 2, 1, 0, "abc", 5.5, ""):
            k, err = normalize_teeth_divisions(raw)
            self.assertIsNone(k)
            self.assertIn("odd integer", err)

        result = apply_joints(EXAMPLE, k=5)
        self.assertIn("JM 0 0 20 3 4 4 in", result.text)
        self.assertIn("JF 0 18.5 20 3 4 4", result.text)
        result3 = apply_joints(EXAMPLE, k=3)
        self.assertEqual(result3.applied, 1)
        # L=20, k=3 -> teeth = first_d = 20/3 ≈ 6.67
        self.assertIn("JM 0 0 20 3 6.67 6.67 in", result3.text)
        self.assertIn("JF 0 18.5 20 3 6.67 6.67", result3.text)
        bad = apply_joints(EXAMPLE, k=4)
        self.assertEqual(bad.applied, 0)
        self.assertEqual(bad.text, EXAMPLE)
        self.assertTrue(any("odd integer" in w.message for w in bad.warnings))

    def test_parse_text_ignores_j(self):
        from engraver_ctrl.dsl_parse import parse_text, all_segments
        with_j = EXAMPLE
        without = "".join(
            ln + "\n" for ln in EXAMPLE.splitlines()
            if not ln.strip().startswith("J ")
        )
        self.assertEqual(
            all_segments(parse_text(with_j)),
            all_segments(parse_text(without)),
        )
        cmds = [c for c, _s in parse_text(with_j)["shapes"]]
        self.assertNotIn("J", cmds)

    def test_insert_and_next_name(self):
        from engraver_ctrl.dsl_joint import insert_j_line, next_joint_name, parse_joint_file
        text = "ADD 0 0 p1\nR 0 0 20 20\nEND\n"
        marks0, _o, _w = parse_joint_file(text)
        self.assertEqual(next_joint_name(marks0), "J1")
        out = insert_j_line(text, 1, 0, 0, 20, 3, "J1")
        self.assertIn("J 0 0 20 3 J1", out)
        marks, _o, _w = parse_joint_file(out)
        self.assertEqual(next_joint_name(marks), "J1")  # unpaired, reuse
        out2 = insert_j_line(out, 1, 0, 10, 20, 3, "J1")
        marks2, _o, _w = parse_joint_file(out2)
        self.assertEqual(next_joint_name(marks2), "J2")
        # An existing unpaired custom name is still reused first
        custom = insert_j_line(text, 1, 0, 0, 20, 3, "A")
        marks_a, _o, _w = parse_joint_file(custom)
        self.assertEqual(next_joint_name(marks_a), "A")



def _stitch_polygon(segments, tol=4):
    from collections import defaultdict

    def key(p):
        return (round(p[0], tol), round(p[1], tol))

    adj = defaultdict(list)
    for x1, y1, x2, y2 in segments:
        a, b = key((x1, y1)), key((x2, y2))
        if a == b:
            continue
        adj[a].append(b)
        adj[b].append(a)
    if not adj:
        return []
    start = next(iter(adj))
    poly = [start]
    prev, curr = None, start
    for _ in range(len(segments) + 2):
        nxt = None
        for n in adj[curr]:
            if prev is not None and n == prev:
                continue
            nxt = n
            break
        if nxt is None or nxt == start:
            break
        poly.append(nxt)
        prev, curr = curr, nxt
    return poly


def _point_in_poly(px, py, poly):
    n = len(poly)
    inside = False
    j = n - 1
    for i in range(n):
        xi, yi = poly[i]
        xj, yj = poly[j]
        if (yi > py) != (yj > py):
            xint = (xj - xi) * (py - yi) / ((yj - yi) or 1e-18) + xi
            if px < xint:
                inside = not inside
        j = i
    return inside


def _iter_add_blocks(text):
    lines = text.splitlines()
    depth = 0
    started = False
    chunk = []
    for raw in lines:
        s = raw.strip()
        if not s or s.startswith("#"):
            if started:
                chunk.append(raw)
            continue
        cmd = s.split()[0]
        if cmd == "ADD":
            if not started:
                started = True
                chunk = [raw]
                depth = 1
                continue
            depth += 1
        elif cmd == "END":
            if started:
                chunk.append(raw)
                depth -= 1
                if depth == 0:
                    yield "\n".join(chunk) + "\n"
                    started = False
                    chunk = []
            continue
        if started:
            chunk.append(raw)


def _first_add_block(text):
    return next(_iter_add_blocks(text))


def _block_local(text, predicate):
    """Return one ADD block rewritten to ADD 0 0 so geometry is local."""
    for blk in _iter_add_blocks(text):
        if predicate(blk):
            lines = blk.splitlines()
            for i, raw in enumerate(lines):
                s = raw.strip()
                if s.startswith("ADD "):
                    parts = s.split()
                    label = " ".join(parts[3:]) if len(parts) > 3 else ""
                    indent = raw[:len(raw) - len(raw.lstrip())]
                    lines[i] = indent + ("ADD 0 0 " + label if label else "ADD 0 0")
                    break
            return "\n".join(lines) + "\n"
    return ""


class JointGeometryTests(unittest.TestCase):
    def test_example_tenon_not_notch_fits_jf(self):
        from engraver_ctrl.dsl_joint import apply_joints, tooth_spans
        from engraver_ctrl.dsl_parse import parse_text
        from engraver_ctrl.dsl_highlight import polygons_from_joint_segments

        result = apply_joints(EXAMPLE)
        self.assertIn("JM 0 0 20 3 4 4 in", result.text)
        spans = tooth_spans(20, 4, 4)
        self.assertEqual(spans, [(4.0, 8.0), (12.0, 16.0)])

        male = _first_add_block(result.text)
        self.assertIn("R 0 0 20 20", male)
        shapes = parse_text(male)["shapes"]
        jm = [s for c, s in shapes if c == "JM"]
        self.assertEqual(len(jm), 1)
        poly = polygons_from_joint_segments("JM", jm[0])[0]
        # Tooth material (matches the JF holes at [4,8] and [12,16])
        # is inside the JM fill; end and middle shoulders are not.
        self.assertTrue(_point_in_poly(6, 1.5, poly), poly)
        self.assertTrue(_point_in_poly(14, 1.5, poly), poly)
        self.assertFalse(_point_in_poly(2, 1.5, poly), poly)
        self.assertFalse(_point_in_poly(10, 1.5, poly), poly)
        self.assertFalse(_point_in_poly(18, 1.5, poly), poly)

        # Highlight fill is the tooth (material) region, not the notch
        jm = [s for c, s in shapes if c == "JM"]
        self.assertEqual(len(jm), 1)
        polys = polygons_from_joint_segments("JM", jm[0])
        self.assertTrue(any(_point_in_poly(6, 1.5, p) for p in polys))
        self.assertFalse(any(_point_in_poly(2, 1.5, p) for p in polys))
        self.assertFalse(any(_point_in_poly(10, 1.5, p) for p in polys))

        self.assertIn("JF 0 18.5 20 3 4 4", result.text)
        female = _block_local(result.text, lambda b: "JF " in b)
        jf_shapes = [s for c, s in parse_text(female)["shapes"] if c == "JF"]
        self.assertTrue(jf_shapes)
        jf_polys = polygons_from_joint_segments("JF", jf_shapes[0])
        self.assertEqual(len(jf_polys), 2)
        boxes = sorted(
            (min(p[0] for p in poly), max(p[0] for p in poly))
            for poly in jf_polys
        )
        self.assertAlmostEqual(boxes[0][0], 4, places=4)
        self.assertAlmostEqual(boxes[0][1], 8, places=4)
        self.assertAlmostEqual(boxes[1][0], 12, places=4)
        self.assertAlmostEqual(boxes[1][1], 16, places=4)
        self.assertTrue(any(_point_in_poly(6, 20, p) for p in jf_polys))
        self.assertTrue(any(_point_in_poly(14, 20, p) for p in jf_polys))
        self.assertFalse(any(_point_in_poly(10, 20, p) for p in jf_polys))

    def test_both_edge_mortise_slots_match_tenon(self):
        from engraver_ctrl.dsl_joint import apply_joints, tooth_spans
        from engraver_ctrl.dsl_parse import parse_text
        from engraver_ctrl.dsl_highlight import polygons_from_joint_segments

        result = apply_joints(BOTH_EDGE)
        self.assertIn("JM 0 0 20 3 4 4 in", result.text)
        self.assertIn("JF 0 17 20 3 4 4", result.text)
        self.assertEqual(tooth_spans(20, 4, 4), [(4.0, 8.0), (12.0, 16.0)])
        male = _first_add_block(result.text)
        self.assertIn("R 0 0 20 20", male)
        jm = [s for c, s in parse_text(male)["shapes"] if c == "JM"]
        poly = polygons_from_joint_segments("JM", jm[0])[0]
        self.assertTrue(_point_in_poly(6, 1.5, poly))
        self.assertTrue(_point_in_poly(14, 1.5, poly))
        self.assertFalse(_point_in_poly(2, 1.5, poly))
        self.assertFalse(_point_in_poly(10, 1.5, poly))
        female = _block_local(result.text, lambda b: "JF " in b)
        jf = [s for c, s in parse_text(female)["shapes"] if c == "JF"]
        holes = polygons_from_joint_segments("JF", jf[0])
        self.assertEqual(len(holes), 2)
        boxes = sorted(
            (min(p[0] for p in poly), max(p[0] for p in poly),
             min(p[1] for p in poly), max(p[1] for p in poly))
            for poly in holes
        )
        self.assertAlmostEqual(boxes[0][0], 4, places=4)
        self.assertAlmostEqual(boxes[0][1], 8, places=4)
        self.assertAlmostEqual(boxes[1][0], 12, places=4)
        self.assertAlmostEqual(boxes[1][1], 16, places=4)
        self.assertAlmostEqual(boxes[0][2], 17, places=4)
        self.assertAlmostEqual(boxes[0][3], 20, places=4)
        self.assertTrue(any(_point_in_poly(6, 18.5, h) for h in holes))
        self.assertFalse(any(_point_in_poly(10, 18.5, h) for h in holes))

    def test_all_four_edge_orientations_are_tenons(self):
        from engraver_ctrl.dsl_joint import apply_joints
        from engraver_ctrl.dsl_parse import parse_text
        from engraver_ctrl.dsl_highlight import polygons_from_joint_segments

        cases = [
            ("bottom", "J 0 0 20 3 A", "in", (6, 1.5), (2, 1.5),
             "J 0 18.5 20 3 A", "R 0 0 20 40"),
            ("top", "J 0 17 20 3 A", "out", (6, 18.5), (2, 18.5),
             "J 0 18.5 20 3 A", "R 0 0 20 40"),
            ("left", "J 0 0 3 20 A", "in", (1.5, 6), (1.5, 2),
             "J 18.5 0 3 20 A", "R 0 0 40 20"),
            ("right", "J 17 0 3 20 A", "out", (18.5, 6), (18.5, 2),
             "J 18.5 0 3 20 A", "R 0 0 40 20"),
        ]
        for name, jline, direction, tooth, shoulder, fj, fr in cases:
            dsl = (
                f"ADD 0 0 male\nR 0 0 20 20\n{jline}\nEND\n"
                f"ADD 40 0 female\n{fr}\n{fj}\nEND\n"
            )
            result = apply_joints(dsl)
            self.assertEqual(result.applied, 1, (name, result.warnings, result.text))
            self.assertTrue(
                any(f" {direction}" in ln and ln.strip().startswith("JM ")
                    for ln in result.text.splitlines()),
                (name, result.text),
            )
            male = _first_add_block(result.text)
            self.assertIn("R 0 0 20 20", male)
            jm = [s for c, s in parse_text(male)["shapes"] if c == "JM"]
            poly = polygons_from_joint_segments("JM", jm[0])[0]
            self.assertTrue(_point_in_poly(*tooth, poly), (name, tooth, poly))
            self.assertFalse(_point_in_poly(*shoulder, poly), (name, shoulder, poly))


class JointTkTests(unittest.TestCase):
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

    def _gcode(self, tab, dsl):
        from engraver_ctrl import tab_designer as td
        tab.text_input.delete("1.0", "end")
        tab.text_input.insert("1.0", dsl)
        with patch.object(td, "CUT_PLAN_GCODE_PATH", os.devnull), \
             patch.object(td.messagebox, "showinfo"), \
             patch.object(td.messagebox, "showerror"):
            # Write to a real temp file instead of os.devnull for reading
            import tempfile
            fd, path = tempfile.mkstemp(suffix=".gcode")
            os.close(fd)
            try:
                with patch.object(td, "CUT_PLAN_GCODE_PATH", path):
                    tab.generate_gcode()
                return Path(path).read_bytes()
            finally:
                try:
                    os.remove(path)
                except OSError:
                    pass

    def test_gcode_ignores_j_marks(self):
        win, tab = self._make_tab()
        try:
            with_j = EXAMPLE
            without = "\n".join(
                ln for ln in EXAMPLE.splitlines() if not ln.strip().startswith("J ")
            ) + "\n"
            self.assertEqual(self._gcode(tab, with_j), self._gcode(tab, without))
        finally:
            win.destroy()

    def test_canvas_draws_marks_and_apply_button(self):
        win, tab = self._make_tab()
        try:
            self.assertTrue(hasattr(tab, "apply_joints"))
            tab.text_input.delete("1.0", "end")
            tab.text_input.insert("1.0", EXAMPLE)
            tab.preview()
            self.root.update_idletasks()
            items = list(tab.canvas.find_all())
            tags = [tab.canvas.gettags(i) for i in items]
            flat = [t for group in tags for t in group]
            self.assertTrue(any(t == "jmark" or t.startswith("jmark") for t in flat),
                            flat[:40])
            tab.apply_joints()
            text = tab.text_input.get("1.0", "end")
            self.assertIn("JM 0 0 20 3 4 4 in", text)
            self.assertIn("JF 0 18.5 20 3 4 4", text)
            tab.preview()
            self.root.update_idletasks()
            # After apply, J marks are commented so no jmark overlays
            items = list(tab.canvas.find_all())
            flat = [t for i in items for t in tab.canvas.gettags(i)]
            self.assertFalse(any(t == "jmark" or t.startswith("jmark")
                                 for t in flat if t != "jmjf_hl"))
            # Highlights for the new JM/JF should be present
            self.assertTrue(any("jmjf_hl" in tab.canvas.gettags(i) for i in items))
            self.assertIn("R 0 0 20 20", text)
            self.assertNotIn("# R ", text)
        finally:
            win.destroy()

    def test_joints_panel_k_default_and_apply(self):
        win, tab = self._make_tab()
        try:
            self.assertEqual(tab.teeth_k_var.get(), "5")
            tab.text_input.delete("1.0", "end")
            tab.text_input.insert("1.0", EXAMPLE)
            tab.apply_joints()
            text = tab.text_input.get("1.0", "end")
            self.assertIn("JM 0 0 20 3 4 4 in", text)
            self.assertIn("JF 0 18.5 20 3 4 4", text)
            # Invalid k is rejected and leaves the DSL unchanged
            tab.text_input.delete("1.0", "end")
            tab.text_input.insert("1.0", EXAMPLE)
            tab.teeth_k_var.set("4")
            from unittest.mock import patch
            with patch("engraver_ctrl.tab_designer.messagebox.showerror"):
                tab.apply_joints()
            self.assertIn("J 0 0 20 3 A", tab.text_input.get("1.0", "end"))
            self.assertNotIn("JM ", tab.text_input.get("1.0", "end"))
        finally:
            win.destroy()

    def test_gcode_merges_r_edge_and_jm_tooth_tip(self):
        """R bottom (0,0)-(20,0) overlaps JM tooth tips [4,8] and [12,16].

        _remove_duplicate_segments only drops exact same-endpoint copies,
        so the short tips remain until _merge_collinear_overlaps folds them
        into the full edge. G-code then cuts y=0 once from x=0 to x=20.
        """
        from engraver_ctrl.dsl_joint import apply_joints

        win, tab = self._make_tab()
        try:
            dsl = apply_joints(EXAMPLE).text
            self.assertIn("R 0 0 20 20", dsl)
            self.assertIn("JM 0 0 20 3 4 4 in", dsl)
            tab.text_input.delete("1.0", "end")
            tab.text_input.insert("1.0", dsl)
            tab.preview()
            raw = tab._shapes_to_segments()

            def on_y0(seg, xlo, xhi):
                x1, y1, x2, y2 = seg
                xs = sorted((x1, x2))
                return (abs(y1) < 1e-6 and abs(y2) < 1e-6
                        and abs(xs[0] - xlo) < 1e-6 and abs(xs[1] - xhi) < 1e-6)

            self.assertTrue(any(on_y0(s, 0, 20) for s in raw), raw)
            self.assertTrue(any(on_y0(s, 4, 8) for s in raw), raw)
            self.assertTrue(any(on_y0(s, 12, 16) for s in raw), raw)
            merged = tab._merge_collinear_overlaps(
                tab._remove_duplicate_segments(raw)
            )
            y0 = [s for s in merged
                  if abs(s[1]) < 1e-6 and abs(s[3]) < 1e-6
                  and min(s[0], s[2]) < 25]  # p1, not p2 at x=30
            self.assertEqual(len(y0), 1, y0)
            xs = sorted((y0[0][0], y0[0][2]))
            self.assertAlmostEqual(xs[0], 0, places=6)
            self.assertAlmostEqual(xs[1], 20, places=6)
            self.assertFalse(any(on_y0(s, 4, 8) for s in merged))
            self.assertFalse(any(on_y0(s, 12, 16) for s in merged))

            gcode = self._gcode(tab, dsl).decode()
            # The segment list is already one merged 0-20 edge. G-code may
            # still name the comb vertices that lie on y=0 (tooth corners
            # at 4, 8, 12, 16) as waypoints of that same pass.
            y0_cuts = []
            for ln in gcode.splitlines():
                if not ln.startswith("G1 "):
                    continue
                if "Y0.000" in ln and "X" in ln:
                    # keep cuts whose X is in [0, 20]
                    try:
                        x = float([p[1:] for p in ln.split() if p.startswith("X")][0])
                    except (IndexError, ValueError):
                        continue
                    if 0 <= x <= 20 + 1e-6:
                        y0_cuts.append(ln)
            self.assertTrue(y0_cuts, gcode)
            self.assertLessEqual(len(y0_cuts), 8, y0_cuts)
        finally:
            win.destroy()


if __name__ == "__main__":
    unittest.main()
