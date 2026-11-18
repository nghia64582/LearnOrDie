#!/usr/bin/env python3
"""Snap, ownership, and pairing helpers for Mark joint."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_ROOT = _HERE.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from engraver_ctrl.dsl_joint import (
    apply_joints, classify_mark, next_joint_name, parse_joint_file,
)
from engraver_ctrl.dsl_mark_ux import (
    SNAP_GRID, THICKNESS,
    apply_dialog_values, collect_pieces, draft_from_drag,
    format_draft_label, owning_piece, pair_placement_error,
    pending_unpaired_mark, snap_grid, suggested_joint_name,
)

TWO_PIECES = """ADD 0 0 p1
R 0 0 20 20
END
ADD 30 0 p2
R 0 0 20 40
END
"""

NESTED = """ADD 0 0 outer
R 0 0 40 40
ADD 5 5 inner
R 0 0 10 10
END
END
"""

OVERLAP = """ADD 0 0 big
R 0 0 40 20
END
ADD 10 0 small
R 0 0 10 10
END
"""

ONE_MARK = """ADD 0 0 p1
R 0 0 20 20
J 0 0 20 3 J1
END
ADD 30 0 p2
R 0 0 20 40
END
"""

BOTH_INTERIOR_FIRST = """ADD 0 0 p1
R 0 0 20 40
J 0 10 20 3 J1
END
ADD 30 0 p2
R 0 0 20 40
END
"""


def _piece(text, add_line=None, at=None):
    pieces = collect_pieces(text)
    if at is not None:
        hit = owning_piece(pieces, at[0], at[1])
        if hit is None:
            raise AssertionError(f"no piece at {at}")
        return hit
    for p in pieces:
        if p.add_line == add_line:
            return p
    raise AssertionError(f"no piece with add_line={add_line}")


class SnapGridTests(unittest.TestCase):
    def test_nearest_millimetre(self):
        self.assertEqual(snap_grid(0.0), 0.0)
        self.assertEqual(snap_grid(1.4), 1.0)
        self.assertEqual(snap_grid(1.5), 2.0)
        self.assertEqual(snap_grid(0.5), 1.0)
        self.assertEqual(snap_grid(-0.6), -1.0)
        self.assertEqual(snap_grid(-0.5), -1.0)
        self.assertEqual(snap_grid(18.4), 18.0)
        self.assertEqual(snap_grid(18.6), 19.0)

    def test_custom_step(self):
        self.assertEqual(snap_grid(2.4, 0.5), 2.5)


class OwnershipTests(unittest.TestCase):
    def test_collects_translated_rectangles(self):
        pieces = collect_pieces(TWO_PIECES)
        self.assertEqual({p.add_line for p in pieces}, {1, 4})
        p1 = _piece(TWO_PIECES, 1)
        p2 = _piece(TWO_PIECES, 4)
        self.assertEqual(p1.add_dx, 0)
        self.assertEqual(p2.add_dx, 30)
        self.assertEqual(p1.depth, 0)
        self.assertGreater(p2.area, p1.area)

    def test_point_inside_p2(self):
        pieces = collect_pieces(TWO_PIECES)
        hit = owning_piece(pieces, 35, 10)
        self.assertIsNotNone(hit)
        self.assertEqual(hit.add_line, 4)

    def test_miss_returns_none(self):
        pieces = collect_pieces(TWO_PIECES)
        self.assertIsNone(owning_piece(pieces, 100, 100))

    def test_edge_counts_as_inside(self):
        pieces = collect_pieces(TWO_PIECES)
        hit = owning_piece(pieces, 0, 0)
        self.assertIsNotNone(hit)
        self.assertEqual(hit.add_line, 1)

    def test_nested_picks_smallest(self):
        pieces = collect_pieces(NESTED)
        inner = owning_piece(pieces, 8, 8)
        self.assertEqual(inner.add_line, 3)
        self.assertEqual(inner.depth, 1)
        outer_only = owning_piece(pieces, 1, 1)
        self.assertEqual(outer_only.add_line, 1)

    def test_overlap_picks_smaller_area(self):
        pieces = collect_pieces(OVERLAP)
        hit = owning_piece(pieces, 12, 5)
        self.assertEqual(hit.add_line, 4)
        outside_small = owning_piece(pieces, 2, 5)
        self.assertEqual(outside_small.add_line, 1)


class EdgeDraftTests(unittest.TestCase):
    def test_bottom_edge_flush_inside(self):
        piece = _piece(TWO_PIECES, 1)
        draft = draft_from_drag(piece, 0.2, 0.3, 19.6, 0.4)
        self.assertTrue(draft.valid)
        self.assertTrue(draft.on_edge)
        self.assertEqual(draft.add_line, 1)
        self.assertAlmostEqual(draft.x, 0)
        self.assertAlmostEqual(draft.y, 0)
        self.assertAlmostEqual(draft.w, 20)
        self.assertAlmostEqual(draft.h, THICKNESS)
        self.assertTrue(draft.along_x)
        self.assertEqual(draft.name, "J1")

    def test_top_edge_flush_inward(self):
        piece = _piece(TWO_PIECES, 1)
        draft = draft_from_drag(piece, 0, 19.8, 20, 20.2)
        self.assertTrue(draft.on_edge)
        self.assertAlmostEqual(draft.y, 17)  # 20 - 3, inside the piece
        self.assertAlmostEqual(draft.h, THICKNESS)
        self.assertAlmostEqual(draft.x, 0)
        self.assertAlmostEqual(draft.w, 20)

    def test_right_edge_vertical(self):
        piece = _piece(TWO_PIECES, 1)
        draft = draft_from_drag(piece, 19.8, 0, 20.1, 20)
        self.assertTrue(draft.on_edge)
        self.assertFalse(draft.along_x)
        self.assertAlmostEqual(draft.x, 17)
        self.assertAlmostEqual(draft.w, THICKNESS)
        self.assertAlmostEqual(draft.y, 0)
        self.assertAlmostEqual(draft.h, 20)

    def test_thickness_ignores_tall_drag(self):
        piece = _piece(TWO_PIECES, 1)
        draft = draft_from_drag(piece, 0, 0.2, 20, 8)
        self.assertTrue(draft.on_edge)
        self.assertAlmostEqual(draft.h, THICKNESS)
        self.assertAlmostEqual(draft.w, 20)

    def test_grid_snap_on_edge(self):
        piece = _piece(TWO_PIECES, 1)
        draft = draft_from_drag(piece, 0.4, 0.4, 10.4, 0.2)
        self.assertAlmostEqual(draft.x, 0)
        self.assertAlmostEqual(draft.w, 10)

    def test_too_small_without_pending(self):
        piece = _piece(TWO_PIECES, 1)
        draft = draft_from_drag(piece, 5, 0.1, 5.2, 0.2)
        self.assertFalse(draft.valid)
        self.assertIn("too small", draft.message)

    def test_translated_piece_uses_local_coords(self):
        piece = _piece(TWO_PIECES, 4)
        # World bottom-left of p2 is (30, 0); drag along the bottom edge.
        draft = draft_from_drag(piece, 30.1, 0.2, 50, 0.3)
        self.assertTrue(draft.on_edge)
        self.assertEqual(draft.add_line, 4)
        self.assertAlmostEqual(draft.x, 0)
        self.assertAlmostEqual(draft.y, 0)
        self.assertAlmostEqual(draft.world_x, 30)
        self.assertAlmostEqual(draft.w, 20)


class InteriorDraftTests(unittest.TestCase):
    def test_free_placement_inside_taller_piece(self):
        piece = _piece(TWO_PIECES, 4)
        # Stay more than EDGE_SNAP_MM from every side (p2 is 30..50, 0..40).
        draft = draft_from_drag(piece, 34, 18, 46, 18.2)
        self.assertFalse(draft.on_edge)
        self.assertAlmostEqual(draft.w, 12)  # 34->46 in world; local 4..16
        self.assertAlmostEqual(draft.h, THICKNESS)
        self.assertAlmostEqual(draft.world_x, 34)
        self.assertAlmostEqual(draft.h, 3)
        # Snapped start y=18 already fits; do not shift the strip.
        self.assertAlmostEqual(draft.world_y, 18)
        self.assertAlmostEqual(draft.y, 18)
        self.assertGreaterEqual(draft.y, 0)
        self.assertLessEqual(draft.y + draft.h, 40)

    def test_label_mentions_interior(self):
        piece = _piece(TWO_PIECES, 4)
        draft = draft_from_drag(piece, 34, 18, 46, 18)
        self.assertIn("interior", format_draft_label(draft))
        self.assertIn("J1", format_draft_label(draft))


class PairingTests(unittest.TestCase):
    def test_second_mark_copies_length_and_name(self):
        marks, _o, _w = parse_joint_file(ONE_MARK)
        self.assertEqual(suggested_joint_name(marks), "J1")
        self.assertEqual(pending_unpaired_mark(marks).length
                         if False else pending_unpaired_mark(marks).name, "J1")
        piece = _piece(ONE_MARK, at=(40, 18))
        # Interior of p2, short drag: length must still be 20 from J1.
        draft = draft_from_drag(piece, 34, 18, 37, 18.1, marks=marks)
        self.assertTrue(draft.copied_length)
        self.assertEqual(draft.name, "J1")
        self.assertAlmostEqual(draft.length, 20)
        self.assertAlmostEqual(draft.h, THICKNESS)
        self.assertTrue(draft.along_x)
        self.assertFalse(draft.on_edge)

    def test_second_mark_on_vertical_edge_follows_edge(self):
        marks, _o, _w = parse_joint_file(ONE_MARK)
        piece = _piece(ONE_MARK, at=(40, 18))
        # Right edge of p2 is world x=50, y=0..40. Copied length 20, vertical.
        draft = draft_from_drag(piece, 49.8, 5, 50.1, 12, marks=marks)
        self.assertTrue(draft.on_edge)
        self.assertFalse(draft.along_x)
        self.assertAlmostEqual(draft.w, THICKNESS)
        self.assertAlmostEqual(draft.h, 20)
        self.assertEqual(draft.name, "J1")

    def test_both_interior_rejected(self):
        marks, outlines, _w = parse_joint_file(BOTH_INTERIOR_FIRST)
        piece = _piece(BOTH_INTERIOR_FIRST, at=(40, 18))
        draft = draft_from_drag(piece, 34, 18, 46, 18, marks=marks)
        self.assertFalse(draft.on_edge)
        err = pair_placement_error(draft, marks, outlines)
        self.assertIsNotNone(err)
        self.assertIn("both marks in the interior", err)

    def test_edge_plus_interior_ok(self):
        marks, outlines, _w = parse_joint_file(ONE_MARK)
        self.assertEqual(classify_mark(marks[0], outlines)[0], "edge")
        piece = _piece(ONE_MARK, at=(40, 18))
        draft = draft_from_drag(piece, 34, 18, 46, 18, marks=marks)
        self.assertIsNone(pair_placement_error(draft, marks, outlines))

    def test_dialog_keeps_copied_length(self):
        marks, _o, _w = parse_joint_file(ONE_MARK)
        piece = _piece(ONE_MARK, at=(40, 18))
        draft = draft_from_drag(piece, 34, 18, 37, 18, marks=marks)
        updated, err = apply_dialog_values(draft, 0, 18.5, 99, "J1")
        self.assertIsNone(err)
        self.assertAlmostEqual(updated.length, 20)
        self.assertAlmostEqual(updated.y, 18.5)
        self.assertAlmostEqual(updated.x, 0)
        self.assertAlmostEqual(updated.world_x, 30)

    def test_dialog_rejects_bad_name(self):
        piece = _piece(TWO_PIECES, 1)
        draft = draft_from_drag(piece, 0, 0, 20, 0)
        updated, err = apply_dialog_values(draft, 0, 0, 20, "  ")
        self.assertIsNone(updated)
        self.assertIn("Name", err)

    def test_automatic_names_j1_j2(self):
        self.assertEqual(next_joint_name([]), "J1")
        marks, _o, _w = parse_joint_file(ONE_MARK)
        # unpaired J1 is reused
        self.assertEqual(next_joint_name(marks), "J1")
        text = ONE_MARK.replace("END\n", "J 0 18.5 20 3 J1\nEND\n", 1)
        # only replace the last END (p2)
        text = """ADD 0 0 p1
