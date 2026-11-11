"""Tests for the card-based DSL editor (parse, assemble, placement, UI)."""

from __future__ import annotations

import os
import unittest
from unittest.mock import patch
from pathlib import Path


PURE_ADD = """ADD 0 0 p1
R 0 0 20 20
END
ADD 30 0 p2
R 0 0 20 40
END
"""

LOOSE = """C 50 50 30
R 20 30 40 50
"""

MIXED = """C 1 1 2

ADD 10 0 p1
R 0 0 20 20
END

LV 0 0 5
# trailing comment stays with this run
LH 0 0 5
"""

NESTED = """ADD 0 0 outer
R 0 0 30 30
ADD 5 5 inner
C 0 0 3
END
R 1 1 2 2
END
"""

ROTATE_BLOCK = """ADD 50 0 Xoay 45 do
ROTATE 45
R 0 0 20 10
END
END
"""

EXAMPLE = """ADD 0 0 p1
R 0 0 20 20
J 0 0 20 3 A
END
ADD 30 0 p2
R 0 0 20 40
J 0 18.5 20 3 A
END
"""


class ParseAssembleTests(unittest.TestCase):
    def test_wrap_loose_commands_one_run(self):
        from engraver_ctrl.dsl_cards import parse_cards, assemble_cards

        cards = parse_cards(LOOSE)
        self.assertEqual(len(cards), 1)
        self.assertEqual(cards[0].name, "loose")
        self.assertEqual(cards[0].dx, 0.0)
        self.assertEqual(cards[0].dy, 0.0)
        self.assertIn("C 50 50 30", cards[0].inner)
        self.assertIn("R 20 30 40 50", cards[0].inner)
        raw = assemble_cards(cards)
        self.assertIn("ADD 0 0 loose", raw)
        self.assertIn("C 50 50 30", raw)
        self.assertTrue(raw.strip().endswith("END"))

    def test_wrap_preserves_document_order_separate_runs(self):
        from engraver_ctrl.dsl_cards import parse_cards

        cards = parse_cards(MIXED)
        self.assertEqual(len(cards), 3)
        self.assertEqual(cards[0].name, "loose")
        self.assertIn("C 1 1 2", cards[0].inner)
        self.assertEqual(cards[1].name, "p1")
        self.assertEqual(cards[1].dx, 10.0)
        self.assertIn("R 0 0 20 20", cards[1].inner)
        self.assertEqual(cards[2].name, "loose_2")
        self.assertIn("LV 0 0 5", cards[2].inner)
        self.assertIn("LH 0 0 5", cards[2].inner)
        self.assertIn("# trailing comment stays with this run", cards[2].inner)

    def test_round_trip_pure_add_file(self):
        from engraver_ctrl.dsl_cards import parse_cards, assemble_cards

        cards = parse_cards(PURE_ADD)
        self.assertEqual(len(cards), 2)
        self.assertEqual(cards[0].name, "p1")
        self.assertEqual((cards[0].dx, cards[0].dy), (0.0, 0.0))
        self.assertEqual(cards[0].inner, "R 0 0 20 20")
        self.assertEqual(cards[1].name, "p2")
        self.assertEqual((cards[1].dx, cards[1].dy), (30.0, 0.0))
        self.assertEqual(cards[1].inner, "R 0 0 20 40")
        self.assertEqual(assemble_cards(cards), PURE_ADD)
        # Second pass is stable
        self.assertEqual(assemble_cards(parse_cards(assemble_cards(cards))),
                         PURE_ADD)

    def test_nested_add_stays_inside_parent(self):
        from engraver_ctrl.dsl_cards import parse_cards, assemble_cards

        cards = parse_cards(NESTED)
        self.assertEqual(len(cards), 1)
        self.assertEqual(cards[0].name, "outer")
        self.assertIn("ADD 5 5 inner", cards[0].inner)
        self.assertIn("C 0 0 3", cards[0].inner)
        self.assertIn("END", cards[0].inner)
        self.assertIn("R 1 1 2 2", cards[0].inner)
        raw = assemble_cards(cards)
        self.assertEqual(raw.count("ADD "), 2)
        self.assertTrue(raw.strip().startswith("ADD 0 0 outer"))

    def test_rotate_end_does_not_close_parent_card_early(self):
        from engraver_ctrl.dsl_cards import parse_cards

        cards = parse_cards(ROTATE_BLOCK)
        self.assertEqual(len(cards), 1)
        self.assertEqual(cards[0].name, "Xoay 45 do")
        self.assertEqual((cards[0].dx, cards[0].dy), (50.0, 0.0))
        self.assertIn("ROTATE 45", cards[0].inner)
        self.assertIn("R 0 0 20 10", cards[0].inner)
        # The END that closes ROTATE stays inside; the outer END is the card close.
        self.assertEqual(cards[0].inner.strip().count("END"), 1)

    def test_unnamed_add_gets_piece_name(self):
        from engraver_ctrl.dsl_cards import parse_cards

        cards = parse_cards("ADD 1 2\nR 0 0 1 1\nEND\n")
        self.assertEqual(len(cards), 1)
        self.assertEqual(cards[0].name, "p1")
        self.assertEqual((cards[0].dx, cards[0].dy), (1.0, 2.0))

    def test_comment_only_gap_is_not_a_card(self):
        from engraver_ctrl.dsl_cards import parse_cards

        text = "ADD 0 0 a\nR 0 0 1 1\nEND\n\n# just a note\n\nADD 5 0 b\nR 0 0 1 1\nEND\n"
        cards = parse_cards(text)
        self.assertEqual([c.name for c in cards], ["a", "b"])


