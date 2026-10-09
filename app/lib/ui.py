"""Shared UI helpers: theme CSS, PIS badges, metric cards, navigation deep-links."""
from __future__ import annotations

import streamlit as st

CSS = """
<style>
  .stApp { background: #0b1220; }
  h1, h2, h3 { color: #f4f5f7; font-weight: 700; letter-spacing: -0.01em; }
  .pis-badge { display:inline-block; padding:6px 14px; border-radius:10px;
      font-weight:800; font-size:26px; color:#0b1220; }
  .metric-card { background:#111a2b; border:1px solid #1f2d44; border-radius:12px;
      padding:14px 16px; }
  .muted { color:#9aa7bd; font-size:13px; }
  .pill { background:#15223a; border:1px solid #22304a; border-radius:999px;
      padding:2px 10px; font-size:12px; color:#aebbd4; margin-right:4px; }
  [data-testid="stSidebar"] { background:#0e1626; }
</style>
"""


def inject_theme():
    st.markdown(CSS, unsafe_allow_html=True)


def pis_color(v: float) -> str:
    """Red -> amber -> green ramp for a 0-100 score."""
    if v is None or v != v:  # NaN
        return "#6b7280"
    if v >= 85:
        return "#2ecc71"
    if v >= 70:
        return "#9acd32"
    if v >= 55:
        return "#f4d35e"
    if v >= 40:
        return "#e8963a"
    return "#ef6f6c"


def pis_badge(v: float, label: str = "PIS"):
    c = pis_color(v)
    txt = "N/A" if (v is None or v != v) else f"{v:.0f}"
    st.markdown(
        f'<span class="muted">{label}</span><br>'
        f'<span class="pis-badge" style="background:{c}">{txt}</span>',
        unsafe_allow_html=True,
    )


def goto_play(game_id: int, play_id: int):
    """Store a target play and switch to the Play Explorer page."""
    st.session_state["target_game"] = int(game_id)
    st.session_state["target_play"] = int(play_id)
    try:
        st.switch_page("pages/1_Play_Explorer.py")
    except Exception:
        st.info("Open the Play Explorer page to view this play.")


def cache_warning():
    st.error(
        "No precomputed cache found. Build it first:\n\n"
        "`python scripts/build_cache.py`\n\n"
        "(use `--max-games 10` for a quick demo build)."
    )
