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
    def test_example_edge_interior_roles_and_centerline(self):
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
        self.assertIn("JM 0 0 20 3 10 5 out", result.text)
        # Centerline of R 0 18.5 20 3 is y=20
        self.assertIn("JF 0 20 20 3 10 5", result.text)
        self.assertIn("# J 0 0 20 3 A", result.text)
        self.assertIn("# J 0 18.5 20 3 A", result.text)
        self.assertIn("# R 0 0 20 20", result.text)
        # Female outline kept; male bottom edge not re-emitted
        self.assertIn("R 0 0 20 40", result.text)
        self.assertNotIn("\nR 0 0 20 20\n", result.text)
        self.assertNotIn("L 0 0 20 0", result.text)
        teeth, first_d = choose_teeth(20)
        self.assertEqual(teeth, 10.0)
        self.assertEqual(first_d, 5.0)
        self.assertFalse(any(w.level == "error" for w in result.warnings))

    def test_both_edge_defaults_first_male_second_female(self):
        from engraver_ctrl.dsl_joint import apply_joints
        result = apply_joints(BOTH_EDGE)
        self.assertEqual(result.applied, 1)
        # First mark (p1 bottom) -> JM; second (p2 top) -> JF at y=18.5
        self.assertIn("JM 0 0 20 3 10 5 out", result.text)
        self.assertIn("JF 0 18.5 20 3 10 5", result.text)
        self.assertIn("# R 0 0 20 20", result.text)
        # Female R on p2 remains
        self.assertEqual(result.text.count("\nR 0 0 20 20\n"), 1)

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
        self.assertIn("JF 0 1.5 20 3 10 5", result.text)
        self.assertIn("JM 0 17 20 3 10 5 in", result.text)

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
        self.assertIn("JF 0 20 20 4 10 5", result.text)

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
        out = insert_j_line(text, 1, 0, 0, 20, 3, "A")
        self.assertIn("J 0 0 20 3 A", out)
        marks, _o, _w = parse_joint_file(out)
        self.assertEqual(next_joint_name(marks), "A")  # unpaired, reuse
        out2 = insert_j_line(out, 1, 0, 10, 20, 3, "A")
        marks2, _o, _w = parse_joint_file(out2)
        self.assertEqual(next_joint_name(marks2), "B")


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
            self.assertIn("JM 0 0 20 3 10 5 out", text)
            self.assertIn("JF 0 20 20 3 10 5", text)
            tab.preview()
            self.root.update_idletasks()
            # After apply, J marks are commented so no jmark overlays
            items = list(tab.canvas.find_all())
            flat = [t for i in items for t in tab.canvas.gettags(i)]
            self.assertFalse(any(t == "jmark" or t.startswith("jmark")
                                 for t in flat if t != "jmjf_hl"))
            # Highlights for the new JM/JF should be present
            self.assertTrue(any("jmjf_hl" in tab.canvas.gettags(i) for i in items))
        finally:
            win.destroy()


if __name__ == "__main__":
    unittest.main()
