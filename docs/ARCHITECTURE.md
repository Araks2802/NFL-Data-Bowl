# Project Architecture & Implementation Plan

## Stack

- **Python** for all data processing and metric computation.
- **Streamlit** for the interactive dashboard (fast to build, good for a laptop
  demo, no separate frontend build).
- **Plotly** for the animated 2-D field, timeline, and charts.
- **pandas / numpy / scipy** (`ConvexHull`) for feature engineering.
- **pyarrow / Parquet** for the precomputed metric cache so the app never
  recomputes tracking features in the browser.

## Repository layout

```
nfl-big-data-bowl-regional-event-data-main/
├── data/                     # raw CSVs (given) + tracking/
├── pocket/                   # the Python package (pipeline + metric)
│   ├── __init__.py
│   ├── config.py             # paths, tunable constants, PIS weights
│   ├── io.py                 # load/clean/join raw tables
│   ├── normalize.py          # play-direction normalisation
│   ├── events.py             # eligible observation window (A)
│   ├── geometry.py           # per-frame pocket features (B)
│   ├── pis.py                # PIS computation (C)
│   ├── attribution.py        # blocker<->rusher, PPPR/PCR (D, E)
│   └── pipeline.py           # orchestration: play-level + player-level tables
├── scripts/
│   ├── profile_data.py       # data profiling (done)
│   ├── probe_assumptions.py  # assumption checks (done)
│   ├── build_cache.py        # precompute all metrics -> cache/*.parquet
│   ├── validate_metric.py    # validation report (F)
│   └── find_examples.py      # select & verify 3 demo plays (deliverable 5)
├── app/
│   ├── Home.py               # Streamlit entry (How PIS works + overview)
│   └── pages/
│       ├── 1_Play_Explorer.py
│       ├── 2_Leaderboards.py
│       ├── 3_Matchup_Inspector.py
│       └── 4_Team_Unit_View.py
├── cache/                    # generated parquet metric tables
├── reports/                  # data profile + validation outputs
├── tests/                    # pytest validation checks
├── docs/                     # METHODOLOGY.md, ARCHITECTURE.md
├── requirements.txt
└── README.md
```

## Data flow

```
raw CSVs ──io.load_*──► cleaned frames ──normalize──► L2R tracking
                                   │
                     events.window(play) ─► [t_snap, t_end], flags
                                   │
                 geometry.per_frame(play) ─► hull_area, clean_dist, n_near,
                                             closing, edge/interior, depth
                                   │
                        pis.score(play) ─► PIS + component breakdown
                                   │
          attribution.player_contrib ─► PPPR (off), PCR (def)
                                   │
   build_cache.py ─► cache/plays_pis.parquet
                     cache/player_pppr.parquet
                     cache/player_pcr.parquet
                     cache/matchups.parquet
                     cache/frames_geometry.parquet (for demo plays + on-demand)
                                   │
            Streamlit app reads parquet (cached) ─► 4 views
```

## Performance strategy

- The app **never** loads all 122 tracking files. `build_cache.py` streams one
  game file at a time, computes play-level + player-level metrics, and writes
  compact Parquet. The app reads only those small tables for leaderboards,
  matchups, and team views.
- Play Explorer loads a **single** game's tracking file on demand (cached with
  `st.cache_data`), reconstructs the animation and overlays, and reads
  precomputed per-frame geometry for the pocket/PIS curve.
- A `--sample` / `--max-games` flag on `build_cache.py` allows a quick subset
  build for iteration; the full build runs all 122 games.

## Build order (incremental, each step verified before the next)

1. Package skeleton + `config`, `io`, `normalize` — verify joins & L2R on sample.
2. `events` window + `geometry` features — verify on 3 hand-picked plays.
3. `pis` — compute on a sample, inspect component values and bounds.
4. `attribution` + `pipeline` — PPPR/PCR on a sample.
5. `validate_metric.py` — correlations, bands, sensitivity, held-out.
6. `build_cache.py` — full precompute to Parquet.
7. `find_examples.py` — select & verify the 3 demo plays.
8. Streamlit app: Play Explorer → Leaderboards → Matchup → Team view.
9. `tests/` + README + end-to-end run.
```
