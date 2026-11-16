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



class SizeBorderTests(unittest.TestCase):
    def test_unmarked_dsl_infers_size_without_treating_r_as_border(self):
        from engraver_ctrl.dsl_cards import parse_cards, assemble_cards

        cards = parse_cards(PURE_ADD)
        self.assertEqual(len(cards), 2)
        self.assertEqual(cards[0].inner, "R 0 0 20 20")
        self.assertFalse(cards[0].border)
        self.assertEqual((cards[0].w, cards[0].h), (20.0, 20.0))
        self.assertEqual(cards[1].inner, "R 0 0 20 40")
        self.assertFalse(cards[1].border)
        self.assertEqual((cards[1].w, cards[1].h), (20.0, 40.0))
        # Unmarked files stay byte-for-byte: no meta comment, no stolen R.
        self.assertEqual(assemble_cards(cards), PURE_ADD)
        self.assertEqual(assemble_cards(parse_cards(assemble_cards(cards))),
                         PURE_ADD)

    def test_infer_size_uses_max_extents_from_origin(self):
        from engraver_ctrl.dsl_cards import infer_size, parse_cards

        # Circle centred at (50,50) r=30 extends to 80,80.
        self.assertEqual(infer_size("C 50 50 30"), (80.0, 80.0))
        cards = parse_cards(LOOSE)
        self.assertEqual(len(cards), 1)
        self.assertFalse(cards[0].border)
        # Loose body has C 50 50 30 and R 20 30 40 50 (to 60,80) -> 80,80.
        self.assertEqual((cards[0].w, cards[0].h), (80.0, 80.0))

    def test_border_round_trip_strips_r_from_inner(self):
        from engraver_ctrl.dsl_cards import (
            Card, assemble_cards, parse_cards, extract_card_meta,
        )

        src = [Card("p1", 0.0, 0.0, "J 0 0 20 3 A", w=20.0, h=20.0, border=True)]
        raw = assemble_cards(src)
        self.assertIn("# card w=20 h=20 border=1", raw)
        self.assertIn("R 0 0 20 20", raw)
        self.assertTrue(raw.strip().startswith("ADD 0 0 p1"))
        # Marker and R come first, then the remaining inner.
        body = raw.split("ADD 0 0 p1", 1)[1]
        self.assertLess(body.find("# card w=20 h=20 border=1"),
                        body.find("R 0 0 20 20"))
        self.assertLess(body.find("R 0 0 20 20"), body.find("J 0 0 20 3 A"))

        cards = parse_cards(raw)
        self.assertEqual(len(cards), 1)
        self.assertTrue(cards[0].border)
        self.assertEqual((cards[0].w, cards[0].h), (20.0, 20.0))
        self.assertEqual(cards[0].inner, "J 0 0 20 3 A")
        self.assertEqual(assemble_cards(cards), raw)
        # extract helper: unmarked R stays in inner
        inner, w, h, border = extract_card_meta("R 0 0 20 20\nJ 0 0 20 3 A")
        self.assertFalse(border)
        self.assertIn("R 0 0 20 20", inner)

    def test_trailing_card_border_comment_on_r_line(self):
        from engraver_ctrl.dsl_cards import parse_cards, assemble_cards

        text = "ADD 0 0 p1\nR 0 0 30 15  # card-border\nC 5 5 2\nEND\n"
        cards = parse_cards(text)
        self.assertEqual(len(cards), 1)
        self.assertTrue(cards[0].border)
        self.assertEqual((cards[0].w, cards[0].h), (30.0, 15.0))
        self.assertEqual(cards[0].inner, "C 5 5 2")
        raw = assemble_cards(cards)
        self.assertIn("# card w=30 h=15 border=1", raw)
        self.assertIn("R 0 0 30 15", raw)
        self.assertIn("C 5 5 2", raw)
        self.assertNotIn("# card-border", raw)

    def test_untick_border_removes_r_and_marker(self):
        from engraver_ctrl.dsl_cards import Card, assemble_cards, parse_cards

        card = Card("p1", 0.0, 0.0, "C 10 10 5", w=20.0, h=20.0, border=True)
        raw = assemble_cards([card])
        self.assertIn("R 0 0 20 20", raw)
        card.border = False
        raw = assemble_cards([card])
        self.assertNotIn("R 0 0 20 20", raw)
        # C 10 10 5 extends to 15,15; w/h 20,20 is custom, so the size
        # comment is kept (border=0) and the generated R is gone.
        self.assertIn("# card w=20 h=20 border=0", raw)
        self.assertIn("C 10 10 5", raw)
        again = parse_cards(raw)
        self.assertFalse(again[0].border)
        self.assertEqual((again[0].w, again[0].h), (20.0, 20.0))
        self.assertEqual(again[0].inner, "C 10 10 5")

    def test_custom_size_without_border_persists_via_comment_only(self):
        from engraver_ctrl.dsl_cards import Card, assemble_cards, parse_cards

        # Inferred from R 0 0 20 20 is 20x20; custom 25x30 is persisted.
        card = Card("p1", 0.0, 0.0, "R 0 0 20 20", w=25.0, h=30.0, border=False)
        raw = assemble_cards([card])
        self.assertIn("# card w=25 h=30 border=0", raw)
        self.assertEqual(raw.count("R 0 0"), 1)
        self.assertIn("R 0 0 20 20", raw)
        cards = parse_cards(raw)
        self.assertFalse(cards[0].border)
        self.assertEqual((cards[0].w, cards[0].h), (25.0, 30.0))
        self.assertEqual(cards[0].inner, "R 0 0 20 20")

    def test_changing_wh_updates_assembled_border_rect(self):
        from engraver_ctrl.dsl_cards import Card, assemble_cards

        card = Card("p1", 0.0, 0.0, "", w=10.0, h=12.0, border=True)
        self.assertIn("R 0 0 10 12", assemble_cards([card]))
        card.w, card.h = 40.0, 15.5
        raw = assemble_cards([card])
        self.assertIn("R 0 0 40 15.5", raw)
        self.assertIn("# card w=40 h=15.5 border=1", raw)
        self.assertNotIn("R 0 0 10 12", raw)

    def test_placement_uses_wh_when_set(self):
        from engraver_ctrl.dsl_cards import Card, place_new_card, add_card

        # Empty inner, size 40x10 at origin: envelope xmax=40, ymax=10.
        cards = [Card("wide", 0.0, 0.0, "", w=40.0, h=10.0, border=True)]
        self.assertEqual(place_new_card(cards), (0.0, 10.0))
        _, added = add_card(cards)
        self.assertEqual((added.dx, added.dy), (0.0, 10.0))

        cards = [Card("tall", 0.0, 0.0, "", w=10.0, h=40.0, border=True)]
        self.assertEqual(place_new_card(cards), (10.0, 0.0))

    def test_duplicate_copies_size_and_border(self):
        from engraver_ctrl.dsl_cards import Card, duplicate_card, assemble_cards

        src = [Card("p1", 0.0, 0.0, "C 2 2 1", w=40.0, h=10.0, border=True)]
        cards, dup = duplicate_card(src, 0)
        self.assertEqual(dup.name, "p1_2")
        self.assertEqual(dup.inner, "C 2 2 1")
        self.assertTrue(dup.border)
        self.assertEqual((dup.w, dup.h), (40.0, 10.0))
        # 40x10: duplicate centre at (0,10) is closer than (40,0)
        self.assertEqual((dup.dx, dup.dy), (0.0, 10.0))
        raw = assemble_cards(cards)
        self.assertEqual(raw.count("# card w=40 h=10 border=1"), 2)
        self.assertEqual(raw.count("R 0 0 40 10"), 2)

    def test_nested_add_r_is_not_a_border(self):
        from engraver_ctrl.dsl_cards import parse_cards

        cards = parse_cards(NESTED)
        self.assertEqual(len(cards), 1)
        self.assertFalse(cards[0].border)
        self.assertIn("ADD 5 5 inner", cards[0].inner)
        self.assertIn("R 0 0 30 30", cards[0].inner)
        # Outer extents include the 30x30 rect.
        self.assertEqual((cards[0].w, cards[0].h), (30.0, 30.0))

    def test_line_ranges_include_border_prefix(self):
        from engraver_ctrl.dsl_cards import (
            Card, assemble_cards, assemble_line_ranges, card_index_for_line,
        )

        cards = [Card("p1", 0.0, 0.0, "C 1 1 1", w=10.0, h=10.0, border=True)]
        raw = assemble_cards(cards)
        # ADD, # card, R, C, END  => 5 lines, then trailing newline
        self.assertEqual(assemble_line_ranges(cards), [(1, 5)])
        self.assertEqual(card_index_for_line(cards, 3), 0)
        self.assertEqual(len(raw.strip().splitlines()), 5)