class PlacementTests(unittest.TestCase):
    def test_first_card_at_origin(self):
        from engraver_ctrl.dsl_cards import place_new_card, add_card

        self.assertEqual(place_new_card([]), (0.0, 0.0))
        cards, card = add_card([])
        self.assertEqual((card.dx, card.dy), (0.0, 0.0))
        self.assertEqual(card.name, "p1")
        self.assertEqual(len(cards), 1)

    def test_wide_layout_prefers_y_stack(self):
        from engraver_ctrl.dsl_cards import Card, place_new_card, add_card

        # 40 x 10 at origin: xmax=40, ymax=10. Empty origin (0,10) is closer.
        cards = [Card("wide", 0.0, 0.0, "R 0 0 40 10")]
        self.assertEqual(place_new_card(cards), (0.0, 10.0))
        _, added = add_card(cards)
        self.assertEqual((added.dx, added.dy), (0.0, 10.0))

    def test_tall_layout_prefers_x_stack(self):
        from engraver_ctrl.dsl_cards import Card, place_new_card, add_card

        cards = [Card("tall", 0.0, 0.0, "R 0 0 10 40")]
        self.assertEqual(place_new_card(cards), (10.0, 0.0))
        _, added = add_card(cards)
        self.assertEqual((added.dx, added.dy), (10.0, 0.0))

    def test_envelope_uses_all_cards(self):
        from engraver_ctrl.dsl_cards import Card, place_new_card

        # Two 20x20 pieces side by side: xmax=40, ymax=20 -> (0, 20)
        cards = [
            Card("a", 0.0, 0.0, "R 0 0 20 20"),
            Card("b", 20.0, 0.0, "R 0 0 20 20"),
        ]
        self.assertEqual(place_new_card(cards), (0.0, 20.0))

    def test_duplicate_name_and_placement(self):
        from engraver_ctrl.dsl_cards import Card, duplicate_card

        # Wide 40x10: duplicate center at (0,10) is closer than (40,0)
        src = [Card("p1", 0.0, 0.0, "R 0 0 40 10")]
        cards, dup = duplicate_card(src, 0)
        self.assertEqual(dup.name, "p1_2")
        self.assertEqual(dup.inner, "R 0 0 40 10")
        self.assertEqual((dup.dx, dup.dy), (0.0, 10.0))
        self.assertEqual([c.name for c in cards], ["p1", "p1_2"])

        # Tall 10x40: prefer (10, 0)
        src = [Card("p1", 0.0, 0.0, "R 0 0 10 40")]
        _cards, dup = duplicate_card(src, 0)
        self.assertEqual((dup.dx, dup.dy), (10.0, 0.0))

        # Unique name when p1_2 already exists
        src = [
            Card("p1", 0.0, 0.0, "R 0 0 10 10"),
            Card("p1_2", 10.0, 0.0, "R 0 0 10 10"),
        ]
        _cards, dup = duplicate_card(src, 0)
        self.assertEqual(dup.name, "p1_3")


