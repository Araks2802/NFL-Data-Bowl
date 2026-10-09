"""Verify the NGS 'dir' angle convention by comparing it to actual displacement.

NGS docs: o and dir are 'degrees', 0 = pointing toward the opponent's end zone
is NOT the convention; the accepted convention is 0 deg = facing the away/+y
direction increasing... we instead derive it empirically: for frames where a
player moves, compare dir to atan2 of actual (dx, dy) between consecutive frames.
"""
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

DATA = Path(__file__).resolve().parents[1] / "data"
t = pd.read_csv(DATA / "tracking" / "tracking_2021090900.csv", na_values=["NA"])
# pick a fast-moving player on one play
play = t[t.playId == 97].copy()
play = play[play.nflId.notna()]
# compute displacement per player
play = play.sort_values(["nflId", "frameId"])
play["dx"] = play.groupby("nflId")["x"].diff()
play["dy"] = play.groupby("nflId")["y"].diff()
play["disp"] = np.hypot(play.dx, play.dy)
fast = play[play.disp > 0.3].copy()
# empirical bearing: two candidate conventions
# A: dir measured clockwise from +y (0->+y, 90->+x): vx=sin, vy=cos
fast["predA_x"] = np.sin(np.deg2rad(fast.dir))
fast["predA_y"] = np.cos(np.deg2rad(fast.dir))
# B: dir measured counterclockwise from +x: vx=cos, vy=sin
fast["predB_x"] = np.cos(np.deg2rad(fast.dir))
fast["predB_y"] = np.sin(np.deg2rad(fast.dir))
# actual unit displacement
fast["ux"] = fast.dx / fast.disp
fast["uy"] = fast.dy / fast.disp
errA = (np.hypot(fast.predA_x - fast.ux, fast.predA_y - fast.uy)).mean()
errB = (np.hypot(fast.predB_x - fast.ux, fast.predB_y - fast.uy)).mean()
print(f"n fast samples: {len(fast)}")
print(f"convention A (0=+y, cw, vx=sin/vy=cos) mean unit error: {errA:.3f}")
print(f"convention B (0=+x, ccw, vx=cos/vy=sin) mean unit error: {errB:.3f}")
print("\nsample rows:")
print(fast[["dir", "ux", "uy", "predA_x", "predA_y"]].head(8).to_string(index=False))
