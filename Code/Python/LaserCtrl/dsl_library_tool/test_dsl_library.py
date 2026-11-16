#!/usr/bin/env python3
"""DSL Library parser, JM/JF preview highlights, and local samples."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

_HERE = Path(__file__).resolve().parent
_ROOT = _HERE.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

SAMPLE_PATH = _HERE / "data" / "JM JF Joints.txt"


def _sample_dsl():
    from dsl_library_tool.dsl_library import parse_sections
    return parse_sections(SAMPLE_PATH.read_text(encoding="utf-8"))["dsl"]


class LibraryParserTests(unittest.TestCase):
    def test_jf_segments_match_engraver(self):
        from dsl_library_tool.dsl_parser import parse_dsl
        from engraver_ctrl.dsl_parse import parse_text

        dsl = "JF 10 0 3 100 10 0\n"
        result = parse_dsl(dsl)
        self.assertEqual(result.errors, [])
        self.assertTrue(result.segments)
        self.assertEqual([cmd for cmd, _ in result.shapes], ["JF"])
        engraver = parse_text(dsl)["shapes"][0][1]
        self.assertEqual(
            [tuple(round(v, 6) for v in seg) for seg in result.segments],
            [tuple(round(v, 6) for v in seg) for seg in engraver],
        )

    def test_jm_out_and_in_parse(self):
        from dsl_library_tool.dsl_parser import parse_dsl

        out = parse_dsl("JM 17 0 3 100 10 0 out\n")
        inn = parse_dsl("JM 17 0 3 100 10 0 in\n")
        self.assertEqual(out.errors, [])
        self.assertEqual(inn.errors, [])
        self.assertEqual(out.shapes[0][0], "JM")
        self.assertNotEqual(
            [tuple(round(v, 6) for v in s) for s in out.segments],
            [tuple(round(v, 6) for v in s) for s in inn.segments],
        )

    def test_j_mark_is_not_cut(self):
        from dsl_library_tool.dsl_parser import parse_dsl

        result = parse_dsl("J 0 0 3 40 edgeA F\nR 0 0 20 40\n")
        self.assertEqual(result.errors, [])
        self.assertEqual(len(result.marks), 1)
        self.assertEqual(result.marks[0].name, "edgeA")
        self.assertEqual(result.marks[0].role, "F")
        self.assertEqual(len(result.marks[0].polygon), 4)
        cmds = [cmd for cmd, _ in result.shapes]
        self.assertEqual(cmds, ["R"])
        # Four rectangle edges only; the J rectangle is not a cut path.
        self.assertEqual(len(result.segments), 4)

    def test_malformed_joint_commands_are_errors(self):
        from dsl_library_tool.dsl_parser import parse_dsl

        cases = [
            "JF 10 0 3 100\n",
            "JM 17 0 3 100 10 0 sideways\n",
            "J 0 0 3 40\n",
            "JM 17 0 3 100 10 0\n",
        ]
        for dsl in cases:
            with self.subTest(dsl=dsl.strip()):
                result = parse_dsl(dsl)
                self.assertTrue(result.errors, dsl)
                self.assertEqual(result.segments, [])

    def test_legacy_commands_still_parse(self):
        from dsl_library_tool.dsl_parser import parse_dsl

        result = parse_dsl("ADD 10 0 box\nR 0 0 20 20\nEND\n")
        self.assertEqual(result.errors, [])
        self.assertEqual(len(result.segments), 4)
        self.assertEqual(result.labels[0][2], "box")

    def test_sample_library_entry_parses(self):
        from dsl_library_tool.dsl_parser import parse_dsl

        result = parse_dsl(_sample_dsl())
        self.assertEqual(result.errors, [])
        cmds = [cmd for cmd, _ in result.shapes]
        self.assertIn("JF", cmds)
        self.assertIn("JM", cmds)
        self.assertIn("R", cmds)
        self.assertEqual(len(result.marks), 1)
        self.assertEqual(result.marks[0].name, "edgeA")


class LibraryListingTests(unittest.TestCase):
    def test_local_txt_appears_when_missing_from_index(self):
        from dsl_library_tool.dsl_library import DSLLibrary, build_content

        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            (folder / "jm-jf-joints.txt").write_text(
                build_content("JM JF Joints", "local only", "JF 10 0 3 100 10 0\n"),
                encoding="utf-8",
            )
            lib = DSLLibrary(folder, base_url="http://127.0.0.1:9/")
            lib._loaded = True
            lib.online = False
            lib.index = {
                "schema": "dsl_library.index",
                "version": 1,
                "updated_at": "",
                "drawings": {},
            }
            entries = lib.list_entries()
            names = [name for _path, name, _desc in entries]
            self.assertIn("JM JF Joints", names)


class LibraryCanvasTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import tkinter as tk

        cls.root = tk.Tk()
        cls.root.withdraw()

    @classmethod
    def tearDownClass(cls):
        cls.root.destroy()

    def test_preview_draws_highlights_under_paths(self):
        import tkinter as tk
        from common.ui import JF_HIGHLIGHT, JM_HIGHLIGHT
        from dsl_library_tool.dsl_canvas import DSLCanvas
        from dsl_library_tool.dsl_parser import parse_dsl

        win = tk.Toplevel(self.root)
        win.withdraw()
        try:
            canvas = DSLCanvas(win)
            canvas.config(width=640, height=420)
            canvas.pack(fill="both", expand=True)
            self.root.update()
            canvas.render(parse_dsl(_sample_dsl()))
            self.root.update_idletasks()
            items = list(canvas.find_all())
            hl = [i for i in items if "jmjf_hl" in canvas.gettags(i)]
            paths = [i for i in items if "dsl_path" in canvas.gettags(i)]
            marks = [i for i in items if "jmark" in canvas.gettags(i)]
            self.assertTrue(hl, "expected JM/JF highlight polygons")
            self.assertTrue(paths, "expected cut path lines")
            self.assertTrue(marks, "expected J mark overlay")
            self.assertLess(
                max(items.index(i) for i in hl),
                min(items.index(i) for i in paths),
            )
            fills = {canvas.itemcget(i, "fill") for i in hl}
            self.assertEqual(fills, {JM_HIGHLIGHT, JF_HIGHLIGHT})
            texts = {
                canvas.itemcget(i, "text"): canvas.coords(i)
                for i in items if canvas.type(i) == "text"
            }
            for name in ("mortise", "tenon", "marked", "edgeA F"):
                self.assertIn(name, texts, f"missing label {name}")
            # ADD labels must use the same world-to-canvas map as the axes
            # (a prior bug reused cx/cy and shifted these labels).
            ox = texts["Oy"][0]
            self.assertAlmostEqual(texts["mortise"][0], ox + 7, delta=12)
            self.assertGreater(texts["tenon"][0], texts["mortise"][0])
            self.assertAlmostEqual(texts["marked"][0], texts["mortise"][0], delta=2)
        finally:
            win.destroy()

    def test_panel_preview_accepts_jm_jf(self):
        import tkinter as tk
        from dsl_library_tool.gui import DSLLibraryPanel

        win = tk.Toplevel(self.root)
        win.withdraw()
        with tempfile.TemporaryDirectory() as tmp, patch.object(
            DSLLibraryPanel, "after_idle", lambda self, fn: None
        ):
            panel = DSLLibraryPanel(win, library_path=tmp)
            panel.pack(fill="both", expand=True)
            panel.dsl_text.delete("1.0", "end")
            panel.dsl_text.insert("1.0", _sample_dsl())
            panel.canvas.config(width=400, height=280)
            self.root.update()
            panel.preview()
            self.root.update_idletasks()
            self.assertFalse(panel.canvas.result.errors)
            hl = [
                i for i in panel.canvas.find_all()
                if "jmjf_hl" in panel.canvas.gettags(i)
            ]
            self.assertTrue(hl)
            self.assertIn("OK", panel.status_var.get())
            win.destroy()


if __name__ == "__main__":
    unittest.main()
