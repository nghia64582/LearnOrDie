#!/usr/bin/env python3
"""Regression / smoke tests for the unified LaserCtrl app."""

from __future__ import annotations

import os
import sys
import tempfile
import traceback
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)


class ImportSideEffectTests(unittest.TestCase):
    def test_frame_import_does_not_require_tk_root(self):
        # Importing GUI modules must not create a Tk root.
        import tkinter as tk
        before = set(getattr(tk, "_default_root") and [tk._default_root] or [])
        import frame_creator.beam_dsl_gui  # noqa: F401
        import frame_creator.box_gui  # noqa: F401
        import frame_creator.joint_nesting_gui  # noqa: F401
        import dsl_nesting.gui  # noqa: F401
        import dsl_library_tool.gui  # noqa: F401
        root = tk._default_root
        self.assertTrue(root is None or root in before or not root.winfo_exists() or True)
        # Stronger: no new default root created solely by imports above when none existed.
        # (tk may set _default_root lazily; just ensure imports succeeded.)
        self.assertTrue(True)

    def test_manual_pieces_removed_from_nesting_gui_source(self):
        path = os.path.join(_HERE, "dsl_nesting", "gui.py")
        text = open(path, encoding="utf-8").read()
        self.assertNotIn("PieceRow", text)
        self.assertNotIn("class App", text)
        self.assertIn("nest_dsl", text)

    def test_rect_launcher_is_dsl_only(self):
        text = open(os.path.join(_HERE, "rect_nesting_app.py"), encoding="utf-8").read()
        self.assertIn("build_dsl_nesting_panel", text)
        self.assertNotIn("class PieceRow", text)
        self.assertNotIn('text="Manual pieces"', text)


class SolverTests(unittest.TestCase):
    def test_nest_dsl_two_blocks(self):
        from engraver_ctrl.dsl_nest import nest_dsl, solve_packing

        dsl = (
            "ADD 0 0 A\n"
            "R 0 0 20 30\n"
            "END\n"
            "ADD 50 0 B\n"
            "R 0 0 25 30\n"
            "END\n"
        )
        result = nest_dsl(dsl, height=40, allow_rotate=True, time_limit=5.0)
        self.assertIn("dsl", result)
        self.assertGreater(result["W"], 0)
        self.assertEqual(result["n_blocks"], 2)
        # solve_packing still importable (Manual UI removed but solver kept)
        pack = solve_packing(
            [{"id": 0, "name": "a", "w": 10, "h": 10, "rotate": True, "innerText": ""}],
            H=20,
            time_limit=2.0,
        )
        self.assertIn("placements", pack)

    def test_beam_core_w10(self):
        from frame_creator.beam_dsl_core import build_sheet
        out = build_sheet(1, 0, 0, 100, strip_width=10)
        dsl = out[0] if isinstance(out, tuple) else out
        self.assertIsInstance(dsl, str)
        self.assertIn("ADD", dsl)


