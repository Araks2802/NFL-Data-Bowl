"""Player Leaderboards: PPPR (offense) and PCR (defense) with filters and links."""
from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import numpy as np
import pandas as pd
import streamlit as st

from app.lib import data, ui, glossary
from pocket import attribution, config as C

st.set_page_config(page_title="Leaderboards", page_icon="📊", layout="wide")
ui.inject_theme()
st.title("📊 Player Leaderboards")


# ---------------------------------------------------------------------------
# Re-aggregation on filtered rows (so filters change the ratings)
# ---------------------------------------------------------------------------
@st.cache_data(show_spinner=False)
def _players_df():
    return data.load_players()


def _agg_offense(rows: pd.DataFrame, name_map: dict, min_snaps: int) -> pd.DataFrame:
    if rows.empty:
        return pd.DataFrame()
    cfg = C.PISConfig(min_snaps_offense=min_snaps)
    agg = attribution.aggregate_offense(rows, _players_df(), cfg)
    team = (rows.groupby("nflId")["possessionTeam"]
            .agg(lambda s: s.mode().iloc[0] if not s.mode().empty else None))
    agg["team"] = agg["nflId"].map(team)
    return agg


def _agg_defense(rows: pd.DataFrame, name_map: dict, min_snaps: int) -> pd.DataFrame:
    if rows.empty:
        return pd.DataFrame()
    cfg = C.PISConfig(min_snaps_defense=min_snaps)
    agg = attribution.aggregate_defense(rows, _players_df(), cfg)
    team = (rows.groupby("nflId")["defensiveTeam"]
            .agg(lambda s: s.mode().iloc[0] if not s.mode().empty else None))
    agg["team"] = agg["nflId"].map(team)
    return agg


def _example_play_for(nflId: int, side: str) -> tuple[int, int] | None:
    """A representative play for this player (best/worst PIS) to deep-link to."""
    rows = pp[(pp.nflId == nflId) & (pp.side == side) & pp.scorable]
    if rows.empty:
        return None
    r = rows.sort_values("pis", ascending=(side == "defense")).iloc[0]
    return int(r.gameId), int(r.playId)


def _leaderboard_table(agg: pd.DataFrame, side: str):
    if agg.empty:
        st.info("No players match these filters at the chosen snap threshold.")
        return
    rating = "PPPR" if side == "offense" else "PCR"
    if side == "offense":
        cols = ["displayName", "officialPosition", "team", "snaps", rating,
                "avg_pis", "pressures_allowed", "hits_allowed", "hurries_allowed",
                "sacks_allowed", "beaten", "pressure_rate_allowed", "bootstrap_sd"]
        rename = {"displayName": "Player", "officialPosition": "Pos",
                  "team": "Tm", "snaps": "Snaps", "avg_pis": "Avg PIS",
                  "pressures_allowed": "Press", "hits_allowed": "Hits",
                  "hurries_allowed": "Hur", "sacks_allowed": "Sacks",
                  "beaten": "Beaten", "pressure_rate_allowed": "Press%",
                  "bootstrap_sd": "±"}
    else:
        cols = ["displayName", "officialPosition", "team", "snaps", rating,
                "pressures", "hits", "hurries", "sacks", "pressure_rate",
                "avg_prox_impact", "avg_min_dist", "bootstrap_sd"]
        rename = {"displayName": "Player", "officialPosition": "Pos",
                  "team": "Tm", "snaps": "Snaps", "pressures": "Press",
                  "hits": "Hits", "hurries": "Hur", "sacks": "Sacks",
                  "pressure_rate": "Press%", "avg_prox_impact": "ProxImpact",
                  "avg_min_dist": "MinDist", "bootstrap_sd": "±"}

    disp = agg[cols].copy().rename(columns=rename)
    disp = disp.round({rating: 1, "Avg PIS": 1} if side == "offense" else {rating: 1})
    for c in ("Press%",):
        if c in disp:
            disp[c] = (disp[c] * 100).round(1)
    for c in ("ProxImpact", "MinDist", "±"):
        if c in disp:
            disp[c] = disp[c].round(2)

    st.dataframe(
        disp, use_container_width=True, hide_index=True, height=460,
        column_config={rating: st.column_config.ProgressColumn(
            rating, min_value=0, max_value=100, format="%.0f")},
    )

    st.markdown("**Open a player's representative play**")
    top = agg.head(12)
    cols_btn = st.columns(4)
    for i, (_, r) in enumerate(top.iterrows()):
        tgt = _example_play_for(int(r.nflId), side)
        label = f"{r.displayName} ({r[rating]:.0f})"
        with cols_btn[i % 4]:
            if st.button(label, key=f"{side}_{int(r.nflId)}", use_container_width=True):
                if tgt:
                    ui.goto_play(*tgt)

