import random
from typing import List, Tuple
import xml.etree.ElementTree as ET

def generate(d: int, n: int = 20) -> List[int]:
    # Generate a list of n random
    # Try to repeat a number
    result = []
    while len(result) < n:
        for n_bars in range(1, 4):
            bar_length = random.randint(10, random.randint(10, d))
            result += [bar_length] * n_bars
            if len(result) >= n:
                result = result[:n]
                break
    return result

def place_into_bin(bins: List[List[int]], d: int, item: int, idx: int):
    """Try to place item into bins[idx]. Return True if success."""
    if sum(bins[idx]) + item <= d:
        bins[idx].append(item)
        return True
    return False

def cut_ffd(d: int, a: List[int]) -> List[List[int]]:
    """First Fit Decreasing. Very fast, near-optimal."""
    pieces = sorted(a, reverse=True)
    bins = []

    for item in pieces:
        placed = False
        for i in range(len(bins)):
            if place_into_bin(bins, d, item, i):
                placed = True
                break
        if not placed:
            bins.append([item])

    return bins

def cut_bfd(d: int, a: List[int]) -> List[List[int]]:
    """Best Fit Decreasing."""
    pieces = sorted(a, reverse=True)
    bins = []

    for item in pieces:
        best_idx = -1
        best_remain = d + 1

        for i in range(len(bins)):
            cur_sum = sum(bins[i])
            if cur_sum + item <= d:
                remain = d - (cur_sum + item)
                if remain < best_remain:
                    best_remain = remain
                    best_idx = i

        if best_idx == -1:
            bins.append([item])
        else:
            bins[best_idx].append(item)

    return bins

def local_optimize_swap(bins: List[List[int]], d: int) -> List[List[int]]:
    """Try simple 1-1 swaps to reduce number of bins."""
    improved = True
    count = 10000

    while improved:
        improved = False
        count -= 1
        if count % 10000 == 0:
            print(count)
        if count <= 0:
            break
        for i in range(len(bins)):
            for j in range(i + 1, len(bins)):
                A, B = bins[i], bins[j]

                # Try swap each pair a in A, b in B
                for ai in range(len(A)):
                    for bi in range(len(B)):
                        a_item = A[ai]
                        b_item = B[bi]

                        new_A_sum = sum(A) - a_item + b_item
                        new_B_sum = sum(B) - b_item + a_item

                        if new_A_sum <= d and new_B_sum <= d:
                            # Accept swap
                            A[ai], B[bi] = B[bi], A[ai]
                            improved = True

                # After swapping, if one bin becomes empty, remove it
                if sum(bins[j]) == 0:
                    bins.pop(j)
                    return bins  # restructure => restart

    # Finally sort bins by fill level (optional)
    bins.sort(key=lambda x: sum(x), reverse=True)
    return bins

def cut_optimize(d: int, a: List[int]) -> List[List[int]]:
    """FFD + Local Optimization"""
    bins = cut_ffd(d, a)
    bins = local_optimize_swap(bins, d)
    return bins

def compute_cut_lines_fixed(bins: List[List[int]], d: int, r: int, c: int,
                            include_end_cut: bool = False) -> List[Tuple[float, float, float]]:
    """
    Trả về danh sách các đường cắt cần thực hiện theo định dạng:
        (start_x, y, length)
    - start_x: toạ độ x bắt đầu đường cắt (mm)
    - y: toạ độ theo chiều dài que (mm) nơi đặt đường cắt (đường song song Ox)
    - length: độ dài đường cắt (mm)

    Quy ước:
    - Que i (i = 0,1,2,...) có cạnh trái tại x = i*(r+c)
      Ta bắt đầu cut ở start_x = i*(r+c) - 1 (dư 1 mm về phía trái)
    - Chiều dài cut = r + 2 (dư 1 mm hai đầu)
    - Với mỗi que: tạo cut tại y = 0 (đầu que) rồi các vị trí cumsum sau mỗi miếng (nếu pos < d)
    - Nếu include_end_cut=True thì cũng tạo cut tại pos == d
    """
    cut_lines: List[Tuple[float, float, float]] = []

    cut_len = r + 4  # mỗi đường cắt dài r + 4 mm (2mm mỗi đầu)

    for i, pieces in enumerate(bins):
        start_x = i * (r + c) - 2  # que 0 => -2 ; que 1 => (r+c)-2 ; ...
        # luôn cần cắt ở y = 0 để cắt phần thừa đầu
        cut_lines.append((start_x, 0.0, cut_len))

        pos = 0
        for piece in pieces:
            pos += piece
            # Nếu pos == d thì thường không cần cắt (mép cuối),
            # nhưng nếu người dùng muốn, bật include_end_cut=True
            if pos < d or (include_end_cut and pos == d):
                cut_lines.append((start_x, float(pos), cut_len))
            # nếu pos > d => input không hợp lệ (miếng > d), ta vẫn bỏ qua

    return cut_lines

