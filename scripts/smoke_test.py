"""Smoke-test the PIS engine on one game: bounds, scorable rate, outcome sanity."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd

from pocket import pipeline, io

GID = io.available_game_ids()[0]
print(f"Scoring game {GID} ...")
plays, frames = pipeline.score_game(GID, want_frames=True)
print(f"\nplays scored: {len(plays)}  frames rows: {0 if frames is None else len(frames)}")

print("\n--- bounds / scorable ---")
print("scorable:", plays["scorable"].sum(), "/", len(plays))
sc = plays[plays["scorable"]]
print("PIS min/mean/max:", round(sc.pis.min(), 1), round(sc.pis.mean(), 1), round(sc.pis.max(), 1))
assert sc.pis.between(0, 100).all(), "PIS out of bounds!"
for comp in ["s_clean", "s_press", "s_collapse", "s_closing", "s_final"]:
    assert sc[comp].between(0, 1).all(), f"{comp} out of [0,1]"
print("all components in [0,1]  OK")
print("unscorable reasons:", plays[~plays.scorable].unscorable_reason.value_counts().to_dict())

print("\n--- mean PIS by passResult (expect S < C) ---")
print(sc.groupby("passResult").pis.agg(["count", "mean"]).round(1))

print("\n--- mean PIS by hurry/hit (expect lower when pressured) ---")
# recompute outcome flags via columns we stored? we stored outcome_adj only.
print(sc.groupby(sc.outcome_adj < 0).pis.agg(["count", "mean"]).round(1))

print("\n--- end_kind distribution ---")
print(plays.end_kind.value_counts().to_dict())
print("snap_approx:", int(plays.snap_approx.sum()), " end_approx:", int(plays.end_approx.sum()))

print("\n--- 5 cleanest and 5 messiest scorable plays ---")
cols = ["playId", "passResult", "pis", "pis_geom", "outcome_adj", "min_clean_dist", "end_kind"]
print("CLEANEST:\n", sc.nlargest(5, "pis")[cols].to_string(index=False))
print("MESSIEST:\n", sc.nsmallest(5, "pis")[cols].to_string(index=False))
