"""Validation checks for the PIS pipeline.

Covers the brief's required test areas:
  - correct joins
  - play-direction normalization
  - pocket-area (convex hull) calculation
  - event detection (observation window)
  - metric bounds
  - missing-data handling

Run with:  pytest -q
Most tests use one real game so they exercise the actual data end to end.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np
import pandas as pd
import pytest

from pocket import config as C
from pocket import io, events, geometry, pis, pipeline, attribution
from pocket.normalize import normalize_tracking, normalize_play

GID = 2021090900  # first game, always present


# --------------------------------------------------------------------------- #
# Joins
# --------------------------------------------------------------------------- #
def test_join_keys_unique():
    plays = io.load_plays()
    assert plays[["gameId", "playId"]].duplicated().sum() == 0
    pff = io.load_pff()
    assert pff[["gameId", "playId", "nflId"]].duplicated().sum() == 0


def test_plays_enriched_join_adds_week():
    e = io.load_plays_enriched()
    assert "week" in e.columns
    assert e["week"].notna().all()


def test_one_qb_per_play():
    pff = io.pff_for_game(GID)
    qb = pff[pff.pff_role == C.ROLE_QB]
    counts = qb.groupby(["gameId", "playId"]).size()
    assert (counts == 1).all()


# --------------------------------------------------------------------------- #
# Direction normalization
# --------------------------------------------------------------------------- #
def test_normalization_flips_left_plays():
    df = io.load_tracking_game(GID)
    left = df[df.playDirection == "left"].head(200).copy()
    if left.empty:
        pytest.skip("no left plays in sample")
    out = normalize_tracking(left)
    # x should be mirrored around FIELD_LENGTH
    np.testing.assert_allclose(out["x"].to_numpy(),
                               C.FIELD_LENGTH - left["x"].to_numpy(), atol=1e-6)
    np.testing.assert_allclose(out["y"].to_numpy(),
                               C.FIELD_WIDTH - left["y"].to_numpy(), atol=1e-6)
    assert (out["playDirection_norm"] == "right").all()


def test_normalization_preserves_right_plays():
    df = io.load_tracking_game(GID)
    right = df[df.playDirection == "right"].head(200).copy()
    out = normalize_tracking(right)
    np.testing.assert_allclose(out["x"].to_numpy(), right["x"].to_numpy(), atol=1e-6)


def test_velocity_components_consistent_with_speed():
    df = io.load_tracking_game(GID)
    out = normalize_tracking(df[df.nflId > 0].head(500).copy())
    speed = np.hypot(out["vx"], out["vy"])
    np.testing.assert_allclose(speed.to_numpy(), out["s"].to_numpy(), atol=1e-6)


# --------------------------------------------------------------------------- #
# Pocket-area (convex hull)
# --------------------------------------------------------------------------- #
def test_convex_hull_area_of_unit_square():
    pts = np.array([[0, 0], [1, 0], [1, 1], [0, 1]], dtype=float)
    area, verts = geometry._poly_area(pts)
    assert area == pytest.approx(1.0, abs=1e-9)
    assert verts is not None and len(verts) == 4


def test_hull_area_degenerate_points():
    # fewer than 3 points -> zero area, no crash
    area, verts = geometry._poly_area(np.array([[0.0, 0.0], [1.0, 1.0]]))
    assert area == 0.0 and verts is None


def test_hull_area_collinear_points():
    pts = np.array([[0, 0], [1, 1], [2, 2]], dtype=float)
    area, _ = geometry._poly_area(pts)
    assert area == pytest.approx(0.0, abs=1e-9)


# --------------------------------------------------------------------------- #
# Event detection / observation window
# --------------------------------------------------------------------------- #
def test_window_order_and_kind():
    track = io.load_tracking_game(GID)
    pff = io.pff_for_game(GID)
    plays = io.plays_for_game(GID)
    for _, pr in plays.head(25).iterrows():
        pid = int(pr.playId)
        pt = track[track.playId == pid]
        if pt.empty:
            continue
        win = events.resolve_window(normalize_play(pt), pr.passResult)
        assert win.end_frame > win.snap_frame
        assert win.end_kind in {"pass", "sack", "scramble", "approx_last"}


def test_sack_window_uses_sack_event_when_present():
    track = io.load_tracking_game(GID)
    plays = io.plays_for_game(GID)
    sacks = plays[plays.passResult == "S"]
    if sacks.empty:
        pytest.skip("no sacks in game sample")
    pr = sacks.iloc[0]
    pt = track[track.playId == int(pr.playId)]
    win = events.resolve_window(normalize_play(pt), "S")
    assert win.end_kind in {"sack", "approx_last"}


# --------------------------------------------------------------------------- #
# Metric bounds
# --------------------------------------------------------------------------- #
def test_pis_bounds_and_components_on_game():
    plays_df, _ = pipeline.score_game(GID)
    sc = plays_df[plays_df.scorable]
    assert len(sc) > 0
    assert sc.pis.between(0, 100).all()
    for comp in ["s_clean", "s_press", "s_collapse", "s_closing", "s_final"]:
        assert sc[comp].between(0, 1).all()


def test_pis_orders_sack_below_completion():
    plays_df, _ = pipeline.score_game(GID)
    sc = plays_df[plays_df.scorable]
    by = sc.groupby("passResult").pis.mean()
    if "S" in by and "C" in by:
        assert by["S"] < by["C"]


def test_player_ratings_bounded():
    plays_df, pp, _ = pipeline.score_game_full(GID)
    players = io.load_players()
    cfg = C.PISConfig(min_snaps_offense=1, min_snaps_defense=1)
    off = attribution.aggregate_offense(pp, players, cfg)
    deff = attribution.aggregate_defense(pp, players, cfg)
    assert off.PPPR.between(0, 100).all()
    assert deff.PCR.between(0, 100).all()


# --------------------------------------------------------------------------- #
# Missing-data handling
# --------------------------------------------------------------------------- #
def test_unscorable_when_window_too_short():
    # craft a frames frame with too few rows -> unscorable, not a crash
    feats = pd.DataFrame({"usable": [True, True], "frameId": [1, 2],
                          "clean_dist": [3.0, 3.0], "n_near": [0, 0],
                          "closing": [0.0, 0.0], "depth_cushion": [3.0, 3.0],
                          "hull_area": [10.0, 10.0]})
    win = events.Window(1, 2, "pass", False, False, "C")
    res = pis.score_play(feats, win, {}, C.DEFAULT)
    assert res.scorable is False
    assert np.isnan(res.pis)


def test_no_qb_is_unscorable():
    # pff play with no QB row -> roles.qb_id < 0 -> unscorable, no crash
    track = io.load_tracking_game(GID)
    plays = io.plays_for_game(GID)
    pid = int(plays.iloc[0].playId)
    pt = track[track.playId == pid]
    pff = io.pff_for_game(GID)
    pff_play = pff[pff.playId == pid]
    pff_no_qb = pff_play[pff_play.pff_role != C.ROLE_QB]
    win, roles, res, _ = pipeline.score_single(pt, pff_no_qb, "C")
    assert res.scorable is False


def test_football_rows_flagged():
    df = io.load_tracking_game(GID)
    assert df["is_football"].sum() > 0
    assert (df.loc[df.is_football, "nflId"] == -1).all()


def test_attribution_uncertain_flag_present():
    _, pp, _ = pipeline.score_game_full(GID)
    off = pp[pp.side == "offense"]
    assert "attribution_uncertain" in off.columns
    # most assignments should be known; some may be uncertain
    assert off.attribution_uncertain.mean() < 0.2