if not data.cache_exists():
    ui.cache_warning()
    st.stop()

plays = data.load_plays()
pp = data.load_player_play()
name_map = data.player_name_map()
games = data.load_games()


def filtered_player_play(side: str) -> pd.DataFrame:
    """Apply context filters to player-play rows, then re-aggregate."""
    rows = pp[(pp.side == side) & pp.scorable].copy()
    ctx = plays.merge(games[["gameId", "week"]], on="gameId", how="left",
                      suffixes=("", "_g"))
    keep = ["gameId", "playId", "week", "offenseFormation", "pff_passCoverage",
            "dropBackType", "pff_playAction", "down", "defensiveTeam",
            "possessionTeam"]
    rows = rows.merge(ctx[keep], on=["gameId", "playId"], how="left")
    return rows


tab_off, tab_def = st.tabs(["🛡️ Pass protectors (PPPR)", "💥 Pass rushers (PCR)"])

# ---------------------------------------------------------------------------
# Shared filter widget
# ---------------------------------------------------------------------------
def context_filters(df: pd.DataFrame, key: str, team_col: str):
    c = st.columns(6)
    weeks = sorted(df["week"].dropna().unique().tolist())
    forms = sorted(df["offenseFormation"].dropna().unique().tolist())
    covs = sorted(df["pff_passCoverage"].dropna().unique().tolist())
    drops = sorted(df["dropBackType"].dropna().unique().tolist())
    teams = sorted(df[team_col].dropna().unique().tolist())
    w = c[0].multiselect("Week", weeks, key=f"{key}_w")
    tm = c[1].multiselect("Team", teams, key=f"{key}_tm")
    fo = c[2].multiselect("Formation", forms, key=f"{key}_fo")
    co = c[3].multiselect("Coverage", covs, key=f"{key}_co")
    dr = c[4].multiselect("Dropback", drops, key=f"{key}_dr")
    pa = c[5].selectbox("Play action", ["Any", "Yes", "No"], key=f"{key}_pa")
    out = df
    if w:
        out = out[out.week.isin(w)]
    if tm:
        out = out[out[team_col].isin(tm)]
    if fo:
        out = out[out.offenseFormation.isin(fo)]
    if co:
        out = out[out.pff_passCoverage.isin(co)]
    if dr:
        out = out[out.dropBackType.isin(dr)]
    if pa == "Yes":
        out = out[out.pff_playAction == 1]
    elif pa == "No":
        out = out[out.pff_playAction == 0]
    return out


# ---------------------------------------------------------------------------
# OFFENSE
# ---------------------------------------------------------------------------
with tab_off:
    st.caption(glossary.PPPR)
    off = filtered_player_play("offense")
    sub = context_filters(off, "off", "possessionTeam")
    min_snaps = st.slider("Minimum snaps", 10, 300, 50, 10, key="off_ms")
    pos_opts = ["T", "G", "C", "TE", "RB", "FB"]
    pos_pick = st.multiselect("Position", pos_opts, default=[], key="off_pos")

    agg = _agg_offense(sub, name_map, min_snaps)
    if pos_pick:
        agg = agg[agg.officialPosition.isin(pos_pick)]
    agg = agg[agg.snaps >= min_snaps].sort_values("PPPR", ascending=False)

    st.markdown(f"**{len(agg)} qualified players**")
    _leaderboard_table(agg, side="offense")


# ---------------------------------------------------------------------------
# DEFENSE
# ---------------------------------------------------------------------------
with tab_def:
    st.caption(glossary.PCR)
    deff = filtered_player_play("defense")
    sub = context_filters(deff, "def", "defensiveTeam")
    min_snaps = st.slider("Minimum snaps", 10, 300, 50, 10, key="def_ms")
    pos_opts = ["DE", "DT", "NT", "OLB", "ILB", "MLB", "LB", "CB", "SS", "FS"]
    pos_pick = st.multiselect("Position", pos_opts, default=[], key="def_pos")

    agg = _agg_defense(sub, name_map, min_snaps)
    if pos_pick:
        agg = agg[agg.officialPosition.isin(pos_pick)]
    agg = agg[agg.snaps >= min_snaps].sort_values("PCR", ascending=False)

    st.markdown(f"**{len(agg)} qualified players**")
    _leaderboard_table(agg, side="defense")
