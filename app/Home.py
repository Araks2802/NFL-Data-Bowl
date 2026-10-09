"""Pocket Integrity Score — dashboard home / How-PIS-works."""
from __future__ import annotations

from pathlib import Path
import sys
import json

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st

from app.lib import data, ui, glossary
from pocket import config as C

st.set_page_config(page_title="Pocket Integrity Score", page_icon="🏈",
                   layout="wide", initial_sidebar_state="expanded")
ui.inject_theme()

st.title("🏈 Pocket Integrity Score")
st.markdown(
    "**Which offensive linemen and protection units build the cleanest, most "
    "sustainable pockets, and which defenders generate pressure most "
    "consistently, not just on splash plays?**"
)

if not data.cache_exists():
    ui.cache_warning()
    st.stop()

meta = data.load_meta()

# ---- top-line metrics ----
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Games", meta.get("n_games", "—"))
c2.metric("Pass plays scored", f"{meta.get('n_plays', 0):,}")
c3.metric("Scorable", f"{meta.get('scorable_frac', 0)*100:.0f}%")
c4.metric("Rated blockers (PPPR)", meta.get("n_pppr_qualified", "—"))
c5.metric("Rated rushers (PCR)", meta.get("n_pcr_qualified", "—"))

st.divider()

left, right = st.columns([3, 2], gap="large")

with left:
    st.subheader("The coaching / scouting problem")
    st.markdown(
        "Sacks are rare and noisy: only ~6% of dropbacks. A protection unit can "
        "surrender a quietly collapsing pocket on a play that still ends in a "
        "completion, and a clean pocket can end in a coverage sack. Grading "
        "protection on the box score alone misses most of the story.\n\n"
        "**Pocket Integrity Score (PIS)** measures the *continuous geometry and "
        "dynamics* of the pocket from snap to the throw or sack, so sustained "
        "clean pockets are rewarded and gradual collapses are penalised, even "
        "when the QB escapes or completes the pass."
    )

    st.subheader("How PIS works")
    st.markdown(
        "For every pass play we define a snap→release/sack window from the "
        "tracking events, then build a per-frame picture of the pocket from the "
        "QB and his pass blockers. PIS (0–100) is a weighted blend of five "
        "interpretable components, lightly calibrated by the recorded outcome:"
    )
    for name, desc in glossary.COMPONENTS.items():
        st.markdown(f"- **{name}** — {desc}")
    st.caption(glossary.OUTCOME_ADJ)

    with st.expander("The two player ratings"):
        st.markdown(f"**PPPR** — {glossary.PPPR}")
        st.markdown(f"**PCR** — {glossary.PCR}")

    with st.expander("Validation summary (does the metric add value?)"):
        st.markdown(
            "- PIS vs PFF-credited pressures allowed: **Spearman −0.64** "
            "(geometry alone, with no outcome adjustment, is still **−0.51**).\n"
            "- Sack rate across PIS bands falls **97% → 69% → 7% → 0.2% → 0%**; "
            "pressure rate falls **87% → 1.5%**.\n"
            "- Rank order is stable to the pressure radius (ρ ≥ 0.98) and to "
            "component weights (ρ ≥ 0.99).\n"
            "- Held-out weeks 1–6 vs 7–8 (game-grouped): PPPR rank ρ = 0.27 — "
            "a real but modest signal over an 8-week sample.\n\n"
            "Correlation is evidence of association, not proof of causation or "
            "out-of-sample prediction. Full report: `reports/validation.txt`."
        )
        st.caption("**Limitations.** " + glossary.LIMITATIONS)

with right:
    st.subheader("Example plays")
    st.caption("Real, verified plays that show what PIS captures. Click to open "
               "in the Play Explorer.")
    ex_path = C.CACHE_DIR / "example_plays.json"
    if ex_path.exists():
        examples = json.loads(ex_path.read_text())
        for key in ("clean", "collapse", "sack"):
            ex = examples.get(key)
            if not ex:
                continue
            with st.container(border=True):
                cc1, cc2 = st.columns([3, 1])
                with cc1:
                    st.markdown(f"**{ex['narrative']}**")
                    st.markdown(
                        f'<span class="muted">min QB space {ex["min_clean_dist"]} yd '
                        f'· clean {ex["early_clean"]}→{ex["late_clean"]} yd '
                        f'· {ex["end_kind"]}</span>', unsafe_allow_html=True)
                with cc2:
                    ui.pis_badge(ex["pis"])
                if st.button("Open play ▶", key=f"ex_{key}", use_container_width=True):
                    ui.goto_play(ex["gameId"], ex["playId"])
    else:
        st.info("Run `python scripts/find_examples.py` to populate example plays.")

    st.subheader("Views")
    st.markdown(
        "- **Play Explorer** — animate any play with the live pocket overlay.\n"
        "- **Leaderboards** — rank protectors (PPPR) and rushers (PCR).\n"
        "- **Matchup Inspector** — blocker-vs-rusher head-to-heads.\n"
        "- **Team / Unit View** — PIS by formation, coverage, down and more."
    )

st.divider()
st.caption(
    f"Data: NFL Big Data Bowl 2023 (2021 season, weeks 1–8). "
    f"Cache built {meta.get('built_at','?')}. "
    "Tracking by NFL Next Gen Stats; scouting by PFF."
)
