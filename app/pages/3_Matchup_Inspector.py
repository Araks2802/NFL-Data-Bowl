"""Matchup Inspector: blocker-vs-rusher head-to-heads from PFF assignments."""
from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import numpy as np
import pandas as pd
import streamlit as st

from app.lib import data, ui

st.set_page_config(page_title="Matchup Inspector", page_icon="🥊", layout="wide")
ui.inject_theme()
st.title("🥊 Matchup Inspector")
st.caption("Head-to-head blocker vs pass-rusher results, built from PFF block "
           "assignments (which handle double teams, chips and stunts). Pocket "
           "integrity is the PIS on the plays where they met.")

if not data.cache_exists():
    ui.cache_warning()
    st.stop()

mu = data.load_matchups()
name_map = data.player_name_map()
players = data.load_players()
pos_map = dict(zip(players.nflId, players.officialPosition))
pp = data.load_player_play()

mu = mu.copy()
mu["blocker"] = mu["blocker_nflId"].map(name_map)
mu["defender"] = mu["defender_nflId"].map(name_map)
mu["blocker_pos"] = mu["blocker_nflId"].map(pos_map)
mu["defender_pos"] = mu["defender_nflId"].map(pos_map)


def _summarise(group_key: str, other_key: str, other_name: str, other_pos: str):
    g = mu.groupby([group_key, other_key]).agg(
        reps=("playId", "size"),
        pressures=("pressureAllowed", "sum"),
        hits=("hitAllowed", "sum"),
        hurries=("hurryAllowed", "sum"),
        sacks=("sackAllowed", "sum"),
        beaten=("beatenByDefender", "sum"),
        avg_pis=("pis", "mean"),
    ).reset_index()
    g["win_rate_def"] = (g["pressures"] / g["reps"]).round(3)
    g[other_name] = g[other_key].map(name_map)
    g[other_pos] = g[other_key].map(pos_map)
    return g


def _highlight(disp: pd.DataFrame, who_col: str, worst_label: str,
               min_reps: int = 3):
    """Call out the strongest/weakest matchups by win rate (min reps)."""
    win_col = "Def win%" if "Def win%" in disp else "Rush win%"
    cand = disp[disp["Reps"] >= min_reps]
    if cand.empty:
        return
    tough = cand.sort_values(win_col, ascending=False).head(3)
    easy = cand.sort_values(win_col, ascending=True).head(3)
    cc1, cc2 = st.columns(2)
    with cc1:
        st.markdown(f"**{worst_label}**")
        for _, r in tough.iterrows():
            st.markdown(f'<span class="muted">{r[who_col]} — {r[win_col]:.0f}% '
                        f'over {int(r["Reps"])} reps</span>', unsafe_allow_html=True)
    with cc2:
        st.markdown("**Best-controlled matchups (lowest win%)**")
        for _, r in easy.iterrows():
            st.markdown(f'<span class="muted">{r[who_col]} — {r[win_col]:.0f}% '
                        f'over {int(r["Reps"])} reps</span>', unsafe_allow_html=True)


mode = st.radio("Inspect", ["Offensive lineman vs the rushers he faced",
                            "Pass rusher vs the blockers he faced"],
                horizontal=True)

if mode.startswith("Offensive"):
    linemen = (mu.groupby("blocker_nflId").size().sort_values(ascending=False))
    options = linemen.index.tolist()
    sel = st.selectbox("Offensive blocker", options,
                       format_func=lambda n: f"{name_map.get(n,'?')} "
                       f"({pos_map.get(n,'?')}) · {int(linemen[n])} reps")
    g = _summarise("blocker_nflId", "defender_nflId", "defender", "defender_pos")
    g = g[g.blocker_nflId == sel].sort_values("reps", ascending=False)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Rushers faced", g.defender_nflId.nunique())
    c2.metric("Total reps", int(g.reps.sum()))
    c3.metric("Pressures allowed", int(g.pressures.sum()))
    c4.metric("Avg pocket PIS", f"{np.average(g.avg_pis, weights=g.reps):.0f}"
              if len(g) else "—")

    disp = g[["defender", "defender_pos", "reps", "pressures", "hits",
              "hurries", "sacks", "beaten", "win_rate_def", "avg_pis"]].copy()
    disp.columns = ["Defender", "Pos", "Reps", "Press", "Hits", "Hur",
                    "Sacks", "Beaten", "Def win%", "Avg PIS"]
    disp["Def win%"] = (disp["Def win%"] * 100).round(1)
    disp["Avg PIS"] = disp["Avg PIS"].round(1)
    st.dataframe(disp, use_container_width=True, hide_index=True)
    _highlight(disp, "Defender", worst_label="Toughest matchups (highest Def win%)")

else:
    rushers = (mu.groupby("defender_nflId").size().sort_values(ascending=False))
    options = rushers.index.tolist()
    sel = st.selectbox("Pass rusher", options,
                       format_func=lambda n: f"{name_map.get(n,'?')} "
                       f"({pos_map.get(n,'?')}) · {int(rushers[n])} reps")
    g = _summarise("defender_nflId", "blocker_nflId", "blocker", "blocker_pos")
    g = g[g.defender_nflId == sel].sort_values("reps", ascending=False)

    reps = int(g.reps.sum())
    press = int(g.pressures.sum())
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Blockers faced", g.blocker_nflId.nunique())
    c2.metric("Total reps", reps)
    c3.metric("Pressures created", press)
    c4.metric("Pressure rate", f"{press/reps*100:.0f}%" if reps else "—")

    disp = g[["blocker", "blocker_pos", "reps", "pressures", "hits",
              "hurries", "sacks", "beaten", "win_rate_def", "avg_pis"]].copy()
    disp.columns = ["Blocker", "Pos", "Reps", "Press", "Hits", "Hur",
                    "Sacks", "Beaten", "Rush win%", "Avg PIS"]
    disp["Rush win%"] = (disp["Rush win%"] * 100).round(1)
    disp["Avg PIS"] = disp["Avg PIS"].round(1)
    st.dataframe(disp, use_container_width=True, hide_index=True)
    _highlight(disp, "Blocker", worst_label="Blockers he beat most (highest Rush win%)")
