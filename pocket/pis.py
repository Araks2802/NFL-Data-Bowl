"""Pocket Integrity Score (Methodology section C).

Aggregates per-frame geometry features over the eligible window into a single
0-100 score with an interpretable component breakdown, then applies a bounded
outcome adjustment.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict

import numpy as np
import pandas as pd

from . import config as C
from .events import Window


def _clamp01(a):
    return np.clip(a, 0.0, 1.0)


@dataclass
class PISResult:
    pis: float
    pis_geom: float
    outcome_adj: float
    s_clean: float
    s_press: float
    s_collapse: float
    s_closing: float
    s_final: float
    scorable: bool
    unscorable_reason: str | None
    n_frames_used: int
    frac_unusable: float
    peak_hull_area: float
    end_hull_area: float
    min_clean_dist: float
    time_to_pressure_s: float  # first time clean_dist < proximity_radius

    def as_dict(self) -> dict:
        return asdict(self)


def _per_frame_scores(feats: pd.DataFrame, cfg: C.PISConfig) -> pd.DataFrame:
    f = feats[feats["usable"]].copy()
    f["clean_space_score"] = _clamp01(f["clean_dist"] / cfg.d_clean)
    f["proximity_score"] = 1.0 - _clamp01(f["n_near"] / cfg.n_max)
    f["closing_score"] = 1.0 - _clamp01(f["closing"] / cfg.c_max)
    f["depth_score"] = _clamp01(f["depth_cushion"] / cfg.d_depth)
    return f


def score_play(feats: pd.DataFrame, window: Window, outcome: dict,
               cfg: C.PISConfig = C.DEFAULT) -> PISResult:
    """Compute PIS for one play from its per-frame features."""
    n_total = len(feats)
    usable = feats["usable"].sum() if n_total else 0
    frac_unusable = 1.0 - (usable / n_total) if n_total else 1.0

    # eligibility
    if n_total < cfg.min_window_frames:
        return _unscorable("window too short", n_total, frac_unusable)
    if frac_unusable > cfg.max_missing_frac:
        return _unscorable("too many unusable frames", int(usable), frac_unusable)

    f = _per_frame_scores(feats, cfg)
    if f.empty:
        return _unscorable("no usable frames", 0, 1.0)

    # time weighting is uniform (constant 10Hz), so plain means are time-weighted
    s_clean = float(f["clean_space_score"].mean())
    s_press = float(f["proximity_score"].mean())
    s_closing = float(f["closing_score"].mean())

    # collapse resistance: end area vs peak area (floored so expansion != reward)
    peak = float(f["hull_area"].max())
    end_area = float(f["hull_area"].iloc[-1])
    if peak > 1e-6:
        retained = _clamp01(end_area / peak)
    else:
        retained = 0.0
    # blend retained-area with sustained depth so a lineman drifting wide
    # (inflating then losing area) can't dominate; depth keeps QB protected deep.
    s_collapse = float(0.5 * retained + 0.5 * f["depth_score"].mean())

    # last-second integrity: mean cleanliness over final window
    n_final = max(1, int(round(cfg.final_window_s * C.TRACKING_HZ)))
    tail = f.tail(n_final)
    s_final = float((0.6 * tail["clean_space_score"] + 0.4 * tail["proximity_score"]).mean())

    pis_geom = 100.0 * (
        cfg.w_clean * s_clean
        + cfg.w_press * s_press
        + cfg.w_collapse * s_collapse
        + cfg.w_closing * s_closing
        + cfg.w_final * s_final
    )

    adj = 0.0
    if outcome.get("is_sack"):
        adj += cfg.adj_sack
    if outcome.get("any_hit"):
        adj += cfg.adj_hit
    if outcome.get("any_hurry"):
        adj += cfg.adj_hurry
    if outcome.get("is_scramble"):
        adj += cfg.adj_scramble
    if outcome.get("clean_throw"):
        adj += cfg.adj_clean

    pis = float(np.clip(pis_geom + adj, 0.0, 100.0))

    # diagnostics
    min_clean = float(f["clean_dist"].min())
    below = f[f["clean_dist"] < cfg.proximity_radius]
    if not below.empty:
        first_frame = int(below["frameId"].iloc[0])
        ttp = (first_frame - window.snap_frame) * C.DT
    else:
        ttp = float("nan")

    return PISResult(
        pis=pis, pis_geom=float(pis_geom), outcome_adj=float(adj),
        s_clean=s_clean, s_press=s_press, s_collapse=s_collapse,
        s_closing=s_closing, s_final=s_final,
        scorable=True, unscorable_reason=None,
        n_frames_used=int(usable), frac_unusable=float(frac_unusable),
        peak_hull_area=peak, end_hull_area=end_area,
        min_clean_dist=min_clean, time_to_pressure_s=float(ttp),
    )


def _unscorable(reason: str, n: int, frac: float) -> PISResult:
    return PISResult(
        pis=float("nan"), pis_geom=float("nan"), outcome_adj=0.0,
        s_clean=float("nan"), s_press=float("nan"), s_collapse=float("nan"),
        s_closing=float("nan"), s_final=float("nan"),
        scorable=False, unscorable_reason=reason,
        n_frames_used=int(n), frac_unusable=float(frac),
        peak_hull_area=float("nan"), end_hull_area=float("nan"),
        min_clean_dist=float("nan"), time_to_pressure_s=float("nan"),
    )
