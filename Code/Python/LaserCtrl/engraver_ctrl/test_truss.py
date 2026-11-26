"""Tests for the Truss designer core, its tab, and the Small parts
label/qty format it feeds.

Run from LaserCtrl root:
  python -m unittest engraver_ctrl.test_truss
"""

from __future__ import annotations

import math
import unittest

from engraver_ctrl.cut_plan_builder import (
    Part,
    build_cut_plan,
    expand_parts,
    format_parts_text,
    parse_parts_text,
    parse_qty_field,
    validate_holes,
)
from engraver_ctrl.truss_core import (
    TRUSS_TYPES,
    TrussParams,
    build_design,
    build_topology,
    candidate_grid,
    color_graph,
    find_chains,
    is_rigid,
    lap_centres,
    optimise,
    rigidity_rank,
    split_chain,
    to_small_parts,
    toggle_pin,
)


class SmallPartsLabelQtyFormatTests(unittest.TestCase):
    def test_old_lines_still_parse(self):
        parts = parse_parts_text("50, 1, 0, 10, 30\n70, 0, 1\n")
        self.assertEqual([p.label for p in parts], ["", ""])
        self.assertEqual([p.qty for p in parts], [1, 1])
        self.assertEqual(format_parts_text(parts), "50, 1, 0, 10, 30\n70, 0, 1")

    def test_label_and_qty(self):
        parts = parse_parts_text("D1-D4: 92, 1, 1, 6, 86, x4\nV1: 72, 1, 1, 6, 66 x2\n")
        self.assertEqual(parts[0].label, "D1-D4")
        self.assertEqual(parts[0].qty, 4)
        self.assertEqual(parts[0].hole_centers, [6.0, 86.0])
        self.assertEqual(parts[1].qty, 2)
        self.assertEqual(parts[1].hole_centers, [6.0, 66.0])
        text = format_parts_text(parts)
        self.assertIn("D1-D4: 92, 1, 1, 6, 86, x4", text)
        again = parse_parts_text(text)
        self.assertEqual([(p.label, p.qty, p.hole_centers) for p in again],
                         [(p.label, p.qty, p.hole_centers) for p in parts])

    def test_qty_without_holes_and_star(self):
        parts = parse_parts_text("40, 0, 0, x3\nA: 30, 1, 1, *2\n")
        self.assertEqual((parts[0].qty, parts[0].hole_centers), (3, []))
        self.assertEqual((parts[1].label, parts[1].qty), ("A", 2))

    def test_expand(self):
        parts = expand_parts([Part(50, True, False, [10], label="X", qty=3)])
        self.assertEqual(len(parts), 3)
        self.assertTrue(all(p.label == "X" and p.qty == 1 for p in parts))

    def test_hole_outside_piece_rejected(self):
        with self.assertRaises(ValueError):
            parse_parts_text("50, 0, 0, 55")
        with self.assertRaises(ValueError):
            parse_parts_text("50, 0, 0, 0")
        with self.assertRaises(ValueError):
            parse_parts_text("50, 0, 0, 10, x0")

    def test_validate_holes_edge_and_overlap(self):
        validate_holes([Part(50, False, False, [1.5, 48.5])], 1.5)
        with self.assertRaises(ValueError):
            validate_holes([Part(50, False, False, [1.0])], 1.5)
        with self.assertRaises(ValueError):
            validate_holes([Part(50, False, False, [10, 12])], 1.5)
        with self.assertRaisesRegex(ValueError, "Piece 1 \\(Q\\)"):
            validate_holes([Part(50, False, False, [49], label="Q")], 1.5)

    def test_build_cut_plan_expands_qty_and_keeps_labels(self):
        plan = build_cut_plan(
            114, [Part(50, True, True, [6, 44], label="P", qty=4)],
            width=10, gap=5, hole_radius=1.5, method="heuristic",
        )
        self.assertEqual(len(plan.parts), 4)
        self.assertEqual(len(plan.sticks), 2)
        labels = [pl.label for st in plan.sticks for pl in st.placements]
        self.assertEqual(labels, ["P"] * 4)
        self.assertEqual(len(plan.holes), 8)

    def test_build_cut_plan_rejects_bad_hole(self):
        with self.assertRaises(ValueError):
            build_cut_plan(114, [Part(50, False, False, [0.5])], width=10, gap=5,
                           hole_radius=1.5)

    def test_qty_field(self):
        self.assertEqual(parse_qty_field(""), 1)
        self.assertEqual(parse_qty_field("x5"), 5)
        self.assertEqual(parse_qty_field("3"), 3)
        with self.assertRaises(ValueError):
            parse_qty_field("0")
        with self.assertRaises(ValueError):
            parse_qty_field("abc")