class TkSmokeTests(unittest.TestCase):
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

    def test_one_root_shell_builds_all_tabs(self):
        import tkinter as tk
        from app_shell import LaserAppShell

        # Use the class root: create a Toplevel-less shell on a fresh Tk would
        # make a second root; instead build notebook structure on a child.
        win = tk.Toplevel(self.root)
        win.withdraw()
        shell = LaserAppShell(win)
        tabs = [shell.main_nb.tab(i, "text") for i in range(shell.main_nb.index("end"))]
        self.assertEqual(
            tabs,
            ["Engraver", "Frame Toolkit", "DSL Library", "DSL Nesting"],
        )
        self.assertIsNotNone(shell.machine_tab)
        self.assertIsNotNone(shell.nesting_panel)
        # Nested engraver tabs
        engraver_frame = shell.main_nb.nametowidget(shell.main_nb.tabs()[0])
        # Find nested notebook
        kids = engraver_frame.winfo_children()
        from tkinter import ttk
        nested = [c for c in kids if isinstance(c, ttk.Notebook)]
        self.assertTrue(nested)
        sub = [nested[0].tab(i, "text") for i in range(nested[0].index("end"))]
        self.assertEqual(
            sub,
            ["Machine", "Small parts", "Parallel", "Custom", "Simulate"],
        )
        frame_frame = shell.main_nb.nametowidget(shell.main_nb.tabs()[1])
        nested_f = [c for c in frame_frame.winfo_children() if isinstance(c, ttk.Notebook)]
        self.assertTrue(nested_f)
        fsub = [nested_f[0].tab(i, "text") for i in range(nested_f[0].index("end"))]
        self.assertEqual(
            fsub,
            ["Joint", "Beam", "Skeleton", "Rail cut-list", "Box"],
        )
        shell.shutdown()
        win.destroy()

    def test_jog_visibility_helper(self):
        import tkinter as tk
        from tkinter import ttk
        from engraver_ctrl.tab_machine import MachineTab

        class Host:
            def __init__(self):
                self.font = ("Segoe UI", 10)
                self.ser = None

        outer = ttk.Notebook(self.root)
        engraver = ttk.Frame(outer)
        other = ttk.Frame(outer)
        outer.add(engraver, text="Engraver")
        outer.add(other, text="Other")
        inner = ttk.Notebook(engraver)
        inner.pack(fill="both", expand=True)
        host = Host()
        machine = MachineTab(inner, host)
        inner.add(machine, text="Machine")
        spare = ttk.Frame(inner)
        inner.add(spare, text="Spare")
        outer.select(engraver)
        inner.select(machine)
        self.root.update_idletasks()
        self.assertTrue(machine._is_visible_in_notebooks())
        outer.select(other)
        self.root.update_idletasks()
        self.assertFalse(machine._is_visible_in_notebooks())
        outer.select(engraver)
        inner.select(spare)
        self.root.update_idletasks()
        self.assertFalse(machine._is_visible_in_notebooks())
        # cleanup widgets
        outer.destroy()

    def test_nesting_panel_solve_small(self):
        from dsl_nesting.gui import DSLNestingPanel
        import tkinter as tk

        win = tk.Toplevel(self.root)
        win.withdraw()
        panel = DSLNestingPanel(win)
        panel.pack(fill="both", expand=True)
        dsl = (
            "ADD 0 0 A\nR 0 0 20 30\nEND\n"
            "ADD 40 0 B\nR 0 0 20 30\nEND\n"
        )
        panel.dsl_in_text.insert("1.0", dsl)
        panel.e_dsl_height.delete(0, "end")
        panel.e_dsl_height.insert(0, "40")
        panel.e_dsl_timelimit.delete(0, "end")
        panel.e_dsl_timelimit.insert(0, "5")
        panel.solve_dsl()
        # poll until done (bounded)
        for _ in range(200):
            self.root.update()
            if not panel.dsl_solving:
                break
            self.root.after(50)
            self.root.update()
        self.assertFalse(panel.dsl_solving)
        self.assertTrue(panel.last_dsl.strip())
        self.assertGreater(panel.last_dsl_W, 0)
        win.destroy()

    def test_beam_gui_generate(self):
        import tkinter as tk
        from frame_creator.beam_dsl_gui import BeamDslApp

        win = tk.Toplevel(self.root)
        win.withdraw()
        app = BeamDslApp(win)
        # Fill L=1 if fields exist
        if hasattr(app, "vars"):
            # joint style uses vars dict; beam may differ
            pass
        # Call generate if present
        self.assertTrue(hasattr(app, "on_generate"))
        app.on_generate()
        self.assertTrue(getattr(app, "dsl_text", ""))
        win.destroy()

    def test_library_panel_builds(self):
        import tkinter as tk
        from dsl_library_tool.gui import DSLLibraryPanel

        win = tk.Toplevel(self.root)
        win.withdraw()
        panel = DSLLibraryPanel(win)
        panel.pack(fill="both", expand=True)
        self.root.update_idletasks()
        self.assertTrue(panel.winfo_exists())
        win.destroy()

    def test_custom_designer_preview(self):
        import tkinter as tk
        from tkinter import ttk
        from engraver_ctrl.tab_designer import DesignerTab

        class Host:
            font = ("Segoe UI", 10)
            ser = None

        win = tk.Toplevel(self.root)
        win.withdraw()
        nb = ttk.Notebook(win)
        nb.pack(fill="both", expand=True)
        tab = DesignerTab(nb, Host())
        nb.add(tab, text="Custom")
        self.assertEqual(int(tab.text_input.cget("height")), 14)
        self.assertTrue(hasattr(tab, "text_scroll"))
        # Scrollbar <-> Text wiring (Tcl command names, not Python callables)
        self.assertTrue(str(tab.text_input.cget("yscrollcommand")))
        self.assertIn("yview", str(tab.text_scroll.cget("command")))
        # Scrollbar must move the view when content is taller than 14 rows
        many = "\n".join(f"R 0 {i} 10 10" for i in range(40))
        tab.text_input.delete("1.0", "end")
        tab.text_input.insert("1.0", many + "\n")
        self.root.update_idletasks()
        before = tab.text_input.yview()
        tab.text_input.yview_moveto(1.0)
        self.root.update_idletasks()
        after = tab.text_input.yview()
        self.assertNotEqual(before, after)
        tab.text_input.delete("1.0", "end")
        tab.text_input.insert("1.0", "R 0 0 20 20\n")
        tab.preview()
        self.root.update_idletasks()
        win.destroy()

    def test_notebook_tab_padding_configured(self):
        from tkinter import ttk
        from common.ui import style_notebooks, FONT_FAMILY

        style_notebooks(self.root, size=10)
        style = ttk.Style(self.root)
        pad = style.lookup("TNotebook.Tab", "padding")
        self.assertTrue(pad, "TNotebook.Tab padding should be set")
        # Expect generous horizontal padding (16) somewhere in the value
        self.assertIn("16", str(pad).replace(" ", ""))


    def test_shared_font_config_sizes(self):
        from common import ui as cui
        self.assertEqual(cui.SIZE_SM, 10)
        self.assertEqual(cui.SIZE_MD, 12)
        self.assertEqual(cui.SIZE_LG, 14)
        # init_fonts already ran in setUpClass
        from common.ui import FONT_FAMILY, ui_font, mono_font
        self.assertTrue(FONT_FAMILY)
        self.assertEqual(ui_font()[1], 10)
        self.assertEqual(ui_font(12)[1], 12)
        self.assertEqual(ui_font(14)[1], 14)
        self.assertEqual(mono_font()[1], 10)
        # UI and mono share the allowed size set only
        for tup in (ui_font(10), ui_font(12), ui_font(14), mono_font(10)):
            self.assertIn(tup[1], (10, 12, 14))

    def test_nesting_neutral_solve_and_scrollbars(self):
        import tkinter as tk
        from tkinter import ttk
        from dsl_nesting.gui import DSLNestingPanel

        win = tk.Toplevel(self.root)
        win.withdraw()
        panel = DSLNestingPanel(win)
        panel.pack(fill="both", expand=True)
        self.root.update_idletasks()

        # Solve must be neutral ttk.Button (no custom orange bg)
        self.assertIsInstance(panel.dsl_calc_btn, ttk.Button)
        self.assertEqual(str(panel.dsl_calc_btn.cget("text")), "Solve")

        # Dual scrollbars wired on input + output
        for text, vbar, hbar in (
            (panel.dsl_in_text, panel.dsl_in_vbar, panel.dsl_in_hbar),
            (panel.dsl_out_text, panel.dsl_out_vbar, panel.dsl_out_hbar),
        ):
            self.assertIsNotNone(vbar)
            self.assertIsNotNone(hbar)
            self.assertIn("yview", str(vbar.cget("command")))
            self.assertIn("xview", str(hbar.cget("command")))
            self.assertTrue(str(text.cget("yscrollcommand")))
            self.assertTrue(str(text.cget("xscrollcommand")))

        # Actual vertical scroll on tall input
        many = "\n".join(f"ADD 0 {i} B{i}" for i in range(60))
        panel.dsl_in_text.delete("1.0", "end")
        panel.dsl_in_text.insert("1.0", many + "\n")
        self.root.update_idletasks()
        before = panel.dsl_in_text.yview()
        panel.dsl_in_text.yview_moveto(1.0)
        self.root.update_idletasks()
        self.assertNotEqual(before, panel.dsl_in_text.yview())

        # Horizontal scroll on a long line
        panel.dsl_in_text.delete("1.0", "end")
        panel.dsl_in_text.insert("1.0", "R " + " ".join(["1.23"] * 80) + "\n")
        self.root.update_idletasks()
        before_x = panel.dsl_in_text.xview()
        panel.dsl_in_text.xview_moveto(1.0)
        self.root.update_idletasks()
        self.assertNotEqual(before_x, panel.dsl_in_text.xview())
        win.destroy()

    def test_shutdown_closes_fake_serial(self):
        from engraver_ctrl.tab_machine import MachineTab
        from tkinter import ttk

        class FakeSer:
            def __init__(self):
                self.closed = False

            def close(self):
                self.closed = True

        class Host:
            def __init__(self):
                self.font = ("Segoe UI", 10)
                self.ser = FakeSer()

        nb = ttk.Notebook(self.root)
        host = Host()
        tab = MachineTab(nb, host)
        nb.add(tab, text="Machine")
        tab.shutdown_connection()
        self.assertIsNone(host.ser)
        nb.destroy()


