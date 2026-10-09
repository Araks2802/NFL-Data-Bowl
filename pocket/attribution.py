"""Player-level attribution: PPPR (offense), PCR (defense), and matchups.

Keeps three layers separate (Methodology section D):
  1. recorded individual outcomes (PFF-credited)
  2. tracking-derived observations (proximity, closing)
  3. estimated contributions to pocket integrity

Blocker<->rusher pairing uses pff_nflIdBlockedPlayer (handles double teams,
switches, chips). We never attribute pressure to the nearest defender.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import config as C
from .normalize import normalize_play
from .geometry import roles_from_pff


# ---------------------------------------------------------------------------
# Per-play, per-player contribution rows
# ---------------------------------------------------------------------------
def player_play_rows(play_track: pd.DataFrame, pff_play: pd.DataFrame,
                     pis_result, cfg: C.PISConfig = C.DEFAULT) -> list[dict]:
    """Build one row per participating blocker/rusher for a single scored play.

    play_track: raw tracking rows for the play. pis_result: PISResult (may be
    unscorable -> we still emit rows for exposure but mark pis NaN).
    """
    if pff_play.empty:
        return []
    pnorm = normalize_play(play_track)
    roles = roles_from_pff(pff_play)
    pis_val = getattr(pis_result, "pis", np.nan)
    scorable = getattr(pis_result, "scorable", False)

    rows: list[dict] = []
    gid = int(pff_play["gameId"].iloc[0])
    pid = int(pff_play["playId"].iloc[0])

    # --- min distance per rusher to QB over the window (tracking observation) ---
    rusher_min_dist, rusher_closing = _rusher_tracking(pnorm, roles)

    # --- blockers (offense) ---
    bl = pff_play[pff_play["pff_role"] == C.ROLE_BLOCK]
    for _, r in bl.iterrows():
        hit = _f(r["pff_hitAllowed"]); hur = _f(r["pff_hurryAllowed"])
        sk = _f(r["pff_sackAllowed"]); beat = _f(r["pff_beatenByDefender"])
        assigned = r["pff_nflIdBlockedPlayer"]
        uncertain = pd.isna(assigned)
        rows.append({
            "gameId": gid, "playId": pid, "nflId": int(r["nflId"]),
            "side": "offense", "role": C.ROLE_BLOCK,
            "position": r["pff_positionLinedUp"], "blockType": r.get("pff_blockType"),
            "assignedDefender": None if uncertain else int(assigned),
            "attribution_uncertain": bool(uncertain),
            # layer 1: recorded outcomes
            "hitAllowed": hit, "hurryAllowed": hur, "sackAllowed": sk,
            "beatenByDefender": beat,
            "pressureAllowed": float(hit or hur or sk),
            # layer 3: contribution to pocket
            "pis": pis_val, "scorable": scorable,
            "pppr_contrib": _pppr_contrib(pis_val, hit, hur, sk, beat, cfg)
                            if scorable else np.nan,
        })

    # chipping route-runners who were credited with a block outcome
    chip = pff_play[(pff_play["pff_role"] == C.ROLE_ROUTE)
                    & (pff_play["pff_hitAllowed"].notna())]
    for _, r in chip.iterrows():
        hit = _f(r["pff_hitAllowed"]); hur = _f(r["pff_hurryAllowed"])
        sk = _f(r["pff_sackAllowed"]); beat = _f(r["pff_beatenByDefender"])
        assigned = r["pff_nflIdBlockedPlayer"]
        rows.append({
            "gameId": gid, "playId": pid, "nflId": int(r["nflId"]),
            "side": "offense", "role": "Chip",
            "position": r["pff_positionLinedUp"], "blockType": r.get("pff_blockType"),
            "assignedDefender": None if pd.isna(assigned) else int(assigned),
            "attribution_uncertain": bool(pd.isna(assigned)),
            "hitAllowed": hit, "hurryAllowed": hur, "sackAllowed": sk,
            "beatenByDefender": beat, "pressureAllowed": float(hit or hur or sk),
            "pis": pis_val, "scorable": scorable,
            "pppr_contrib": _pppr_contrib(pis_val, hit, hur, sk, beat, cfg)
                            if scorable else np.nan,
        })

    # --- rushers (defense) ---
    ru = pff_play[pff_play["pff_role"] == C.ROLE_RUSH]
    for _, r in ru.iterrows():
        nid = int(r["nflId"])
        hit = _f(r["pff_hit"]); hur = _f(r["pff_hurry"]); sk = _f(r["pff_sack"])
        mind = rusher_min_dist.get(nid, np.nan)
        clos = rusher_closing.get(nid, np.nan)
        prox_impact = _proximity_impact(mind, clos, cfg)
        rows.append({
            "gameId": gid, "playId": pid, "nflId": nid,
            "side": "defense", "role": C.ROLE_RUSH,
            "position": r["pff_positionLinedUp"], "blockType": None,
            "assignedDefender": None, "attribution_uncertain": False,
            # layer 1
            "hit": hit, "hurry": hur, "sack": sk,
            "pressure": float(hit or hur or sk),
            # layer 2: tracking observations
            "min_dist_to_qb": mind, "max_closing": clos,
            "prox_impact": prox_impact,
            # layer 3
            "pis": pis_val, "scorable": scorable,
            "pcr_contrib": _pcr_contrib(pis_val, hit, hur, sk, prox_impact, cfg)
                           if scorable else np.nan,
        })

    return rows


def _rusher_tracking(pnorm: pd.DataFrame, roles) -> tuple[dict, dict]:
    """Min distance to QB and max closing speed per rusher over the full play."""
    qb = pnorm[pnorm["nflId"] == roles.qb_id][["frameId", "x", "y"]].rename(
        columns={"x": "qx", "y": "qy"})
    if qb.empty:
        return {}, {}
    min_dist, max_clos = {}, {}
    for nid in roles.rusher_ids:
        rr = pnorm[pnorm["nflId"] == nid][["frameId", "x", "y", "vx", "vy"]]
        if rr.empty:
            continue
        m = rr.merge(qb, on="frameId", how="inner")
        if m.empty:
            continue
        dx = m["qx"] - m["x"]; dy = m["qy"] - m["y"]
        dist = np.hypot(dx, dy)
        dsafe = dist.replace(0, 1e-6)
        closing = (m["vx"] * dx + m["vy"] * dy) / dsafe
        min_dist[nid] = float(dist.min())
        max_clos[nid] = float(max(closing.max(), 0.0))
    return min_dist, max_clos


def _f(v) -> float:
    return 0.0 if pd.isna(v) else float(v)


def _pppr_contrib(pis, hit, hur, sk, beat, cfg) -> float:
    return pis - cfg.k_hit * hit - cfg.k_hurry * hur - cfg.k_sack * sk - cfg.k_beat * beat


def _proximity_impact(min_dist, closing, cfg) -> float:
    """Tracking proximity impact in [0,1]: closer + faster closing => higher."""
    if np.isnan(min_dist):
        return 0.0
    prox = max(0.0, 1.0 - min_dist / (cfg.proximity_radius * 2))
    clos = 0.0 if np.isnan(closing) else min(1.0, max(0.0, closing) / cfg.c_max)
    return float(0.7 * prox + 0.3 * clos)


def _pcr_contrib(pis, hit, hur, sk, prox_impact, cfg) -> float:
    base = (100.0 - pis)
    return (base
            + cfg.m_hit * hit + cfg.m_hurry * hur + cfg.m_sack * sk
            + cfg.m_prox * prox_impact)


# ---------------------------------------------------------------------------
# Aggregation to player ratings
# ---------------------------------------------------------------------------
def aggregate_offense(player_play: pd.DataFrame, players: pd.DataFrame,
                      cfg: C.PISConfig = C.DEFAULT) -> pd.DataFrame:
    off = player_play[(player_play["side"] == "offense")
                      & (player_play["scorable"])].copy()
    if off.empty:
        return pd.DataFrame()
    g = off.groupby("nflId")
    agg = g.agg(
        snaps=("playId", "nunique"),
        rows=("playId", "size"),
        mean_contrib=("pppr_contrib", "mean"),
        avg_pis=("pis", "mean"),
        hits_allowed=("hitAllowed", "sum"),
        hurries_allowed=("hurryAllowed", "sum"),
        sacks_allowed=("sackAllowed", "sum"),
        beaten=("beatenByDefender", "sum"),
        pressures_allowed=("pressureAllowed", "sum"),
    ).reset_index()
    agg["pressure_rate_allowed"] = agg["pressures_allowed"] / agg["rows"]
    agg = _scale_rating(agg, "mean_contrib", "PPPR", cfg.min_snaps_offense)
    agg = agg.merge(players[["nflId", "displayName", "officialPosition"]],
                    on="nflId", how="left")
    sd = _bootstrap_sd(off, "pppr_contrib")
    agg["bootstrap_sd"] = agg["nflId"].map(sd)
    return agg.sort_values("PPPR", ascending=False).reset_index(drop=True)


def aggregate_defense(player_play: pd.DataFrame, players: pd.DataFrame,
                      cfg: C.PISConfig = C.DEFAULT) -> pd.DataFrame:
    def_ = player_play[(player_play["side"] == "defense")
                       & (player_play["scorable"])].copy()
    if def_.empty:
        return pd.DataFrame()
    g = def_.groupby("nflId")
    agg = g.agg(
        snaps=("playId", "nunique"),
        rows=("playId", "size"),
        mean_contrib=("pcr_contrib", "mean"),
        avg_pis_faced=("pis", "mean"),
        hits=("hit", "sum"), hurries=("hurry", "sum"), sacks=("sack", "sum"),
        pressures=("pressure", "sum"),
        avg_min_dist=("min_dist_to_qb", "mean"),
        avg_prox_impact=("prox_impact", "mean"),
    ).reset_index()
    agg["pressure_rate"] = agg["pressures"] / agg["rows"]
    agg = _scale_rating(agg, "mean_contrib", "PCR", cfg.min_snaps_defense)
    agg = agg.merge(players[["nflId", "displayName", "officialPosition"]],
                    on="nflId", how="left")
    sd = _bootstrap_sd(def_, "pcr_contrib")
    agg["bootstrap_sd"] = agg["nflId"].map(sd)
    return agg.sort_values("PCR", ascending=False).reset_index(drop=True)


def _scale_rating(agg: pd.DataFrame, contrib_col: str, out_col: str,
                  min_snaps: int) -> pd.DataFrame:
    agg["qualified"] = agg["snaps"] >= min_snaps
    q = agg[agg["qualified"]]
    if len(q) >= 2:
        lo = q[contrib_col].quantile(0.02)
        hi = q[contrib_col].quantile(0.98)
    else:
        lo, hi = agg[contrib_col].min(), agg[contrib_col].max()
    rng = hi - lo if hi > lo else 1.0
    agg[out_col] = (100.0 * (agg[contrib_col] - lo) / rng).clip(0, 100)
    return agg


def _bootstrap_sd(df: pd.DataFrame, col: str, n_boot: int = 300,
                  seed: int = 7) -> dict:
    """Per-player bootstrap SD of the mean contribution (uncertainty band).

    Returns {nflId: sd}. Used to map onto the aggregated table.
    """
    rng = np.random.default_rng(seed)
    out: dict[int, float] = {}
    for nid, g in df.groupby("nflId"):
        vals = g[col].dropna().to_numpy()
        if len(vals) < 2:
            out[int(nid)] = np.nan
            continue
        means = [rng.choice(vals, size=len(vals), replace=True).mean()
                 for _ in range(n_boot)]
        out[int(nid)] = float(np.std(means))
    return out


# ---------------------------------------------------------------------------
# Matchups: blocker vs rusher pairings from pff_nflIdBlockedPlayer
# ---------------------------------------------------------------------------
def matchup_rows(player_play: pd.DataFrame) -> pd.DataFrame:
    """One row per (blocker, assignedDefender) pairing with outcomes."""
    bl = player_play[(player_play["side"] == "offense")
                     & player_play["assignedDefender"].notna()].copy()
    if bl.empty:
        return pd.DataFrame()
    bl["assignedDefender"] = bl["assignedDefender"].astype("Int64")
    return bl[["gameId", "playId", "nflId", "assignedDefender", "position",
               "blockType", "hitAllowed", "hurryAllowed", "sackAllowed",
               "beatenByDefender", "pressureAllowed", "pis", "scorable",
               "attribution_uncertain"]].rename(
        columns={"nflId": "blocker_nflId", "assignedDefender": "defender_nflId"})
