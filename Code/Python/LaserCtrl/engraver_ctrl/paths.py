import os

# Thu muc chua file nay (engraver_ctrl/), tinh theo vi tri file nguon
# nen khong phu thuoc thu muc dang chay (cwd)
ENGRAVER_CTRL_DIR = os.path.dirname(os.path.abspath(__file__))

# File gcode dung chung: cac tab generate (Designer, Parallel, Small
# parts) ghi vao day, tab Machine preview + Run GCODE va tab Simulate
# doc tu day. Dung os.path.join de chay duoc ca Windows/Linux.
CUT_PLAN_GCODE_PATH = os.path.join(ENGRAVER_CTRL_DIR, "cut_plan.gcode")
