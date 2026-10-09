"""Cached data access for the Streamlit app.

All heavy tables are read from the precomputed Parquet cache. Per-play tracking
is loaded one game at a time and the per-frame geometry for the selected play
is computed on demand (fast, single play).
"""
from __future__ import annotations

import sys
from pathlib import Path

# make the `pocket` package importable when Streamlit runs from app/
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import json
import numpy as np
import pandas as pd
import streamlit as st

from pocket import config as C
from pocket import io, pipeline, geometry
from pocket.normalize import normalize_play


# ---------------------------------------------------------------------------
# Cached table loaders
# ---------------------------------------------------------------------------
@st.cache_data(show_spinner=False)
def cache_exists() -> bool:
    return C.PLAYS_PIS_PARQUET.exists() and C.PPPR_PARQUET.exists()


@st.cache_data(show_spinner=False)
def load_meta() -> dict:
    if C.META_JSON.exists():
        return json.loads(C.META_JSON.read_text())
    return {}


@st.cache_data(show_spinner=False)
def load_plays() -> pd.DataFrame:
    return pd.read_parquet(C.PLAYS_PIS_PARQUET)


@st.cache_data(show_spinner=False)
def load_player_play() -> pd.DataFrame:
    return pd.read_parquet(C.PLAYER_PLAY_PARQUET)


@st.cache_data(show_spinner=False)
def load_pppr() -> pd.DataFrame:
    return pd.read_parquet(C.PPPR_PARQUET)


@st.cache_data(show_spinner=False)
def load_pcr() -> pd.DataFrame:
    return pd.read_parquet(C.PCR_PARQUET)


@st.cache_data(show_spinner=False)
def load_matchups() -> pd.DataFrame:
    return pd.read_parquet(C.MATCHUPS_PARQUET)


@st.cache_data(show_spinner=False)
def load_players() -> pd.DataFrame:
    return io.load_players()


@st.cache_data(show_spinner=False)
def load_games() -> pd.DataFrame:
    return io.load_games()


@st.cache_data(show_spinner=False)
def player_name_map() -> dict:
    p = io.load_players()
    return dict(zip(p["nflId"], p["displayName"]))


# ---------------------------------------------------------------------------
# On-demand single-play tracking + geometry
# ---------------------------------------------------------------------------
@st.cache_data(show_spinner=False)
def load_game_tracking(game_id: int) -> pd.DataFrame:
    return io.load_tracking_game(int(game_id))


@st.cache_data(show_spinner=True)
def play_detail(game_id: int, play_id: int) -> dict:
    """Compute everything needed to render one play: normalised tracking,
    per-frame geometry, window, roles, PIS, and a per-frame PIS proxy curve.
    """
    track = load_game_tracking(game_id)
    ptrack = track[track["playId"] == int(play_id)]
    pff = io.pff_for_game(game_id)
    pff_play = pff[pff["playId"] == int(play_id)]
    plays = io.plays_for_game(game_id)
    prow = plays[plays["playId"] == int(play_id)]
    pass_result = prow["passResult"].iloc[0] if len(prow) else None

    win, roles, res, frames = pipeline.score_single(
        ptrack, pff_play, pass_result, want_frames=True
    )
    pnorm = normalize_play(ptrack)

    # per-frame PIS proxy for the live curve: blend the per-frame cleanliness
    # components with the same weights used in the play score.
    curve = _frame_pis_curve(frames)

    return {
        "tracking": pnorm,
        "frames": frames,
        "window": win,
        "roles": roles,
        "pis": res,
        "pass_result": pass_result,
        "play_row": prow.iloc[0].to_dict() if len(prow) else {},
        "pff_play": pff_play,
        "pis_curve": curve,
    }


def _frame_pis_curve(frames: pd.DataFrame, cfg: C.PISConfig = C.DEFAULT) -> pd.DataFrame:
    if frames is None or frames.empty:
        return pd.DataFrame(columns=["frameId", "pis_frame"])
    f = frames[frames["usable"]].copy()
    if f.empty:
        return pd.DataFrame(columns=["frameId", "pis_frame"])
    clean = np.clip(f["clean_dist"] / cfg.d_clean, 0, 1)
    prox = 1 - np.clip(f["n_near"] / cfg.n_max, 0, 1)
    clos = 1 - np.clip(f["closing"] / cfg.c_max, 0, 1)
    depth = np.clip(f["depth_cushion"] / cfg.d_depth, 0, 1)
    # instantaneous proxy (collapse/final are window-level; approximate with depth)
    frame_pis = 100 * (0.35 * clean + 0.25 * prox + 0.2 * clos + 0.2 * depth)
    out = pd.DataFrame({"frameId": f["frameId"], "pis_frame": frame_pis})
    return out.reset_index(drop=True)
