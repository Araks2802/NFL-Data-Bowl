"""Eligible observation window (Methodology section A).

For each play, resolve [snap_frame, end_frame] from the tracking `event`
column, with explicit approximation flags when manual events are missing.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from . import config as C


@dataclass
class Window:
    snap_frame: int
    end_frame: int
    end_kind: str           # 'pass' | 'sack' | 'scramble' | 'approx_last'
    snap_approx: bool
    end_approx: bool
    pass_result: str | None

    @property
    def n_frames(self) -> int:
        return self.end_frame - self.snap_frame + 1


def _event_frames(play_df: pd.DataFrame) -> dict[str, int]:
    """Map each event name -> earliest frame it occurs on this play."""
    ev = play_df[["frameId", "event"]].dropna()
    ev = ev[ev["event"].astype(str) != "None"]
    if ev.empty:
        return {}
    return ev.groupby("event")["frameId"].min().to_dict()


def resolve_window(play_df: pd.DataFrame, pass_result: str | None) -> Window:
    """Resolve the scoring window for one (already play-filtered) tracking frame.

    `play_df` must contain all rows (players + football) for a single play.
    """
    frames = _event_frames(play_df)
    fmin = int(play_df["frameId"].min())
    fmax = int(play_df["frameId"].max())

    # --- snap ---
    snap_approx = False
    snap = next((frames[e] for e in C.SNAP_EVENTS if e in frames), None)
    if snap is None:
        snap = fmin
        snap_approx = True

    # --- end: depends on pass result ---
    end_approx = False
    end_kind = "approx_last"
    end = None
    pr = (pass_result or "").upper()

    if pr == "S":  # sack
        end = next((frames[e] for e in C.SACK_EVENTS if e in frames), None)
        end_kind = "sack"
        if end is None:  # fall back to pass-ish or last frame
            end = next((frames[e] for e in C.PASS_EVENTS if e in frames), None)
            if end is None:
                end, end_kind, end_approx = fmax, "approx_last", True
            else:
                end_kind = "approx_last"
                end_approx = True
    elif pr == "R":  # scramble
        # earliest of run event or pass_forward (scramble that still threw)
        run_f = next((frames[e] for e in C.SCRAMBLE_EVENTS if e in frames), None)
        pass_f = next((frames[e] for e in C.PASS_EVENTS if e in frames), None)
        cands = [f for f in (run_f, pass_f) if f is not None]
        if cands:
            end = min(cands)
            end_kind = "scramble"
        else:
            end, end_kind, end_approx = fmax, "approx_last", True
    else:  # C, I, IN -> pass release
        end = next((frames[e] for e in C.PASS_EVENTS if e in frames), None)
        end_kind = "pass"
        if end is None:
            # maybe a sack event slipped in; otherwise last frame
            end = next((frames[e] for e in C.SACK_EVENTS if e in frames), None)
            if end is not None:
                end_kind = "sack"
            else:
                end, end_kind, end_approx = fmax, "approx_last", True

    # guard: end must be after snap
    if end <= snap:
        end = fmax
        end_approx = True
        if end <= snap:
            end = snap + 1

    return Window(
        snap_frame=int(snap),
        end_frame=int(end),
        end_kind=end_kind,
        snap_approx=snap_approx,
        end_approx=end_approx,
        pass_result=pass_result,
    )


def outcome_flags(pff_play: pd.DataFrame, pass_result: str | None) -> dict:
    """Play-level recorded outcome flags from PFF (defender-credited columns).

    A hit/hurry/sack occurred on the play if ANY defender was credited.
    """
    pr = (pass_result or "").upper()
    rush = pff_play[pff_play["pff_role"].isin([C.ROLE_RUSH, C.ROLE_COVER])]
    any_hit = float(np.nansum(rush["pff_hit"].to_numpy())) > 0
    any_hurry = float(np.nansum(rush["pff_hurry"].to_numpy())) > 0
    any_sack = float(np.nansum(rush["pff_sack"].to_numpy())) > 0 or pr == "S"
    return {
        "any_hit": bool(any_hit),
        "any_hurry": bool(any_hurry),
        "any_sack": bool(any_sack),
        "is_scramble": pr == "R",
        "is_sack": pr == "S",
        "clean_throw": pr in ("C", "I", "IN") and not (any_hit or any_hurry or any_sack),
    }