R 0 0 20 20
J 0 0 20 3 J1
END
ADD 30 0 p2
R 0 0 20 40
J 0 18.5 20 3 J1
END
"""
        marks2, _o, _w = parse_joint_file(text)
        self.assertEqual(next_joint_name(marks2), "J2")

    def test_apply_joints_still_accepts_pair(self):
        text = """ADD 0 0 p1
R 0 0 20 20
J 0 0 20 3 J1
END
ADD 30 0 p2
R 0 0 20 40
J 0 18.5 20 3 J1
END
"""
        result = apply_joints(text)
        self.assertEqual(result.applied, 1)
        self.assertIn("JM 0 0 20 3 4 4 in", result.text)
        self.assertIn("JF 0 18.5 20 3 4 4", result.text)



class MarkDragTkTests(unittest.TestCase):
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

    def _make_tab(self, dsl=TWO_PIECES):
        import tkinter as tk
        from tkinter import ttk
        from engraver_ctrl.tab_designer import DesignerTab

        class Host:
            font = None
            ser = None

        win = tk.Toplevel(self.root)
        win.geometry("1100x800")
        nb = ttk.Notebook(win)
        nb.pack(fill="both", expand=True)
        tab = DesignerTab(nb, Host())
        nb.add(tab, text="Custom")
        win.deiconify()
        win.update()
        win.update_idletasks()
        tab.view_mode_var.set("raw")
        tab._on_view_mode()
        tab.text_input.delete("1.0", "end")
        tab.text_input.insert("1.0", dsl)
        tab.preview()
        win.update()
        win.update_idletasks()
        job = getattr(tab, "_resize_job", None)
        if job is not None:
            try:
                tab.after_cancel(job)
            except Exception:
                pass
            tab._resize_job = None
        tab._mark_dialog_wait = False
        tab.mark_mode_var.set(True)
        tab._toggle_mark_mode()
        return win, tab

    def _event(self, tab, wx, wy):
        px, py = tab.to_canvas(wx, wy)
        ex = px - tab.canvas.canvasx(0)
        ey = py - tab.canvas.canvasy(0)

        class E:
            def __init__(self, x, y):
                self.x, self.y, self.state = x, y, 0

        return E(ex, ey)

    def _drag(self, tab, x0, y0, x1, y1):
        a = self._event(tab, x0, y0)
        b = self._event(tab, x1, y1)
        tab._on_mark_press(a, tab.canvas.canvasx(a.x), tab.canvas.canvasy(a.y))
        # Pin exact world corners so a mid-drag canvas resize cannot
        # shift the snapped length away from the intended 1 mm grid.
        d = tab._mark_drag
        d["x0"], d["y0"], d["x1"], d["y1"] = x0, y0, x1, y1
        tab._draw_mark_preview(d)
        self.root.update()
        return a, b

    def test_drag_opens_dialog_and_commits(self):
        win, tab = self._make_tab()
        try:
            a, b = self._drag(tab, 0.2, 0.3, 19.6, 0.4)
            tags = [t for i in tab.canvas.find_all()
                    for t in tab.canvas.gettags(i)]
            self.assertIn("jmark_hover", tags)
            self.assertIn("jmark_tip", tags)
            self.assertIn("jmark_rubber", tags)
            tip = ""
            for item in tab.canvas.find_withtag("jmark_tip"):
                if tab.canvas.type(item) == "text":
                    tip = tab.canvas.itemcget(item, "text")
            self.assertIn("J1", tip)
            self.assertIn("edge", tip)
            self.assertIn("L=20", tip)
            tab._on_mark_release(b)
            self.root.update()
            self.root.update_idletasks()
            found = getattr(tab, "_mark_dialog", None)
            self.assertIsNotNone(found, "joint mark dialog did not open")
            self.assertTrue(found.winfo_exists())
            self.assertEqual(found.title(), "Joint mark")
            self.assertEqual(found.vars["name"].get(), "J1")
            found.ok_btn.invoke()
            self.root.update()
            text = tab._dsl_text()
            self.assertIn("J 0 0 20 3 J1", text)
        finally:
            win.destroy()


if __name__ == "__main__":
    unittest.main()
