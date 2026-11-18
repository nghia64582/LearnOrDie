#!/usr/bin/env python3
"""Unit tests for the plywood box DSL generator."""

from __future__ import annotations

import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from box_maker.box_core import (
    FACE_NAMES,
    PAIRINGS,
    BoxResult,
    build_box,
    edge_joint_rect,
    face_size,
    pair_edge_length,
)
from engraver_ctrl.dsl_cards import parse_cards
from engraver_ctrl.dsl_joint import (
    DEFAULT_TEETH_DIVISIONS,
    THICKNESS,
    apply_joints,
    classify_mark,
    parse_joint_file,
    tooth_spans,
)


def _example():
    return build_box(100, 60, 40, thickness=3)


class FaceSizeTests(unittest.TestCase):
    def test_all_faces_keep_outer_dimensions(self):
        L, W, H = 100, 60, 40
        self.assertEqual(face_size("top", L, W, H), (L, W))
        self.assertEqual(face_size("bottom", L, W, H), (L, W))
        self.assertEqual(face_size("front", L, W, H), (L, H))
        self.assertEqual(face_size("behind", L, W, H), (L, H))
        self.assertEqual(face_size("left", L, W, H), (W, H))
        self.assertEqual(face_size("right", L, W, H), (W, H))

    def test_pair_edge_lengths_match(self):
        L, W, H = 100, 60, 40
        expected = {
            "TOP_FRONT": L, "TOP_BEHIND": L, "TOP_LEFT": W, "TOP_RIGHT": W,
            "BOTTOM_FRONT": L, "BOTTOM_BEHIND": L,
            "BOTTOM_LEFT": W, "BOTTOM_RIGHT": W,
            "FRONT_RIGHT": H, "RIGHT_BEHIND": H,
            "BEHIND_LEFT": H, "LEFT_FRONT": H,
        }
        for name, length in expected.items():
            self.assertEqual(pair_edge_length(name, L, W, H), length)
        # Cross-check against both sides of each pairing.
        for face_a, edge_a, face_b, edge_b, name, _ra, _rb in PAIRINGS:
            aw, ah = face_size(face_a, L, W, H)
            bw, bh = face_size(face_b, L, W, H)
            la = aw if edge_a in ("up", "down") else ah
            lb = bw if edge_b in ("up", "down") else bh
            self.assertEqual(la, lb, msg=name)
            self.assertEqual(la, pair_edge_length(name, L, W, H))

    def test_unknown_face_raises(self):
        with self.assertRaises(ValueError):
            face_size("lid", 10, 10, 10)


class JointRectTests(unittest.TestCase):
    def test_flush_on_every_edge(self):
        fw, fh, t = 100, 60, 3
        self.assertEqual(edge_joint_rect(fw, fh, "down", t), (0, 0, fw, t))
        self.assertEqual(edge_joint_rect(fw, fh, "up", t), (0, fh - t, fw, t))
        self.assertEqual(edge_joint_rect(fw, fh, "left", t), (0, 0, t, fh))
        self.assertEqual(edge_joint_rect(fw, fh, "right", t), (fw - t, 0, t, fh))

    def test_marks_stay_inside_the_face(self):
        fw, fh, t = 80, 50, 3
        for edge in ("up", "down", "left", "right"):
            x, y, w, h = edge_joint_rect(fw, fh, edge, t)
            self.assertGreaterEqual(x, 0)
            self.assertGreaterEqual(y, 0)
            self.assertLessEqual(x + w, fw)
            self.assertLessEqual(y + h, fh)
            self.assertEqual(min(w, h), t)
            self.assertEqual(max(w, h), fw if edge in ("up", "down") else fh)


