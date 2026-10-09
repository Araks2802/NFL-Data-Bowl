"""Play Explorer: animated field reconstruction with the live PIS pocket overlay."""
from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from app.lib import data, ui, glossary, field
from pocket import config as C

st.set_page_config(page_title="Play Explorer", page_icon="🎞️", layout="wide")
ui.inject_theme()
st.title("🎞️ Play Explorer")

if not data.cache_exists():
    ui.cache_warning()
    st.stop()

plays = data.load_plays()
games = data.load_games()
name_map = data.player_name_map()

# ---------------------------------------------------------------------------
# Selection (supports deep-link from other pages via session_state)
# ---------------------------------------------------------------------------
plays_g = plays.merge(games[["gameId", "week", "homeTeamAbbr", "visitorTeamAbbr"]],
                      on="gameId", how="left", suffixes=("", "_g"))

target_game = st.session_state.pop("target_game", None)
target_play = st.session_state.pop("target_play", None)

with st.sidebar:
    st.header("Select a play")
    weeks = sorted(plays_g["week"].dropna().unique().tolist())
    teams = sorted(plays_g["possessionTeam"].dropna().unique().tolist())

    f_week = st.selectbox("Week", ["All"] + weeks, index=0)
    f_team = st.selectbox("Offense team", ["All"] + teams, index=0)
    f_result = st.multiselect("Outcome", ["C", "I", "S", "R", "IN"], default=[])
    f_formation = st.selectbox(
        "Formation", ["All"] + sorted(plays_g["offenseFormation"].dropna().unique().tolist()))
    pis_rng = st.slider("PIS range", 0, 100, (0, 100))

    view = plays_g.copy()
    if f_week != "All":
        view = view[view.week == f_week]
    if f_team != "All":
        view = view[view.possessionTeam == f_team]
    if f_result:
        view = view[view.passResult.isin(f_result)]
    if f_formation != "All":
        view = view[view.offenseFormation == f_formation]
    view = view[view.scorable]
    view = view[(view.pis >= pis_rng[0]) & (view.pis <= pis_rng[1])]
    view = view.sort_values(["week", "gameId", "playId"])

    st.caption(f"{len(view):,} plays match")

    # choose a game then a play (keeps the dropdowns short)
    if target_game is not None:
        game_ids = [target_game]
    else:
        game_ids = view["gameId"].unique().tolist()
    if not game_ids:
        st.warning("No plays match these filters.")
        st.stop()

    def _game_label(g):
        row = games[games.gameId == g].iloc[0]
        return f"wk{int(row.week)} {row.visitorTeamAbbr}@{row.homeTeamAbbr} ({g})"

    gsel = st.selectbox("Game", game_ids, format_func=_game_label,
                        index=0)
    gplays = view[view.gameId == gsel] if target_game is None else \
        plays_g[(plays_g.gameId == gsel) & plays_g.scorable]
    gplays = gplays.sort_values("playId")

    def _play_label(pid):
        r = gplays[gplays.playId == pid].iloc[0]
        return f"#{pid} · {r.passResult} · PIS {r.pis:.0f}"

    play_ids = gplays["playId"].tolist()
    default_idx = play_ids.index(target_play) if (target_play in play_ids) else 0
    psel = st.selectbox("Play", play_ids, index=default_idx, format_func=_play_label)

    st.divider()
    st.subheader("Layers")
    layers = {
        "pocket": st.checkbox("Pocket shape", True),
        "clean_space": st.checkbox("QB clean-space ring", False),
        "proximity": st.checkbox("Pressure radius", True),
        "trails": st.checkbox("Player trails", False),
        "velocity": st.checkbox("Velocity arrows", False),
    }

# ---------------------------------------------------------------------------
# Load the play detail (on demand) and render
# ---------------------------------------------------------------------------
detail = data.play_detail(int(gsel), int(psel))
prow = detail["play_row"]
res = detail["pis"]

head = st.container()
with head:
    hc1, hc2 = st.columns([5, 1])
    with hc1:
        st.markdown(f"**{prow.get('playDescription','')}**")
        meta_bits = [
            f"Week {int(prow.get('week')) if pd.notna(prow.get('week')) else '?'}",
            f"{prow.get('possessionTeam','?')} vs {prow.get('defensiveTeam','?')}",
            f"{prow.get('offenseFormation','?')}",
            f"{prow.get('dropBackType','?')}",
            f"Cov: {prow.get('pff_passCoverage','?')}",
            f"PA: {'Yes' if prow.get('pff_playAction') else 'No'}",
            f"Result: {detail['pass_result']}",
        ]
        st.markdown('<span class="muted">' + "  ·  ".join(meta_bits) + "</span>",
                    unsafe_allow_html=True)
    with hc2:
        ui.pis_badge(res.pis if res.scorable else float("nan"))

fig_col, info_col = st.columns([3, 1], gap="medium")

with fig_col:
    if detail["frames"] is None or detail["frames"].empty:
        st.warning("This play could not be reconstructed from tracking.")
    else:
        fig = field.build_play_figure(detail, name_map, layers)
        st.plotly_chart(fig, use_container_width=True,
                        config={"displayModeBar": False})
    st.caption("Gold = pass blockers · Red = pass rushers · White = QB · "
               "Grey = routes/coverage · Brown diamond = ball. Press **Play**, "
               "or drag the timeline. Markers flag the snap and the play's end.")