class TrussGeometryTests(unittest.TestCase):
    def test_params_span_from_cap_radius(self):
        p = TrussParams()
        self.assertAlmostEqual(p.end_offset, 6.0)   # W/2 + 1
        self.assertAlmostEqual(p.usable, 104.0)     # L - W
        self.assertAlmostEqual(p.max_span, 92.0)    # L - W - (W + 2)
        q = TrussParams(stock_length=150, stick_width=12)
        self.assertAlmostEqual(q.max_span, 150 - 12 - 14)

    def test_all_types_rigid(self):
        for t in TRUSS_TYPES:
            for n, m in ((4, 1), (3, 2), (5, 2), (4, 2)):
                if t == "K" and m % 2:
                    continue
                nodes, bars = build_topology(t, n, m, 300, 60 * m)
                self.assertTrue(is_rigid(nodes, bars), (t, n, m))

    def test_warren_is_statically_determinate(self):
        nodes, bars = build_topology("Warren", 4, 1, 300, 60)
        self.assertEqual(len(bars), 2 * len(nodes) - 3)
        self.assertEqual(rigidity_rank(nodes, bars), 2 * len(nodes) - 3)

    def test_square_without_diagonal_is_not_rigid(self):
        nodes = [(0, 0), (100, 0), (100, 100), (0, 100)]
        bars = [(0, 1), (1, 2), (2, 3), (3, 0)]
        self.assertFalse(is_rigid(nodes, bars))
        self.assertTrue(is_rigid(nodes, bars + [(0, 2)]))

    def test_sparse_rank_fallback_matches(self):
        from engraver_ctrl import truss_core
        nodes, bars = build_topology("Pratt", 5, 2, 300, 120)
        rows = []
        for a, b in bars:
            (ax, ay), (bx, by) = nodes[a], nodes[b]
            ln = math.hypot(bx - ax, by - ay)
            ux, uy = (bx - ax) / ln, (by - ay) / ln
            rows.append({2 * a: -ux, 2 * a + 1: -uy, 2 * b: ux, 2 * b + 1: uy})
        self.assertEqual(truss_core._sparse_rank(rows), rigidity_rank(nodes, bars))

    def test_chains_join_collinear_bars(self):
        nodes, bars = build_topology("Pratt", 4, 1, 200, 50)
        chains = find_chains(nodes, bars)
        horizontal = [c for c in chains if nodes[c[0]][1] == nodes[c[-1]][1]]
        self.assertEqual(len(horizontal), 2)
        self.assertTrue(all(len(c) == 5 for c in horizontal))
        self.assertEqual(sum(len(c) - 1 for c in chains), len(bars))

    def test_split_chain_respects_span(self):
        p = TrussParams(lap_splice=False)
        pos = [0, 40, 80, 120, 160, 200]
        cuts = split_chain(pos, p)
        self.assertIsNotNone(cuts)
        for c in cuts:
            self.assertLessEqual(c.holes[-1] - c.holes[0], p.max_span + 1e-9)
        self.assertEqual(cuts[0].holes[0], 0)
        self.assertEqual(cuts[-1].holes[-1], 200)
        # Node splices: consecutive pieces share a node.
        for a, b in zip(cuts, cuts[1:]):
            self.assertEqual(a.holes[-1], b.holes[0])

    def test_split_chain_bar_too_long(self):
        self.assertIsNone(split_chain([0, 95], TrussParams(lap_splice=False)))

    def test_lap_splice_two_pins_overlap(self):
        p = TrussParams(max_layers=3)
        pos = [0, 50, 100]
        cuts = split_chain(pos, p, splice_layers=[2, 4, 2])
        self.assertEqual(len(cuts), 2)
        a, b = cuts
        self.assertIsNone(a.node_idx[-1])
        self.assertIsNone(b.node_idx[0])
        self.assertEqual(a.holes[-2:], b.holes[:2])
        self.assertAlmostEqual(a.holes[-1] - a.holes[-2], p.lap_gap)
        # Lap pins stay clear of both nodes of the panel.
        for h in b.holes[:2]:
            self.assertGreaterEqual(h - 50, 2 * p.end_offset - 1e-9)
            self.assertGreaterEqual(100 - h, 2 * p.end_offset - 1e-9)

    def test_node_splice_when_layers_allow(self):
        p = TrussParams(max_layers=4, lap_splice=False)
        cuts = split_chain([0, 50, 100], p, splice_layers=[2, 4, 2])
        self.assertEqual(len(cuts), 2)
        self.assertEqual(cuts[0].holes[-1], 50)
        self.assertEqual(cuts[1].holes[0], 50)

    def test_lap_centres_short_panel(self):
        self.assertEqual(lap_centres([0, 30], 0, TrussParams()), [])
        self.assertTrue(lap_centres([0, 75], 0, TrussParams()))

    def test_color_graph_minimal(self):
        tri = [{1, 2}, {0, 2}, {0, 1}]
        self.assertEqual(max(color_graph(tri)) + 1, 3)
        square = [{1, 3}, {0, 2}, {1, 3}, {0, 2}]
        self.assertEqual(max(color_graph(square)) + 1, 2)