class BuildBoxTests(unittest.TestCase):
    def test_six_faces_twelve_pairs(self):
        result = _example()
        self.assertIsInstance(result, BoxResult)
        self.assertEqual(len(result.faces), 6)
        self.assertEqual(len(result.pairs), 12)
        self.assertEqual({f.name for f in result.faces}, set(FACE_NAMES))

    def test_subset_drops_pairs_and_keeps_plain_edges(self):
        # Open box: no top. Four lid pairs disappear; wall and bottom remain.
        result = build_box(100, 60, 40, faces=["bottom", "left", "right",
                                               "behind", "front"])
        self.assertEqual(len(result.faces), 5)
        self.assertNotIn("top", {f.name for f in result.faces})
        names = {p.name for p in result.pairs}
        self.assertEqual(len(result.pairs), 8)
        self.assertTrue(all(not n.startswith("TOP_") for n in names))
        # Front's up edge (partner was top) must have no J.
        front = next(f for f in result.faces if f.name == "front")
        self.assertNotIn("up", {j.edge for j in front.joints})
        self.assertIn("down", {j.edge for j in front.joints})

    def test_only_two_adjacent_faces(self):
        result = build_box(100, 60, 40, faces=["front", "right"])
        self.assertEqual(len(result.faces), 2)
        self.assertEqual(len(result.pairs), 1)
        self.assertEqual(result.pairs[0].name, "FRONT_RIGHT")

    def test_opposite_faces_have_no_pair(self):
        result = build_box(100, 60, 40, faces=["front", "behind"])
        self.assertEqual(len(result.faces), 2)
        self.assertEqual(result.pairs, [])
        for face in result.faces:
            self.assertEqual(face.joints, [])

    def test_joint_positions_flush_and_lengths_equal(self):
        result = _example()
        by_name = {f.name: f for f in result.faces}
        for pair in result.pairs:
            a = next(j for j in by_name[pair.face_a].joints
                     if j.pair_name == pair.name)
            b = next(j for j in by_name[pair.face_b].joints
                     if j.pair_name == pair.name)
            fa, fb = by_name[pair.face_a], by_name[pair.face_b]
            self.assertEqual(
                (a.x, a.y, a.w, a.h),
                edge_joint_rect(fa.width, fa.height, pair.edge_a, 3),
            )
            self.assertEqual(
                (b.x, b.y, b.w, b.h),
                edge_joint_rect(fb.width, fb.height, pair.edge_b, 3),
            )
            len_a = a.w if a.w >= a.h else a.h
            len_b = b.w if b.w >= b.h else b.h
            self.assertAlmostEqual(len_a, len_b)
            self.assertAlmostEqual(len_a, pair.length)
            self.assertAlmostEqual(min(a.w, a.h), 3)
            self.assertAlmostEqual(min(b.w, b.h), 3)

    def test_roles_are_complementary(self):
        result = _example()
        for pair in result.pairs:
            self.assertIn(pair.role_a, ("M", "F"))
            self.assertIn(pair.role_b, ("M", "F"))
            self.assertNotEqual(pair.role_a, pair.role_b)
        # Lids are mortises; front/behind are tenons.
        by_name = {f.name: f for f in result.faces}
        for name in ("top", "bottom"):
            roles = {j.role for j in by_name[name].joints}
            self.assertEqual(roles, {"F"})
        for name in ("front", "behind"):
            roles = {j.role for j in by_name[name].joints}
            self.assertEqual(roles, {"M"})

    def test_layout_has_no_overlap_and_no_negative_origin(self):
        result = _example()
        boxes = []
        for face in result.faces:
            self.assertGreaterEqual(face.dx, 0)
            self.assertGreaterEqual(face.dy, 0)
            boxes.append((face.name, face.dx, face.dy, face.width, face.height))
        for i, (an, ax, ay, aw, ah) in enumerate(boxes):
            for bn, bx, by, bw, bh in boxes[i + 1:]:
                overlap = (ax + aw > bx + 1e-9 and bx + bw > ax + 1e-9
                           and ay + ah > by + 1e-9 and by + bh > ay + 1e-9)
                self.assertFalse(overlap, msg=f"{an} overlaps {bn}")

    def test_invalid_inputs(self):
        with self.assertRaises(ValueError):
            build_box(0, 60, 40)
        with self.assertRaises(ValueError):
            build_box(100, 60, 40, thickness=0)
        with self.assertRaises(ValueError):
            build_box(100, 60, 3, thickness=3)  # H not greater than t
        with self.assertRaises(ValueError):
            build_box(100, 60, 40, faces=[])
        with self.assertRaises(ValueError):
            build_box(100, 60, 40, faces=["top", "lid"])

    def test_lk_less_than_t_warning(self):
        # H=10, k=5 => 10/5=2 < t=3
        result = build_box(100, 60, 10, thickness=3)
        self.assertTrue(any("thinner than t=" in w for w in result.warnings))
        # The 100x60x40 example is fine (min edge 40/5=8 > 3)
        self.assertFalse(_example().warnings)


