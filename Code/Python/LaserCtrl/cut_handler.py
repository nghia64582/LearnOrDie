import random
from typing import List

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
    count = 100000

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

if __name__ == "__main__":
    d = 100
    a = generate(d, n=30)
    print("Input:", a)

    print("\nFFD result:")
    result = cut_ffd(d, a)
    print(result, len(result))

    print("\nBFD result:")
    result = cut_bfd(d, a)
    print(result, len(result))

    print("\nOptimized result:")
    result = cut_optimize(d, a)
    print(result, len(result))

    print("\nTheorical optimal :", (sum(a) + d - 1) // d)