class TrussDesignTests(unittest.TestCase):
    def _check_design(self, d):
        p = d.params
        e = p.end_offset
        for pc in d.all_pieces:
            self.assertLessEqual(pc.length, p.usable + 1e-9, pc.label)
            if pc.kind != "S":
                self.assertAlmostEqual(pc.length, pc.span + 2 * e)
                self.assertAlmostEqual(pc.node_offsets[0], e)
                self.assertAlmostEqual(pc.node_offsets[-1], pc.length - e)
        # Pieces sharing a joint sit on different layers.
        for v, idxs in d.node_pieces.items():
            layers = [d.pieces[i].layer for i in idxs]
            self.assertEqual(len(layers), len(set(layers)), v)
        self.assertEqual(d.layers, 1 + max(pc.layer for pc in d.pieces))

    def test_example_300x60(self):
        res = optimise(TrussParams(width=300, height=60))
        self.assertTrue(res)
        best = res[0]
        self._check_design(best)
        self.assertLessEqual(best.layers, 3)
        self.assertEqual(best.relaxed_layers, 0)
        self.assertLessEqual(best.sticks, 21)
        self.assertLessEqual(len(res), 3)
        scores = [d.score for d in res]
        self.assertEqual(scores, sorted(scores))

    def test_example_square_100(self):
        res = optimise(TrussParams(width=100, height=100))
        self.assertTrue(res)
        best = res[0]
        self._check_design(best)
        # 100 mm sides exceed the 92 mm one-stick span: lines are spliced.
        for pc in best.pieces:
            self.assertLessEqual(pc.span, 92 + 1e-9)
        self.assertGreaterEqual(best.rows, 2)

    def test_fixed_type_panels_rows(self):
        d = build_design(TrussParams(width=200, height=60), "Pratt", 4, 1,
                         enforce_layers=False)
        self.assertIsNotNone(d)
        self.assertEqual((d.truss_type, d.panels, d.rows), ("Pratt", 4, 1))
        self._check_design(d)
        grid = candidate_grid(TrussParams(width=200, height=60, truss_type="Howe",
                                          panels=4, rows=1))
        self.assertEqual(grid, [("Howe", 4, 1)])

    def test_load_levels_and_toggle(self):
        light = build_design(TrussParams(width=150, height=40, load="Light"),
                             "Pratt", 3, 1, enforce_layers=False)
        heavy = build_design(TrussParams(width=150, height=40, load="Heavy"),
                             "Pratt", 3, 1, enforce_layers=False)
        medium = build_design(TrussParams(width=150, height=40, load="Medium"),
                              "Pratt", 3, 1, enforce_layers=False)
        self.assertEqual(light.pin_count, 0)
        self.assertEqual(heavy.pin_count, len(heavy.nodes))
        corners = [v for v, (x, y) in enumerate(medium.nodes)
                   if x in (0, 150) and y in (0, 40)]
        self.assertTrue(all(medium.pins[v] for v in corners))
        before = medium.pins[corners[0]]
        toggle_pin(medium, corners[0], method="heuristic")
        self.assertNotEqual(medium.pins[corners[0]], before)

    def test_holes_only_at_pins_when_option_off(self):
        d = build_design(TrussParams(width=150, height=40, load="Light",
                                     holes_every_node=False),
                         "Pratt", 3, 1, enforce_layers=False)
        self.assertTrue(all(not pc.holes for pc in d.pieces))
        v = d.pieces[0].nodes[0]
        toggle_pin(d, v, method="heuristic")
        self.assertTrue(any(pc.holes for pc in d.pieces if v in pc.nodes))

    def test_to_small_parts_groups_and_roundtrips(self):
        d = optimise(TrussParams(width=300, height=60))[0]
        parts = to_small_parts(d)
        self.assertEqual(sum(p.qty for p in parts), len(d.all_pieces))
        for p in parts:
            self.assertTrue(p.label)
            self.assertTrue(p.is_cut_down and p.is_cut_up)
        again = parse_parts_text(format_parts_text(parts))
        self.assertEqual(sum(p.qty for p in again), len(d.all_pieces))
        plan = build_cut_plan(d.params.stock_length, again, width=d.params.stick_width,
                              gap=5, hole_radius=d.params.hole_radius,
                              method="heuristic")
        self.assertFalse(plan.unplaced)
        self.assertLessEqual(len(plan.sticks), d.sticks + 1)

    def test_impossible_frame_returns_empty(self):
        res = optimise(TrussParams(width=300, height=60, stock_length=40))
        self.assertEqual(res, [])