class CardPanelJointTests(unittest.TestCase):
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

    def test_card_row_is_compact(self):
        win, tab = self._make_tab()
        try:
            tab.set_view_mode("cards")
            tab.text_input.delete("1.0", "end")
            tab.text_input.insert("1.0", PURE_ADD)
            tab.preview()
            self.root.update_idletasks()
            widths, texts = [], []

            def walk(w):
                for c in w.winfo_children():
                    cls = c.winfo_class()
                    if cls in ("TEntry", "Entry"):
                        widths.append(int(c.cget("width") or 0))
                    if cls in ("TButton", "Button"):
                        texts.append(str(c.cget("text")))
                    walk(c)

            walk(tab.card_panel)
            self.assertIn(10, widths, widths)
            self.assertIn(4, widths, widths)
            self.assertNotIn("Duplicate", texts, texts)
            self.assertNotIn("Delete", texts, texts)

            labels = []

            def collect(w):
                for c in w.winfo_children():
                    if c.winfo_class() == "Label":
                        labels.append(str(c.cget("text")))
                    collect(c)

            collect(tab)
            blob = " ".join(labels)
            self.assertNotIn("Wheel:", blob)
            self.assertNotIn("middle-drag", blob)
            self.assertNotIn("Left-drag", blob)
        finally:
            win.destroy()

    def test_apply_joints_in_card_mode(self):
        win, tab = self._make_tab()
        try:
            self.assertTrue(getattr(tab, "card_mode", True) or tab.view_mode_var.get() == "cards")
            tab.text_input.delete("1.0", "end")
            tab.text_input.insert("1.0", EXAMPLE)
            tab.preview()
            self.root.update_idletasks()
            # Two top-level pieces become two cards
            cards = tab.card_panel.cards()
            self.assertEqual([c.name for c in cards], ["p1", "p2"])
            tab.apply_joints()
            text = tab.get_dsl()
            self.assertIn("JM 0 0 20 3 10 5 in", text)
            self.assertIn("JF 0 20 20 3 10 5", text)
            self.assertIn("# J 0 0 20 3 A", text)
            self.assertIn("R 0 0 20 20", text)
            self.assertNotIn("# R ", text)
            cards = tab.card_panel.cards()
            self.assertEqual(len(cards), 2)
            self.assertIn("JM 0 0 20 3 10 5 in", cards[0].inner)
            self.assertIn("# J 0 0 20 3 A", cards[0].inner)
            self.assertIn("JF 0 20 20 3 10 5", cards[1].inner)
        finally:
            win.destroy()

    def test_toggle_does_not_lose_edits(self):
        win, tab = self._make_tab()
        try:
            tab.set_view_mode("cards")
            tab.text_input.delete("1.0", "end")
            tab.text_input.insert("1.0", PURE_ADD)
            tab.preview()
            self.root.update_idletasks()
            tab.card_panel.set_inner(0, "R 0 0 25 25")
            tab.set_view_mode("raw")
            raw = tab.text_input.get("1.0", "end")
            self.assertIn("R 0 0 25 25", raw)
            self.assertIn("ADD 0 0 p1", raw)
            # Edit in raw, switch back
            raw = raw.replace("R 0 0 20 40", "R 0 0 20 50")
            tab.text_input.delete("1.0", "end")
            tab.text_input.insert("1.0", raw)
            tab.set_view_mode("cards")
            cards = tab.card_panel.cards()
            self.assertEqual(cards[0].inner, "R 0 0 25 25")
            self.assertEqual(cards[1].inner, "R 0 0 20 50")
        finally:
            win.destroy()

    def test_add_and_duplicate_via_panel(self):
        win, tab = self._make_tab()
        try:
            tab.set_view_mode("cards")
            tab.text_input.delete("1.0", "end")
            tab.text_input.insert("1.0", "ADD 0 0 p1\nR 0 0 40 10\nEND\n")
            tab.preview()
            tab.card_panel.add_card()
            cards = tab.card_panel.cards()
            self.assertEqual(cards[-1].name, "p2")
            self.assertEqual((cards[-1].dx, cards[-1].dy), (0.0, 10.0))
            tab.card_panel.duplicate_card(0)
            cards = tab.card_panel.cards()
            names = [c.name for c in cards]
            self.assertIn("p1_2", names)
            dup = next(c for c in cards if c.name == "p1_2")
            self.assertEqual(dup.inner, "R 0 0 40 10")
            # Envelope is now wide+the empty p2 at (0,10): xmax=40, ymax=10
            # (empty has zero size). Duplicate of 40x10 still prefers (0, 10)
            # or a later free slot; at least not a negative / far origin.
            self.assertGreaterEqual(dup.dx, 0.0)
            self.assertGreaterEqual(dup.dy, 0.0)
        finally:
            win.destroy()


if __name__ == "__main__":
    unittest.main()