def export_svg(
    cut_lines,
    filename,
    stroke_width=0.2,
    stroke_color="#FF0000"
):
    import xml.etree.ElementTree as ET

    ox, oy = (0, 0)

    # Compute max_y for flipping
    ys = [y for _, y, _ in cut_lines]
    max_y = max(ys)

    # Transform all coordinates first
    transformed = []
    all_x = []
    all_y = []

    for x, y, length in cut_lines:
        x1 = x
        x2 = x + length
        yf = max_y - y

        x1f = x1 + ox
        x2f = x2 + ox
        y1f = yf + oy
        y2f = yf + oy

        transformed.append((x1f, y1f, x2f, y2f))
        all_x.extend([x1f, x2f])
        all_y.extend([y1f, y2f])

    # Compute bounding box
    min_x = min(all_x)
    max_x = max(all_x)
    min_y = min(all_y)
    max_y = max(all_y)

    width = max_x - min_x
    height = max_y - min_y

    # Keep absolute coords — DO NOT shift the viewBox to min_x/min_y
    svg = ET.Element(
        "svg",
        xmlns="http://www.w3.org/2000/svg",
        version="1.1",
        width=f"{width}mm",
        height=f"{height}mm",
        viewBox=f"{min_x} {min_y} {width} {height}"
    )

    for x1, y1, x2, y2 in transformed:
        ET.SubElement(svg, "line", {
            "x1": f"{x1:.3f}",
            "y1": f"{y1:.3f}",
            "x2": f"{x2:.3f}",
            "y2": f"{y2:.3f}",
            "stroke": stroke_color,
            "stroke-width": f"{stroke_width}",
            "fill": "none"
        })

    tree = ET.ElementTree(svg)
    tree.write(filename, encoding="utf-8", xml_declaration=True)

    print("[OK] Absolute-coordinate SVG exported:", filename)

def export_gcode(cut_lines, filename,
                 feedrate=600,
                 laser_power=100):
    """
    Xuất G-code để chạy cắt thật bằng LaserGRBL.
    Hệ tọa độ giữ nguyên 100%.
    """

    lines = []
    lines.append("; --- Laser Cut Generated by Tool ---")
    lines.append("G21 ; mm mode")
    lines.append("G90 ; absolute coordinates")
    lines.append("M5  ; laser off")
    
    for x, y, length in cut_lines:
        x1 = x
        y1 = y
        x2 = x + length
        y2 = y

        # Chạy đến vị trí đầu
        lines.append(f"\nG0 X{x1:.3f} Y{y1:.3f}")
        lines.append(f"M3 S{laser_power}")  # bật laser
        lines.append(f"G1 X{x2:.3f} Y{y2:.3f} F{feedrate}")  # cắt
        lines.append("M5")  # tắt laser

    lines.append("\nG0 X0 Y0 ; Về gốc sau khi cắt")
    lines.append("M5")
    lines.append("; --- END ---\n")

    with open(filename, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"[OK] G-code exported → {filename}")

if __name__ == "__main__":
    # d là độ dài que
    d = 103
    # a là danh sách độ dài các miếng cần cắt
    a = [20, 20, 20, 20, 25, 25, 25, 25, 30, 30, 30, 30]
    # r là độ rộng que
    r = 10
    # c là khoảng cách giữa các que (hai cạnh kề nhau)
    c = 5
    print("Input:", a)
    # Để cắt hình tròn tâm 10, 10, bán kính 5 dùng g code 
    #

    print("\nFFD result:")
    result = cut_ffd(d, a)
    print(result, len(result))

    print("\nBFD result:")
    result = cut_bfd(d, a)
    print(result, len(result))

    print("\nOptimized result:")
    first_result = cut_optimize(d, a)
    print(first_result, len(first_result))
    print("\nTheorical optimal :", (sum(a) + d - 1) // d)

    cut_lines = compute_cut_lines_fixed(first_result, d, r=10, c=5,
                                        include_end_cut=False)

    print("\nCut lines:")
    for line in cut_lines:
        print(line)

    export_svg(cut_lines, "cut_plan.svg")
    export_gcode(cut_lines, "cut_plan.gcode")