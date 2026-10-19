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

    cut_len = r + 2  # mỗi đường cắt dài r + 2 mm (1mm mỗi đầu)

    for i, pieces in enumerate(bins):
        start_x = i * (r + c) - 1  # que 0 => -1 ; que 1 => (r+c)-1 ; ...
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