class CardPanelSizeBorderTests(unittest.TestCase):
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

    def test_row_has_w_h_border_controls(self):
        win, tab = self._make_tab()
        try:
            tab.set_view_mode("cards")
            tab.text_input.delete("1.0", "end")
            tab.text_input.insert("1.0", PURE_ADD)
            tab.preview()
            self.root.update_idletasks()
            labels, check_texts, widths = [], [], []

            def walk(w):
                for c in w.winfo_children():
                    cls = c.winfo_class()
                    if cls in ("TLabel", "Label"):
                        labels.append(str(c.cget("text")))
                    if cls in ("TCheckbutton", "Checkbutton"):
                        check_texts.append(str(c.cget("text")))
                    if cls in ("TEntry", "Entry"):
                        widths.append(int(c.cget("width") or 0))
                    walk(c)

            walk(tab.card_panel)
            self.assertIn("w", labels, labels)
            self.assertIn("h", labels, labels)
            self.assertIn("dx", labels, labels)
            self.assertIn("border", check_texts, check_texts)
            self.assertIn(10, widths)
            self.assertGreaterEqual(widths.count(4), 4)  # dx dy w h
            cards = tab.card_panel.cards()
            self.assertEqual((cards[0].w, cards[0].h), (20.0, 20.0))
            self.assertFalse(cards[0].border)
        finally:
            win.destroy()

    def test_tick_border_adds_rect_and_untick_removes_it(self):
        win, tab = self._make_tab()
        try:
            tab.set_view_mode("cards")
            tab.text_input.delete("1.0", "end")
            tab.text_input.insert("1.0", "ADD 0 0 p1\nC 10 10 5\nEND\n")
            tab.preview()
            self.root.update_idletasks()
            cards = tab.card_panel.cards()
            self.assertEqual(len(cards), 1)
            self.assertFalse(cards[0].border)
            self.assertEqual((cards[0].w, cards[0].h), (15.0, 15.0))
            self.assertEqual(cards[0].inner, "C 10 10 5")

            row = tab.card_panel._rows[0]
            row["border_var"].set(True)
            tab.card_panel._apply_fields(0, preview=True)
            self.root.update_idletasks()
            cards = tab.card_panel.cards()
            self.assertTrue(cards[0].border)
            raw = tab.card_panel.assemble()
            self.assertIn("# card w=15 h=15 border=1", raw)
            self.assertIn("R 0 0 15 15", raw)
            self.assertIn("C 10 10 5", raw)
            # Inner editor still shows only the original geometry.
            self.assertEqual(cards[0].inner, "C 10 10 5")

            row["w_var"].set("25")
            row["h_var"].set("18")
            tab.card_panel._apply_fields(0, preview=True)
            raw = tab.card_panel.assemble()
            self.assertIn("R 0 0 25 18", raw)
            self.assertIn("# card w=25 h=18 border=1", raw)

            row["border_var"].set(False)
            tab.card_panel._apply_fields(0, preview=True)
            raw = tab.card_panel.assemble()
            self.assertNotIn("R 0 0 25 18", raw)
            self.assertIn("C 10 10 5", raw)
            self.assertFalse(tab.card_panel.cards()[0].border)
        finally:
            win.destroy()


if __name__ == "__main__":
    unittest.main()
