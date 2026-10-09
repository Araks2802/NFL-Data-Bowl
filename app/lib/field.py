"""Plotly football-field reconstruction and play animation.

Renders a normalised (left->right) field with animated players, the ball, the
pocket hull overlay, QB clean-space ring, defender proximity zones, player
trails, and velocity arrows. Returns a go.Figure with animation frames.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from pocket import config as C

# dark sports-analytics palette
FIELD_GREEN = "#0e2e1c"
FIELD_LINE = "#2f5d44"
ENDZONE = "#0a241533"
OFF_COLOR = "#f4d35e"   # offense = warm gold
DEF_COLOR = "#ef6f6c"   # defense = red
QB_COLOR = "#ffffff"
BALL_COLOR = "#8b4513"
HULL_FILL = "rgba(244,211,94,0.18)"
HULL_LINE = "rgba(244,211,94,0.8)"
CLEAN_RING = "rgba(93,173,226,0.5)"
PROX_ZONE = "rgba(239,111,108,0.12)"


def _field_shapes() -> list[dict]:
    shapes = []
    # grass
    shapes.append(dict(type="rect", x0=0, x1=C.FIELD_LENGTH, y0=0, y1=C.FIELD_WIDTH,
                       fillcolor=FIELD_GREEN, line=dict(width=0), layer="below"))
    # end zones
    for x0, x1 in [(0, 10), (110, 120)]:
        shapes.append(dict(type="rect", x0=x0, x1=x1, y0=0, y1=C.FIELD_WIDTH,
                           fillcolor="#09271a", line=dict(width=0), layer="below"))
    # yard lines every 5 yd
    for x in range(10, 111, 5):
        shapes.append(dict(type="line", x0=x, x1=x, y0=0, y1=C.FIELD_WIDTH,
                           line=dict(color=FIELD_LINE, width=1), layer="below"))
    # hash marks baseline
    for x in range(10, 111, 1):
        for yy in (0.5, C.FIELD_WIDTH - 0.5, 23.58, 29.75):
            shapes.append(dict(type="line", x0=x, x1=x, y0=yy - 0.15, y1=yy + 0.15,
                               line=dict(color=FIELD_LINE, width=1), layer="below"))
    return shapes


def _yard_numbers() -> go.Scatter:
    xs, txt = [], []
    labels = {20: "10", 30: "20", 40: "30", 50: "40", 60: "50",
              70: "40", 80: "30", 90: "20", 100: "10"}
    for x, lab in labels.items():
        xs.append(x)
        txt.append(lab)
    return go.Scatter(
        x=xs, y=[5] * len(xs), text=txt, mode="text",
        textfont=dict(color="#3f7a58", size=14), hoverinfo="skip", showlegend=False,
    )


def build_play_figure(detail: dict, name_map: dict,
                      layers: dict | None = None,
                      los_x: float | None = None) -> go.Figure:
    """Build the animated figure for one play.

    layers toggles: pocket, clean_space, proximity, trails, velocity.
    """
    layers = layers or {}
    track = detail["tracking"]
    frames_geo = detail["frames"]
    roles = detail["roles"]
    win = detail["window"]
    curve = detail["pis_curve"]

    frame_ids = sorted(track["frameId"].unique())
    # focus the view around the action (QB region) with margin
    qb = track[track["nflId"] == roles.qb_id]
    if not qb.empty:
        cx = qb["x"].mean()
    else:
        cx = track["x"].mean()
    x_lo, x_hi = max(0, cx - 20), min(C.FIELD_LENGTH, cx + 20)

    geo_by_frame = {int(r.frameId): r for r in frames_geo.itertuples()} if frames_geo is not None else {}
    curve_by_frame = dict(zip(curve["frameId"], curve["pis_frame"])) if not curve.empty else {}

    def frame_traces(fid: int) -> list[go.Scatter]:
        fr = track[track["frameId"] == fid]
        traces = []

        # --- pocket hull ---
        g = geo_by_frame.get(fid)
        if layers.get("pocket", True) and g is not None and getattr(g, "hull_vertices", None):
            hv = np.array(g.hull_vertices)
            if hv.shape[0] >= 3:
                hvc = np.vstack([hv, hv[0]])
                traces.append(go.Scatter(
                    x=hvc[:, 0], y=hvc[:, 1], mode="lines", fill="toself",
                    fillcolor=HULL_FILL, line=dict(color=HULL_LINE, width=2),
                    name="Pocket", hoverinfo="skip", showlegend=False))

        # --- QB clean-space ring + proximity zone ---
        if g is not None and getattr(g, "usable", False):
            qx, qy = g.qb_x, g.qb_y
            if layers.get("clean_space", False):
                traces.append(_circle(qx, qy, C.DEFAULT.d_clean, CLEAN_RING, "Clean space"))
            if layers.get("proximity", False):
                traces.append(_circle(qx, qy, C.DEFAULT.proximity_radius,
                                      "rgba(239,111,108,0.6)", "Pressure radius",
                                      fill=PROX_ZONE))

        # --- trails ---
        if layers.get("trails", False):
            hist = track[(track["frameId"] <= fid) & (track["frameId"] >= fid - 8)]
            for nid, grp in hist.groupby("nflId"):
                if nid == -1:
                    continue
                col = _player_color(nid, roles)
                traces.append(go.Scatter(
                    x=grp["x"], y=grp["y"], mode="lines",
                    line=dict(color=col, width=1), opacity=0.35,
                    hoverinfo="skip", showlegend=False))

        # --- players ---
        for side, ids, col, sym in [
            ("off", roles.blocker_ids, OFF_COLOR, "circle"),
            ("def", roles.rusher_ids, DEF_COLOR, "circle"),
        ]:
            sub = fr[fr["nflId"].isin(ids)]
            if sub.empty:
                continue
            traces.append(go.Scatter(
                x=sub["x"], y=sub["y"], mode="markers+text",
                marker=dict(color=col, size=16, line=dict(color="#111", width=1),
                            symbol=sym),
                text=sub["jerseyNumber"].fillna("").astype(str).str.replace(".0", "", regex=False),
                textfont=dict(color="#111", size=8),
                customdata=[[name_map.get(n, "?")] for n in sub["nflId"]],
                hovertemplate="%{customdata[0]}<extra></extra>",
                name="Blockers" if side == "off" else "Rushers", showlegend=False))
            if layers.get("velocity", False):
                for row in sub.itertuples():
                    traces.append(go.Scatter(
                        x=[row.x, row.x + row.vx * 0.4],
                        y=[row.y, row.y + row.vy * 0.4],
                        mode="lines", line=dict(color=col, width=1.5),
                        hoverinfo="skip", showlegend=False))

        # other offense (routes) + coverage, faded for context
        other = fr[~fr["nflId"].isin(roles.blocker_ids | roles.rusher_ids
                                     | {roles.qb_id, -1})]
        if not other.empty:
            traces.append(go.Scatter(
                x=other["x"], y=other["y"], mode="markers",
                marker=dict(color="#6b7280", size=10, line=dict(color="#111", width=1)),
                customdata=[[name_map.get(n, "?")] for n in other["nflId"]],
                hovertemplate="%{customdata[0]}<extra></extra>",
                hoverinfo="skip", showlegend=False))

        # QB
        qbf = fr[fr["nflId"] == roles.qb_id]
        if not qbf.empty:
            traces.append(go.Scatter(
                x=qbf["x"], y=qbf["y"], mode="markers+text",
                marker=dict(color=QB_COLOR, size=18, line=dict(color="#111", width=2),
                            symbol="circle"),
                text=["QB"], textfont=dict(color="#111", size=8),
                customdata=[[name_map.get(roles.qb_id, "QB")]],
                hovertemplate="%{customdata[0]} (QB)<extra></extra>", showlegend=False))

        # ball
        ball = fr[fr["nflId"] == -1]
        if not ball.empty:
            traces.append(go.Scatter(
                x=ball["x"], y=ball["y"], mode="markers",
                marker=dict(color=BALL_COLOR, size=9, symbol="diamond",
                            line=dict(color="#fff", width=1)),
                hoverinfo="skip", showlegend=False))
        return traces

    # initial frame
    f0 = frame_ids[0]
    fig = go.Figure(data=frame_traces(f0))

    # animation frames
    anim = []
    for fid in frame_ids:
        anim.append(go.Frame(data=frame_traces(fid), name=str(fid)))
    fig.frames = anim

    # event marker labels for the slider
    steps = []
    for fid in frame_ids:
        label = _frame_label(fid, win, geo_by_frame, curve_by_frame)
        steps.append(dict(method="animate",
                          args=[[str(fid)], dict(mode="immediate",
                                                 frame=dict(duration=0, redraw=True),
                                                 transition=dict(duration=0))],
                          label=label))

    fig.update_layout(
        shapes=_field_shapes(),
        xaxis=dict(range=[x_lo, x_hi], showgrid=False, zeroline=False,
                   visible=False, constrain="domain"),
        yaxis=dict(range=[0, C.FIELD_WIDTH], showgrid=False, zeroline=False,
                   visible=False, scaleanchor="x", scaleratio=1),
        plot_bgcolor=FIELD_GREEN, paper_bgcolor="#0b1220",
        font=dict(color="#e5e7eb"),
        margin=dict(l=10, r=10, t=10, b=10), height=430,
        showlegend=False,
        updatemenus=[dict(
            type="buttons", showactive=False, x=0.02, y=1.08, xanchor="left",
            bgcolor="#1f2937", font=dict(color="#e5e7eb"),
            buttons=[
                dict(label="Play", method="animate",
                     args=[None, dict(frame=dict(duration=90, redraw=True),
                                      fromcurrent=True, transition=dict(duration=0))]),
                dict(label="Pause", method="animate",
                     args=[[None], dict(frame=dict(duration=0, redraw=False),
                                        mode="immediate")]),
            ])],
        sliders=[dict(active=0, steps=steps, x=0.02, len=0.96,
                      currentvalue=dict(prefix="", font=dict(size=12)),
                      pad=dict(t=6))],
    )
    fig.add_trace(_yard_numbers())
    return fig


def _circle(cx, cy, r, color, name, fill=None):
    th = np.linspace(0, 2 * np.pi, 40)
    return go.Scatter(x=cx + r * np.cos(th), y=cy + r * np.sin(th), mode="lines",
                      line=dict(color=color, width=1, dash="dot"),
                      fill="toself" if fill else None, fillcolor=fill,
                      name=name, hoverinfo="skip", showlegend=False)


def _player_color(nid, roles):
    if nid in roles.blocker_ids:
        return OFF_COLOR
    if nid in roles.rusher_ids:
        return DEF_COLOR
    if nid == roles.qb_id:
        return QB_COLOR
    return "#6b7280"


def _frame_label(fid, win, geo_by_frame, curve_by_frame):
    tags = []
    if fid == win.snap_frame:
        tags.append("SNAP")
    if fid == win.end_frame:
        tags.append(win.end_kind.upper())
    t = (fid - win.snap_frame) * C.DT
    base = f"{t:+.1f}s"
    if fid in curve_by_frame:
        base += f"  PIS~{curve_by_frame[fid]:.0f}"
    if tags:
        base += "  [" + "/".join(tags) + "]"
    return base
