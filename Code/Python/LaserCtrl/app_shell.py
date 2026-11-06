"""
Unified LaserCtrl application shell.

Hosts Engraver / Frame Toolkit / DSL Library / DSL Nesting under one Tk root.
Tab builders are lazy-imported so a missing optional dependency (e.g. ortools)
only disables that section.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox

from common.ui import enable_dpi_awareness, init_fonts


class EngraverHost:
    """Minimal shared state for engraver tabs (serial port + font)."""

    def __init__(self, root, font):
        self.root = root
        self.font = font
        self.ser = None


class LaserAppShell:
    def __init__(self, root):
        self.root = root
        self.root.title("LaserCtrl")
        self.root.geometry("1280x820")
        self.root.minsize(980, 640)

        self.font_specs = init_fonts(root, size=10)
        self.font = self.font_specs[0]

        self.engraver_host = EngraverHost(root, self.font)
        self.machine_tab = None
        self.nesting_panel = None
        self._busy_providers = []

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self._build()

    def _build(self):
        self.main_nb = ttk.Notebook(self.root)
        self.main_nb.pack(fill="both", expand=True)

        self._add_lazy_tab(self.main_nb, "Engraver", self._build_engraver)
        self._add_lazy_tab(self.main_nb, "Frame Toolkit", self._build_frame)
        self._add_lazy_tab(self.main_nb, "DSL Library", self._build_library)
        self._add_lazy_tab(self.main_nb, "DSL Nesting", self._build_nesting)

    def _add_lazy_tab(self, notebook, title, build_fn):
        frame = ttk.Frame(notebook)
        notebook.add(frame, text=title)
        try:
            build_fn(frame)
        except Exception as e:
            ttk.Label(
                frame,
                text=f"Failed to load this section:\n{e}",
                foreground="red",
                wraplength=640,
                justify="left",
            ).pack(padx=20, pady=20, anchor="nw")

    def _add_subtab(self, notebook, title, build_fn):
        frame = ttk.Frame(notebook)
        notebook.add(frame, text=title)
        try:
            return build_fn(frame)
        except Exception as e:
            ttk.Label(
                frame,
                text=f"Failed to load this tool:\n{e}",
                foreground="red",
                wraplength=500,
                justify="left",
            ).pack(padx=20, pady=20, anchor="nw")
            return None

    # ---- section builders ----

    def _build_engraver(self, parent):
        nb = ttk.Notebook(parent)
        nb.pack(fill="both", expand=True)
        host = self.engraver_host

        def add_engraver_tab(title, factory):
            try:
                widget = factory(nb, host)
                nb.add(widget, text=title)
                return widget
            except Exception as e:
                frame = ttk.Frame(nb)
                nb.add(frame, text=title)
                ttk.Label(
                    frame,
                    text=f"Failed to load this tool:\n{e}",
                    foreground="red",
                    wraplength=500,
                    justify="left",
                ).pack(padx=20, pady=20, anchor="nw")
                return None

        def make_machine(nb_, host_):
            from engraver_ctrl.tab_machine import MachineTab
            return MachineTab(nb_, host_)

        def make_small(nb_, host_):
            from engraver_ctrl.tab_small_parts import SmallPartsTab
            return SmallPartsTab(nb_, host_)

        def make_parallel(nb_, host_):
            from engraver_ctrl.tab_parallel import ParallelTab
            return ParallelTab(nb_, host_)

        def make_custom(nb_, host_):
            from engraver_ctrl.tab_designer import DesignerTab
            return DesignerTab(nb_, host_)

        def make_sim(nb_, host_):
            from engraver_ctrl.tab_simulate import TabSimulate
            return TabSimulate(nb_, host_)

        self.machine_tab = add_engraver_tab("Machine", make_machine)
        add_engraver_tab("Small parts", make_small)
        add_engraver_tab("Parallel", make_parallel)
        add_engraver_tab("Custom", make_custom)
        add_engraver_tab("Simulate", make_sim)

    def _build_frame(self, parent):
        nb = ttk.Notebook(parent)
        nb.pack(fill="both", expand=True)

        def joint(frame):
            import frame_creator.joint_nesting_gui as m
            return m.JointNestingApp(frame)

        def beam(frame):
            import frame_creator.beam_dsl_gui as m
            return m.BeamDslApp(frame)

        def skeleton(frame):
            import frame_creator.rail_skeleton_gui as m
            return m.SkeletonApp(frame)

        def railcut(frame):
            import frame_creator.rail_cutlist_gui as m
            return m.RailDslApp(frame)

        def box(frame):
            import frame_creator.box_gui as m
            return m.BoxApp(frame)

        self._add_subtab(nb, "Joint", joint)
        self._add_subtab(nb, "Beam", beam)
        self._add_subtab(nb, "Skeleton", skeleton)
        self._add_subtab(nb, "Rail cut-list", railcut)
        self._add_subtab(nb, "Box", box)

    def _build_library(self, parent):
        from dsl_library_tool.gui import build_dsl_library_panel
        build_dsl_library_panel(parent)

    def _build_nesting(self, parent):
        from dsl_nesting.gui import build_dsl_nesting_panel
        self.nesting_panel = build_dsl_nesting_panel(parent)

    # ---- lifecycle ----

    def _any_busy(self):
        if self.nesting_panel is not None and getattr(self.nesting_panel, "is_busy", lambda: False)():
            return True
        # Frame solvers expose no shared flag; nesting is the long CP-SAT UX we guard.
        return False

    def on_close(self):
        if self._any_busy():
            if not messagebox.askyesno(
                "Busy",
                "A background solve is still running. Close anyway?",
            ):
                return
        self.shutdown()
        self.root.destroy()

    def shutdown(self):
        """Conservative cleanup: stop workers / close serial. No speculative GCODE."""
        machine = self.machine_tab
        if machine is None:
            ser = getattr(self.engraver_host, "ser", None)
            if ser is not None:
                try:
                    ser.close()
                except Exception:
                    pass
                self.engraver_host.ser = None
            return

        # Prefer the tab's own shutdown helper when present.
        fn = getattr(machine, "shutdown_connection", None)
        if callable(fn):
            try:
                fn()
                return
            except Exception:
                pass

        stop_event = getattr(machine, "stop_event", None)
        if stop_event is not None:
            stop_event.set()
        ser = getattr(self.engraver_host, "ser", None)
        if ser is not None:
            try:
                ser.close()
            except Exception:
                pass
            self.engraver_host.ser = None


def create_app():
    """Create the single Tk root and shell. Caller runs mainloop()."""
    enable_dpi_awareness()
    root = tk.Tk()
    shell = LaserAppShell(root)
    return root, shell


def main():
    root, _shell = create_app()
    root.mainloop()


if __name__ == "__main__":
    main()
