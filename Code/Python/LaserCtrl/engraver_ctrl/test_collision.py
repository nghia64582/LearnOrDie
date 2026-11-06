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

def test_axis():
    blk = [(0, rect(5, 5, 10, 10))]
    c = Collider(blk, [], no_overlap=False, no_cross_x=True, no_cross_y=True)
    assert not c.collides(0, 0)
    assert not c.collides(0, -5)        # canh duoi nam tren Ox
    assert c.collides(0, -5.01)         # vat qua Ox
    assert not c.collides(-5, -5)       # goc tai O
    assert c.collides(-5.5, 0)          # vat qua Oy
    assert not c.collides(0, -15)       # nam han duoi Ox (khong vat)
    # resolve: keo xuong sau -> dung dung y = -5 (minY = 0)
    off, b = c.resolve((0, 0), (0, -9))
    assert b and off == (0, -5.0), off
    off, b = c.resolve((0, -5.0), (3, -9))   # truot doc Ox
    assert abs(off[0] - 3) < 1e-2 and off[1] == -5.0, off
    off, b = c.resolve((0, 0), (-9, -9))     # goc vao O
    assert off == (-5.0, -5.0), off
    c2 = Collider(blk, [], no_overlap=False)
    assert not c2.active and not c2.collides(0, -9)
    c3 = Collider(blk, [], no_overlap=False, no_cross_x=True)
    assert not c3.collides(-9, 0) and c3.collides(0, -9)
    print("axis tests OK")



if __name__ == "__main__":
    n = run(True) + run(False)
    print("failures:", n)
    test_axis()
    raise SystemExit(n)


