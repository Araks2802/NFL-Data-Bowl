"""Data ingestion: load, clean, and join the raw CSV tables.

Join keys (verified):
  games    : gameId
  plays    : gameId, playId
  players  : nflId
  pff      : gameId, playId, nflId
  tracking : gameId, playId, nflId  (nflId NA => football)
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

from . import config as C

NA = ["NA"]


# ---------------------------------------------------------------------------
# Flat (small) tables — cached in-process
# ---------------------------------------------------------------------------
@lru_cache(maxsize=1)
def load_games() -> pd.DataFrame:
    g = pd.read_csv(C.GAMES_CSV, na_values=NA)
    g["gameId"] = g["gameId"].astype("int64")
    return g


@lru_cache(maxsize=1)
def load_players() -> pd.DataFrame:
    p = pd.read_csv(C.PLAYERS_CSV, na_values=NA)
    p["nflId"] = p["nflId"].astype("int64")
    p["displayName"] = p["displayName"].fillna("Unknown")
    # parse height "6-4" -> inches for optional use
    def _h(v):
        try:
            ft, inch = str(v).split("-")
            return int(ft) * 12 + int(inch)
        except Exception:
            return np.nan
    p["height_in"] = p["height"].map(_h)
    return p


@lru_cache(maxsize=1)
def load_plays() -> pd.DataFrame:
    pl = pd.read_csv(C.PLAYS_CSV, na_values=NA)
    pl["gameId"] = pl["gameId"].astype("int64")
    pl["playId"] = pl["playId"].astype("int64")
    # drop exact dup rows if any
    pl = pl.drop_duplicates(subset=["gameId", "playId"]).reset_index(drop=True)
    return pl


@lru_cache(maxsize=1)
def load_pff() -> pd.DataFrame:
    pff = pd.read_csv(C.PFF_CSV, na_values=NA)
    for c in ("gameId", "playId", "nflId"):
        pff[c] = pff[c].astype("int64")
    pff = pff.drop_duplicates(subset=["gameId", "playId", "nflId"]).reset_index(drop=True)
    return pff


@lru_cache(maxsize=1)
def load_plays_enriched() -> pd.DataFrame:
    """plays joined with game context (week, teams)."""
    plays = load_plays()
    games = load_games()[["gameId", "season", "week", "homeTeamAbbr", "visitorTeamAbbr", "gameDate"]]
    return plays.merge(games, on="gameId", how="left")


# ---------------------------------------------------------------------------
# Tracking (large) — load one game file at a time
# ---------------------------------------------------------------------------
def tracking_path(game_id: int) -> Path:
    return C.TRACKING_DIR / f"tracking_{game_id}.csv"


def available_game_ids() -> list[int]:
    ids = []
    for p in sorted(C.TRACKING_DIR.glob("tracking_*.csv")):
        try:
            ids.append(int(p.stem.split("_")[1]))
        except (IndexError, ValueError):
            continue
    return ids


def load_tracking_game(game_id: int) -> pd.DataFrame:
    """Load one game's tracking file with light cleaning.

    - nflId NA (football) kept but flagged is_football.
    - numeric coercion; drop impossible duplicate (playId, nflId, frameId) rows.
    """
    df = pd.read_csv(tracking_path(game_id), na_values=NA, low_memory=False)
    df["gameId"] = int(game_id)
    df["is_football"] = df["nflId"].isna()
    # football rows: assign a sentinel nflId of -1 for grouping stability
    df["nflId"] = df["nflId"].fillna(-1).astype("int64")
    df["playId"] = df["playId"].astype("int64")
    df["frameId"] = df["frameId"].astype("int64")
    for c in ("x", "y", "s", "a", "dis", "o", "dir"):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    # remove exact duplicate observations (same player/frame)
    df = df.drop_duplicates(subset=["playId", "nflId", "frameId"]).reset_index(drop=True)
    return df


def pff_for_game(game_id: int) -> pd.DataFrame:
    pff = load_pff()
    return pff[pff["gameId"] == int(game_id)].copy()


def plays_for_game(game_id: int) -> pd.DataFrame:
    pl = load_plays_enriched()
    return pl[pl["gameId"] == int(game_id)].copy()


def qb_ids_for_game(game_id: int) -> pd.DataFrame:
    """One QB nflId per play (pff_role == 'Pass')."""
    pff = pff_for_game(game_id)
    return pff[pff["pff_role"] == C.ROLE_QB][["gameId", "playId", "nflId"]].rename(
        columns={"nflId": "qb_nflId"}
    )