class TrussTabTests(unittest.TestCase):
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

    def test_optimise_toggle_and_send(self):
        from tkinter import ttk
        from engraver_ctrl.tab_small_parts import SmallPartsTab
        from engraver_ctrl.tab_truss import TrussTab

        shown = []

        class Host:
            font = None
            small_parts_tab = None

            def show_engraver_tab(self, title):
                shown.append(title)

        host = Host()
        nb = ttk.Notebook(self.root)
        nb.pack(fill="both", expand=True)
        small = SmallPartsTab(nb, host)
        host.small_parts_tab = small
        truss = TrussTab(nb, host)
        nb.add(small, text="Small parts")
        nb.add(truss, text="Truss")
        nb.select(truss)
        self.root.geometry("1200x800+0+0")
        self.root.deiconify()
        self.root.update()

        truss.on_optimise()
        self.assertTrue(truss.designs)
        self.assertEqual(len(truss.options.get_children()), len(truss.designs))
        self.assertIn("Sticks:", truss.stats_var.get())
        self.assertTrue(truss.canvas.find_withtag("node"))
        self.assertEqual(len(truss.table.get_children()), len(truss.design.all_pieces))

        # Click toggles a joint between glue and pin.
        self.root.update()
        v = 0
        x, y = truss._node_px[v]
        before = truss.design.pins[v]
        self.assertEqual(truss.node_at(x + 2, y + 1), v)
        truss.toggle_node(v)
        self.assertNotEqual(truss.design.pins[v], before)

        truss.on_send()
        self.assertEqual(shown, ["Small parts"])
        parts = parse_parts_text(small.text_parts.get("1.0", "end"))
        self.assertEqual(sum(p.qty for p in parts), len(truss.design.all_pieces))
        self.assertTrue(all(p.label for p in parts))
        self.assertIsNotNone(small._plan)
        self.assertEqual(small.entry_hole_radius.get(), "1.5")

        # Cards mode shows label + qty on one row.
        small.mode_var.set("cards")
        small.on_mode_change()
        card = small._cards[0]
        self.assertEqual(card.label_var.get(), parts[0].label)
        texts = []
        for w in card.row.winfo_children():
            try:
                texts.append(str(w.cget("text")))
            except Exception:
                pass
        for t in ("Lb", "Len", "Bot", "Top", "Holes", "Qty", "Dup", "✕"):
            self.assertIn(t, texts)
        self.root.update()
        self.assertTrue(all(w.winfo_ismapped() for w in card.row.winfo_children()),
                        "every card field fits on its single row")
        win = truss.show_help()
        self.assertEqual(win.title(), "Truss Help")
        win.event_generate("<Escape>")
        self.root.update()
        nb.destroy()
        self.root.withdraw()

    def test_bad_input_reports_error(self):
        from unittest import mock
        from engraver_ctrl.tab_truss import TrussTab

        class Host:
            font = None

        tab = TrussTab(self.root, Host())
        tab.e_width.delete(0, "end")
        tab.e_width.insert(0, "abc")
        with mock.patch("engraver_ctrl.tab_truss.messagebox.showerror") as err:
            tab.on_optimise()
            err.assert_called_once()
        tab.destroy()


if __name__ == "__main__":
    unittest.main()
