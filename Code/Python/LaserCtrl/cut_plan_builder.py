from dataclasses import dataclass
from typing import List, Tuple
import math

# IMPORT cut_optimize từ module hiện có (cut_handler)
# sửa import nếu tên module khác
from cut_handler import cut_optimize


@dataclass
class Part:
    """
    Mô tả một chi tiết nhỏ cần cắt.
    - length: chiều dài chi tiết (mm)
    - is_cut_down: True nếu bo/cắt ở đầu dưới (mép dưới) (bo 180°)
    - is_cut_up: True nếu bo/cắt ở đầu trên (mép trên) (bo 180°)
    - hole_centers: danh sách vị trí các tâm lỗ (mm) tính từ mép dưới của chi tiết
    """
    length: float
    is_cut_down: bool
    is_cut_up: bool
    hole_centers: List[float]


@dataclass
class CutPlan:
    """
    Kết quả kế hoạch cắt:
    - stick_width: chiều rộng que
    - cuts: list các đoạn cắt ngang, tuple (start_x, y, length_of_cut)
    - holes: list các tâm lỗ, tuple (center_x, center_y)
    - radius: bán kính lỗ (dùng chung cho tất cả lỗ)
    - arches: list các arch (center_x, center_y, is_up)
        is_up = True => cung 180° mở lên (arch hướng lên)
        is_up = False => cung 180° mở xuống (arch hướng xuống)
    """
    stick_width: float
    cuts: List[Tuple[float, float, float]]
    holes: List[Tuple[float, float]]
    radius: float
    arches: List[Tuple[float, float, bool]]
    # print cut plan
    def __str__(self):
        s = "CutPlan:\n"
        s += f"Stick Width: {self.stick_width:.3f}\n"
        s += "Cuts:\n"
        for (sx, y, length) in self.cuts:
            s += f"  StartX: {sx:.3f}, Y: {y:.3f}, Length: {length:.3f}\n"
        s += "Holes:\n"
        for (cx, cy) in self.holes:
            s += f"  CenterX: {cx:.3f}, CenterY: {cy:.3f}\n"
        s += f"Radius: {self.radius:.3f}\n"
        s += "Arches:\n"
        for (cx, cy, is_up) in self.arches:
            dir_str = "Up" if is_up else "Down"
            s += f"  CenterX: {cx:.3f}, CenterY: {cy:.3f}, Direction: {dir_str}\n"
        return s


def build_cut_plan(
    stock_length: float,
    parts: List[Part],
    width: float,
    gap: float,
    hole_radius: float,
    include_end_cut: bool = True
) -> CutPlan:
    """
    Tạo CutPlan từ:
    - stock_length: chiều dài 1 thanh gốc (d)
    - parts: danh sách Part (mỗi Part là 1 miếng cần cắt)
    - width: chiều rộng thanh (r)
    - gap: khoảng cách giữa các thanh khi xếp (c)
    - hole_radius: bán kính các lỗ (chung)
    - include_end_cut: nếu True tạo cut tại y=0 và sau mỗi miếng (trừ khi pos >= stock_length)

    Trả về CutPlan.
    """

    requested_lengths = [p.length for p in parts]

    bins = cut_optimize(stock_length, requested_lengths)

    remaining = []
    for idx, p in enumerate(parts):
        remaining.append((p.length, idx))
    
    tol = 1e-6

    # helper to pop index matching length
    def pop_part_index_by_length(target_length):
        for i, (ln, idx) in enumerate(remaining):
            if abs(ln - target_length) <= tol:
                return remaining.pop(i)[1]
        # if not found exact, try nearest (fallback)
        for i, (ln, idx) in enumerate(remaining):
            if abs(ln - target_length) < 1e-3:
                return remaining.pop(i)[1]
        # if still not found raise
        raise ValueError(f"Cannot match part length {target_length} to any remaining part")

    cuts: List[Tuple[float, float, float]] = []
    holes_out: List[Tuple[float, float]] = []
    arches_out: List[Tuple[float, float, bool]] = []

    cut_extra_margin = 1.0
    cut_length_overall = width + 2.0

    for bin_index, bin_pieces in enumerate(bins):
        start_x = bin_index * (width + gap) - cut_extra_margin
        x_center = start_x + (width / 2.0) + cut_extra_margin
        center_x_for_holes_and_arch = start_x + cut_extra_margin + (width / 2.0)

        y_cursor = 0.0

        if include_end_cut:
            cuts.append((start_x, 0.0, cut_length_overall))

        for piece_length in bin_pieces:
            part_index = pop_part_index_by_length(piece_length)
            part = parts[part_index]

            y_cursor += piece_length
            cut_y = y_cursor

            if cut_y < stock_length - 1e-9 or include_end_cut:
                cuts.append((start_x, cut_y, cut_length_overall))

            for hole_center_rel in part.hole_centers:
                previous_y_before_piece = cut_y - piece_length
                abs_hole_y = previous_y_before_piece + hole_center_rel
                abs_hole_x = center_x_for_holes_and_arch
                holes_out.append((abs_hole_x, abs_hole_y))

            if part.is_cut_down:
                previous_y_before_piece = cut_y - piece_length
                arch_center_x = center_x_for_holes_and_arch
                arch_center_y = previous_y_before_piece + (width / 2.0)
                # lower arch points up -> is_up = True
                arches_out.append((arch_center_x, arch_center_y, True))

            if part.is_cut_up:
                arch_center_x = center_x_for_holes_and_arch
                arch_center_y = cut_y - (width / 2.0)
                # upper arch points down -> is_up = False
                arches_out.append((arch_center_x, arch_center_y, False))


    cut_plan = CutPlan(
        cuts=cuts,
        holes=holes_out,
        radius=hole_radius,
        arches=arches_out,
        stick_width=width
    )
    print(cut_plan)

    return cut_plan

if __name__ == "__main__":
    # Example usage
    parts = [
        Part(length=50.0, is_cut_down=True, is_cut_up=False, hole_centers=[10.0, 30.0]),
        Part(length=70.0, is_cut_down=False, is_cut_up=True, hole_centers=[20.0]),
        Part(length=30.0, is_cut_down=True, is_cut_up=True, hole_centers=[]),
        Part(length=90.0, is_cut_down=False, is_cut_up=False, hole_centers=[45.0]),
    ]

    stock_length = 100.0
    width = 10.0
    gap = 5.0
    hole_radius = 1.5

    cut_plan = build_cut_plan(
        stock_length=stock_length,
        parts=parts,
        width=width,
        gap=gap,
        hole_radius=hole_radius,
        include_end_cut=True
    )
    
    print(cut_plan)