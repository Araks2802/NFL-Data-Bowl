"""Orchestration: compute PIS (and optionally per-frame geometry) for plays.

Public entry points:
  score_game(game_id)            -> (plays_pis_df, frames_df)
  score_play(game_id, play_id)   -> dict with window, features, PISResult
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import config as C
from . import io, events, geometry, pis, attribution
from .normalize import normalize_play


def _play_tracking(track_game: pd.DataFrame, play_id: int) -> pd.DataFrame:
    return track_game[track_game["playId"] == int(play_id)]


def score_single(play_track: pd.DataFrame, pff_play: pd.DataFrame,
                 pass_result: str | None, cfg: C.PISConfig = C.DEFAULT,
                 want_frames: bool = False):
    """Score one play. play_track must be raw (un-normalised) tracking rows."""
    pnorm = normalize_play(play_track)
    win = events.resolve_window(pnorm, pass_result)
    roles = geometry.roles_from_pff(pff_play)
    if roles.qb_id < 0:
        res = pis._unscorable("no QB identified", 0, 1.0)
        feats = pd.DataFrame()
    else:
        feats = geometry.per_frame_features(pnorm, roles, win.snap_frame,
                                            win.end_frame, cfg)
        out = events.outcome_flags(pff_play, pass_result)
        res = pis.score_play(feats, win, out, cfg)
    frames = feats if want_frames else None
    return win, roles, res, frames


def score_game(game_id: int, cfg: C.PISConfig = C.DEFAULT,
               want_frames: bool = False):
    """Score every pass play in one game.

    Returns (plays_pis_df, frames_df_or_None).
    """
    track = io.load_tracking_game(game_id)
    pff = io.pff_for_game(game_id)
    plays = io.plays_for_game(game_id)

    play_rows = []
    frame_chunks = []
    for _, prow in plays.iterrows():
        pid = int(prow["playId"])
        ptrack = _play_tracking(track, pid)
        if ptrack.empty:
            continue
        pff_play = pff[pff["playId"] == pid]
        if pff_play.empty:
            continue
        pr = prow.get("passResult")
        win, roles, res, frames = score_single(
            ptrack, pff_play, pr, cfg, want_frames=want_frames
        )
        rec = {
            "gameId": int(game_id), "playId": pid,
            "week": prow.get("week"),
            "possessionTeam": prow.get("possessionTeam"),
            "defensiveTeam": prow.get("defensiveTeam"),
            "passResult": pr,
            "offenseFormation": prow.get("offenseFormation"),
            "dropBackType": prow.get("dropBackType"),
            "pff_passCoverage": prow.get("pff_passCoverage"),
            "pff_passCoverageType": prow.get("pff_passCoverageType"),
            "pff_playAction": prow.get("pff_playAction"),
            "down": prow.get("down"), "yardsToGo": prow.get("yardsToGo"),
            "qb_nflId": roles.qb_id,
            "snap_frame": win.snap_frame, "end_frame": win.end_frame,
            "end_kind": win.end_kind,
            "snap_approx": win.snap_approx, "end_approx": win.end_approx,
            "n_blockers": len(roles.blocker_ids),
            "n_rushers": len(roles.rusher_ids),
            "playDescription": prow.get("playDescription"),
        }
        rec.update(res.as_dict())
        play_rows.append(rec)

        if want_frames and frames is not None and not frames.empty:
            fc = frames.copy()
            fc["gameId"] = int(game_id)
            fc["playId"] = pid
            frame_chunks.append(fc)

    plays_df = pd.DataFrame(play_rows)
    frames_df = (pd.concat(frame_chunks, ignore_index=True)
                 if frame_chunks else None)
    return plays_df, frames_df


def score_game_full(game_id: int, cfg: C.PISConfig = C.DEFAULT,
                    want_frames: bool = False):
    """Score a game AND emit per-player-per-play contribution rows.

    Returns (plays_pis_df, player_play_df, frames_df_or_None).
    """
    track = io.load_tracking_game(game_id)
    pff = io.pff_for_game(game_id)
    plays = io.plays_for_game(game_id)

    play_rows: list[dict] = []
    pp_rows: list[dict] = []
    frame_chunks = []

    for _, prow in plays.iterrows():
        pid = int(prow["playId"])
        ptrack = _play_tracking(track, pid)
        if ptrack.empty:
            continue
        pff_play = pff[pff["playId"] == pid]
        if pff_play.empty:
            continue
        pr = prow.get("passResult")
        win, roles, res, frames = score_single(
            ptrack, pff_play, pr, cfg, want_frames=want_frames
        )
        rec = {
            "gameId": int(game_id), "playId": pid, "week": prow.get("week"),
            "possessionTeam": prow.get("possessionTeam"),
            "defensiveTeam": prow.get("defensiveTeam"),
            "passResult": pr, "offenseFormation": prow.get("offenseFormation"),
            "dropBackType": prow.get("dropBackType"),
            "pff_passCoverage": prow.get("pff_passCoverage"),
            "pff_passCoverageType": prow.get("pff_passCoverageType"),
            "pff_playAction": prow.get("pff_playAction"),
            "down": prow.get("down"), "yardsToGo": prow.get("yardsToGo"),
            "qb_nflId": roles.qb_id,
            "snap_frame": win.snap_frame, "end_frame": win.end_frame,
            "end_kind": win.end_kind, "snap_approx": win.snap_approx,
            "end_approx": win.end_approx, "n_blockers": len(roles.blocker_ids),
            "n_rushers": len(roles.rusher_ids),
            "playDescription": prow.get("playDescription"),
        }
        rec.update(res.as_dict())
        play_rows.append(rec)
        pp_rows.extend(attribution.player_play_rows(ptrack, pff_play, res, cfg))

        if want_frames and frames is not None and not frames.empty:
            fc = frames.copy()
            fc["gameId"] = int(game_id)
            fc["playId"] = pid
            frame_chunks.append(fc)

    plays_df = pd.DataFrame(play_rows)
    pp_df = pd.DataFrame(pp_rows)
    frames_df = (pd.concat(frame_chunks, ignore_index=True)
                 if frame_chunks else None)
    return plays_df, pp_df, frames_df
