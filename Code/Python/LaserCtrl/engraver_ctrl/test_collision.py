from engraver_ctrl.collision import classify, Collider
import engraver_ctrl.collision as C

def rect(x, y, w, h):
    return [(x, y, x + w, y), (x + w, y, x + w, y + h),
            (x + w, y + h, x, y + h), (x, y + h, x, y)]

def run(use_np):
    def coll(a, b):
        c = Collider([(0, a)], [(1, b)])
        c.use_np = use_np and C.np is not None
        return c.collides(0, 0)
    cases = [
        (rect(0, 20, 20, 20), rect(0, 0, 20, 20), False, "dinh sat canh (collinear)"),
        (rect(5, 20, 20, 20), rect(0, 0, 20, 20), False, "dinh sat lech (T tu ngoai)"),
        (rect(0, 10, 20, 20), rect(0, 0, 20, 20), True, "chong cung be rong (T vao trong)"),
        (rect(5, 10, 20, 20), rect(0, 0, 20, 20), True, "cat cheo"),
        (rect(20, 20, 5, 5), rect(0, 0, 20, 20), False, "cham goc"),
        ([(10, 0, 10, 30)], rect(0, 0, 20, 20), True, "doan xuyen qua"),
        ([(10, 20, 10, 30)], rect(0, 0, 20, 20), False, "T cham tu ngoai"),
        ([(10, 10, 10, 20)], rect(0, 0, 20, 20), True, "T tu trong"),
        ([(-5, 5, 25, 5)], [(0, 0, 0, 20)], True, "cat chu thap"),
        ([(0, 5, 10, 5)], [(0, 0, 0, 20)], False, "T voi doan ho (khong co mien trong)"),
        ([(0, 0, 10, 0)], [(10, 0, 20, 0)], False, "noi tiep thang hang"),
        ([(0, 0, 10, 0)], [(5, 0, 20, 0)], False, "chong thang hang"),
        ([(0, 0, 10, 0)], [(0, 1, 10, 1)], False, "song song"),
    ]
    bad = 0
    for a, b, exp, name in cases:
        got = coll(a, b)
        print(("OK  " if got == exp else "FAIL"), use_np, name, got)
        bad += got != exp
    assert classify((0, 0, 10, 0), (5, -1, 5, 1)) == "cross"
    assert classify((0, 0, 10, 0), (10, 0, 10, 5)) == "none"
    assert classify((5, 0, 5, 5), (0, 0, 10, 0)) == "a_end"
    return bad

if __name__ == "__main__":
    n = run(True) + run(False)
    print("failures:", n)
    raise SystemExit(n)