with info_col:
    st.markdown("**PIS components**")
    if res.scorable:
        comp = {
            "Clean-space (30%)": res.s_clean,
            "Pressure load (20%)": res.s_press,
            "Collapse resist (20%)": res.s_collapse,
            "Closing control (15%)": res.s_closing,
            "Last-second (15%)": res.s_final,
        }
        cdf = pd.DataFrame({"component": list(comp.keys()),
                            "score": [v * 100 for v in comp.values()]})
        bar = go.Figure(go.Bar(
            x=cdf["score"], y=cdf["component"], orientation="h",
            marker_color=[ui.pis_color(v) for v in cdf["score"]],
            text=[f"{v:.0f}" for v in cdf["score"]], textposition="auto"))
        bar.update_layout(
            height=230, margin=dict(l=4, r=4, t=4, b=4),
            paper_bgcolor="#0b1220", plot_bgcolor="#0b1220",
            font=dict(color="#e5e7eb", size=11),
            xaxis=dict(range=[0, 100], showgrid=False),
            yaxis=dict(autorange="reversed"))
        st.plotly_chart(bar, use_container_width=True, config={"displayModeBar": False})
        st.markdown(
            f'<span class="muted">Geometry {res.pis_geom:.0f} '
            f'{"+" if res.outcome_adj>=0 else ""}{res.outcome_adj:.0f} outcome '
            f'= <b>{res.pis:.0f}</b></span>', unsafe_allow_html=True)
        st.markdown(
            f'<span class="muted">Min QB space: {res.min_clean_dist:.1f} yd · '
            f'time to pressure: '
            f'{"n/a" if np.isnan(res.time_to_pressure_s) else f"{res.time_to_pressure_s:.1f} s"}'
            f'</span>', unsafe_allow_html=True)
    else:
        st.info(f"Unscorable: {res.unscorable_reason}")

    with st.expander("What is PIS?"):
        st.caption(glossary.PIS)

# ---------------------------------------------------------------------------
# PIS / clean-space timeline
# ---------------------------------------------------------------------------
st.subheader("Pocket integrity over the play")
frames = detail["frames"]
curve = detail["pis_curve"]
if frames is not None and not frames.empty and not curve.empty:
    win = detail["window"]
    f = frames[frames.usable].merge(curve, on="frameId", how="left")
    t = (f["frameId"] - win.snap_frame) * C.DT
    tl = go.Figure()
    tl.add_trace(go.Scatter(x=t, y=f["pis_frame"], mode="lines",
                            line=dict(color="#5dade2", width=3), name="PIS (frame)"))
    tl.add_trace(go.Scatter(x=t, y=f["clean_dist"] / C.DEFAULT.d_clean * 100,
                            mode="lines", line=dict(color="#f4d35e", width=1.5, dash="dot"),
                            name="QB clean space (scaled)"))
    # event markers
    for fid, lbl, col in [(win.snap_frame, "snap", "#2ecc71"),
                          (win.end_frame, win.end_kind, "#ef6f6c")]:
        tt = (fid - win.snap_frame) * C.DT
        tl.add_vline(x=tt, line=dict(color=col, width=1, dash="dash"))
        tl.add_annotation(x=tt, y=100, text=lbl, showarrow=False,
                          font=dict(color=col, size=11), yshift=8)
    tl.update_layout(
        height=240, margin=dict(l=6, r=6, t=20, b=6),
        paper_bgcolor="#0b1220", plot_bgcolor="#0b1220",
        font=dict(color="#e5e7eb"),
        xaxis=dict(title="seconds from snap", showgrid=False),
        yaxis=dict(title="score / scaled", range=[0, 110], showgrid=True,
                   gridcolor="#1f2d44"),
        legend=dict(orientation="h", y=1.15))
    st.plotly_chart(tl, use_container_width=True, config={"displayModeBar": False})
    st.caption("The blue line is a per-frame PIS proxy; the dotted gold line is "
               "the QB's space from the nearest rusher. Watch them fall as a "
               "pocket collapses.")

# per-blocker / per-rusher outcomes on this play
with st.expander("Player outcomes on this play (PFF-credited)"):
    pff_play = detail["pff_play"]
    show = pff_play[["nflId", "pff_role", "pff_positionLinedUp", "pff_hitAllowed",
                     "pff_hurryAllowed", "pff_sackAllowed", "pff_hit", "pff_hurry",
                     "pff_sack", "pff_nflIdBlockedPlayer", "pff_blockType"]].copy()
    show["player"] = show["nflId"].map(name_map)
    show["blocked"] = show["pff_nflIdBlockedPlayer"].map(
        lambda v: name_map.get(int(v)) if pd.notna(v) else "")
    cols = ["player", "pff_role", "pff_positionLinedUp", "blocked", "pff_blockType",
            "pff_hitAllowed", "pff_hurryAllowed", "pff_sackAllowed",
            "pff_hit", "pff_hurry", "pff_sack"]
    st.dataframe(show[cols], use_container_width=True, hide_index=True)