class ApplyAndCardTests(unittest.TestCase):
    def test_cards_round_trip_with_border(self):
        result = _example()
        cards = parse_cards(result.dsl)
        self.assertEqual(len(cards), 6)
        names = [c.name for c in cards]
        self.assertEqual(set(names), set(FACE_NAMES))
        for card in cards:
            self.assertTrue(card.border)
            self.assertIsNotNone(card.w)
            self.assertIsNotNone(card.h)
            face = next(f for f in result.faces if f.name == card.name)
            self.assertAlmostEqual(card.w, face.width)
            self.assertAlmostEqual(card.h, face.height)
            self.assertAlmostEqual(card.dx, face.dx)
            self.assertAlmostEqual(card.dy, face.dy)
            self.assertIn("J ", card.inner)
            self.assertNotIn("R 0 0", card.inner)
        # Re-assemble and parse again: borders stay ticked, J marks remain.
        from engraver_ctrl.dsl_cards import assemble_cards
        again = parse_cards(assemble_cards(cards))
        self.assertEqual(len(again), 6)
        for card in again:
            self.assertTrue(card.border)
            self.assertTrue(any(line.startswith("J ") for line in
                                card.inner.splitlines()))

    def test_apply_joints_succeeds_and_mates(self):
        result = _example()
        applied = apply_joints(result.dsl)
        errors = [w for w in applied.warnings if w.level == "error"]
        self.assertEqual(errors, [], msg=[w.message for w in errors])
        self.assertEqual(applied.applied, 12)
        self.assertEqual(applied.skipped, 0)
        self.assertEqual(applied.text.count("\nJM "), 12)
        self.assertEqual(applied.text.count("\nJF "), 12)
        # Original J lines are commented, not removed as geometry.
        self.assertGreaterEqual(applied.text.count("# J "), 24)

        # Every J was on an edge of its border R, and each pair has one
        # JM and one JF with identical tooth layout so teeth fill holes.
        marks, outlines, _ = parse_joint_file(result.dsl)
        for mark in marks:
            kind, _outline, _side = classify_mark(mark, outlines)
            self.assertEqual(kind, "edge", msg=f"{mark.name} on line {mark.line}")

        jm, jf = {}, {}
        for raw in applied.text.splitlines():
            parts = raw.strip().split()
            if not parts:
                continue
            if parts[0] == "JM" and len(parts) >= 8:
                # JM x y w h teeth first_d dir — keyed later per pair via
                # the preceding commented J name is awkward; group by
                # (length, teeth, first_d) instead after parsing numbers.
                nums = list(map(float, parts[1:7]))
                x, y, w, h, teeth, first_d = nums
                length = w if w >= h else h
                jm.setdefault((length, teeth, first_d), []).append(parts)
            elif parts[0] == "JF" and len(parts) >= 7:
                nums = list(map(float, parts[1:7]))
                x, y, w, h, teeth, first_d = nums
                length = w if w >= h else h
                jf.setdefault((length, teeth, first_d), []).append(parts)

        # Pair by identical (length, teeth, first_d); 12 JM/JF share 12 keys
        # (some edges share a length — L appears 4 times — so compare counts
        # and tooth spans directly).
        self.assertEqual(sum(len(v) for v in jm.values()), 12)
        self.assertEqual(sum(len(v) for v in jf.values()), 12)
        self.assertEqual(set(jm), set(jf))
        for key, jm_items in jm.items():
            length, teeth, first_d = key
            self.assertAlmostEqual(teeth, length / DEFAULT_TEETH_DIVISIONS)
            self.assertAlmostEqual(first_d, teeth)
            self.assertEqual(len(jm_items), len(jf[key]))
            spans = tooth_spans(length, teeth, first_d)
            # Holes start after a solid end and sit on even segments.
            self.assertGreaterEqual(spans[0][0], teeth - 1e-9)
            self.assertLessEqual(spans[-1][1], length - teeth + 1e-9)

    def test_apply_joints_on_open_box(self):
        result = build_box(100, 60, 40, faces=["bottom", "front", "left",
                                               "right", "behind"])
        applied = apply_joints(result.dsl)
        errors = [w for w in applied.warnings if w.level == "error"]
        self.assertEqual(errors, [])
        self.assertEqual(applied.applied, len(result.pairs))
        self.assertEqual(applied.text.count("\nJM "), len(result.pairs))
        self.assertEqual(applied.text.count("\nJF "), len(result.pairs))


if __name__ == "__main__":
    unittest.main()
