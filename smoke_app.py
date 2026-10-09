"""Headless check that app data + field figure build without a running server."""
from __future__ import annotations

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# stub streamlit's cache decorators so app.lib.data imports without a server
import types
import streamlit as st

from pocket import pipeline, io
from pocket.normalize import normalize_play
from app.lib import field, glossary, ui  # noqa: F401 (import-time check)

# directly exercise the detail builder logic without st.cache
gid, pid = 2021092605, 1820  # the collapse->TD demo
track = io.load_tracking_game(gid)
pt = track[track.playId == pid]
pff = io.pff_for_game(gid)
pffp = pff[pff.playId == pid]
plays = io.plays_for_game(gid)
pr = plays[plays.playId == pid].passResult.iloc[0]
win, roles, res, frames = pipeline.score_single(pt, pffp, pr, want_frames=True)

from app.lib.data import _frame_pis_curve
detail = {
    "tracking": normalize_play(pt), "frames": frames, "window": win,
    "roles": roles, "pis": res, "pass_result": pr,
    "play_row": plays[plays.playId == pid].iloc[0].to_dict(),
    "pff_play": pffp, "pis_curve": _frame_pis_curve(frames),
}
name_map = dict(zip(io.load_players().nflId, io.load_players().displayName))

for layers in [
    {"pocket": True, "proximity": True},
    {"pocket": True, "clean_space": True, "proximity": True, "trails": True, "velocity": True},
]:
    fig = field.build_play_figure(detail, name_map, layers)
    print(f"figure built: {len(fig.data)} traces, {len(fig.frames)} frames, "
          f"layers={list(layers)}")

print("PIS", res.pis, "components",
      round(res.s_clean, 2), round(res.s_press, 2), round(res.s_collapse, 2))
print("curve rows", len(detail["pis_curve"]))
print("glossary keys ok:", bool(glossary.PIS and glossary.COMPONENTS))
print("ui.pis_color(90)=", ui.pis_color(90), "ui.pis_color(30)=", ui.pis_color(30))
print("SCRIPT_OK")