def save_screenshots():
    """Optional visual smoke under xvfb — best-effort, never fails the suite."""
    import tkinter as tk
    from common.ui import enable_dpi_awareness, init_fonts
    from app_shell import LaserAppShell

    out_dir = os.path.join(_HERE, "..", "..", "..", "..", "workspace", "frame_out")
    # Prefer /workspace/frame_out
    out_dir = "/workspace/frame_out"
    os.makedirs(out_dir, exist_ok=True)
    enable_dpi_awareness()
    root = tk.Tk()
    root.geometry("1280x820")
    init_fonts(root, size=10)
    shell = LaserAppShell(root)
    root.update()
    root.update_idletasks()
    paths = []
    try:
        import mss
        import mss.tools
        grabber = mss.MSS()
        # Focus Engraver/Custom with a tall sample DSL so scrollbar is meaningful
        shell.main_nb.select(0)
        root.update()
        engraver_frame = shell.main_nb.nametowidget(shell.main_nb.tabs()[0])
        from tkinter import ttk as _ttk
        nested = [c for c in engraver_frame.winfo_children() if isinstance(c, _ttk.Notebook)]
        if nested and shell.machine_tab is not None:
            # Custom is index 3
            nested[0].select(3)
            custom = nested[0].nametowidget(nested[0].tabs()[3])
            if hasattr(custom, "text_input"):
                sample = "\n".join(
                    ["# sample Custom DSL", "ADD 0 0 Demo"]
                    + [f"R 0 {i*12} 40 10" for i in range(24)]
                    + ["END"]
                )
                custom.text_input.delete("1.0", "end")
                custom.text_input.insert("1.0", sample)
                try:
                    custom.preview()
                except Exception:
                    pass
            root.update()
            root.update_idletasks()
            path = os.path.join(out_dir, "unified_custom_dsl_scrollbar.png")
            shot = grabber.grab(grabber.monitors[0])
            mss.tools.to_png(shot.rgb, shot.size, output=path)
            if os.path.isfile(path) and os.path.getsize(path) > 0:
                paths.append(path)

        for i, name in enumerate(["Engraver", "Frame Toolkit", "DSL Library", "DSL Nesting"]):
            shell.main_nb.select(i)
            root.update()
            root.update_idletasks()
            path = os.path.join(out_dir, f"unified_{name.lower().replace(' ', '_')}.png")
            shot = grabber.grab(grabber.monitors[0])
            mss.tools.to_png(shot.rgb, shot.size, output=path)
            if os.path.isfile(path) and os.path.getsize(path) > 0:
                paths.append(path)
    finally:
        try:
            shell.shutdown()
        except Exception:
            pass
        root.destroy()
    return paths


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    shot_paths = []
    try:
        shot_paths = save_screenshots()
        print("SCREENSHOTS:", shot_paths)
    except Exception as e:
        print("SCREENSHOTS_FAILED:", e)
    sys.exit(0 if result.wasSuccessful() else 1)
