# 🏈 Pocket Integrity Score (PIS)

An interactive pass-protection analytics app built on NFL Next Gen Stats
tracking data (Big Data Bowl 2023 — 2021 season, weeks 1–8). It answers one
coaching/scouting question:

> **Which offensive linemen and protection units create the cleanest, most
> sustainable pockets — and which defenders generate pressure most
> consistently, not just on splash plays?**

The centrepiece is a new, interpretable metric — the **Pocket Integrity Score
(PIS)** — plus two player ratings derived from it: **PPPR** (offense) and
**PCR** (defense). Everything is reconstructed and animated on a 2-D field.

---

## The coaching / scouting problem

Sacks are rare (543 of 8,557 dropbacks) and noisy. A protection unit can
surrender a quietly collapsing pocket on a play that still ends in a completion,
and a clean pocket can end in a coverage sack. Grading protection from the box
score alone misses most of the story.

PIS measures the **continuous geometry and dynamics** of the pocket from snap to
the throw or sack, so sustained clean pockets are rewarded and gradual collapses
are penalised — even when the QB escapes or completes the pass.

---

## The metric, in brief

For every pass play we:

1. **Define a scoring window** `[snap → release / sack / scramble]` from the
   tracking `event` column, with labelled approximations when manual events are
   missing (0.3% of snaps, 0.4% of ends needed one).
2. **Build the pocket** each frame from the QB and his pass blockers (PFF
   `Pass Block` role + chipping backs/TEs).
3. **Measure five interpretable components** and blend them into a 0–100 score,
   then apply a small bounded outcome adjustment:

| Component | Weight | What it measures |
|-----------|:------:|------------------|
| Clean-space sustain | 0.30 | avg QB distance to the nearest rusher |
| Pressure load | 0.20 | how few rushers reached the QB's radius |
| Collapse resistance | 0.20 | pocket holding shape & depth vs shrinking |
| Closing control | 0.15 | how well blockers slowed rushers' closing speed |
| Last-second integrity | 0.15 | cleanliness in the final 0.5 s before the throw |

`PIS = 100 × Σ(weightᵢ · componentᵢ) + outcome_adj` (sack −12, hit −6, hurry −4,
scramble −3, clean throw +2), clamped to 0–100.

Full definition, eligibility and missing-data rules: **[docs/METHODOLOGY.md](docs/METHODOLOGY.md)**.

### Player ratings

- **PPPR — Player Pocket Preservation Rating** (T, G, C, TE, RB, FB): the
  snap-weighted pocket a blocker helped build, minus the hits, hurries and sacks
  PFF credited them with allowing. Scaled 0–100.
- **PCR — Pressure Creation Rating** (pass rushers): snap-weighted pocket
  disruption plus PFF-credited pressures and a tracking proximity term. Rewards
  consistency over one-off splash plays.

Attribution uses PFF's explicit **blocker→defender assignments**
(`pff_nflIdBlockedPlayer`), which handle double teams, switches and chips — we
never assign a pressure to "the nearest defender". Where an assignment is
missing or ambiguous it is flagged `attribution_uncertain` and excluded from the
causal rate.

---

## Does the metric add value? (validation)

From `reports/validation.txt` (full 8,557-play run):

- **Association with PFF-credited pressure:** Spearman **−0.64** (PIS vs
  pressures allowed). Geometry alone, with the outcome adjustment removed, is
  still **−0.51** — the signal comes from tracking, not the outcome label.
- **Monotonic outcome bands:** sack rate falls **97% → 69% → 7% → 0.2% → 0%** and
  pressure rate **87% → 1.5%** as PIS rises across bands.
- **Robust:** rank order is stable to the pressure radius (ρ ≥ 0.98) and to
  component weights (ρ ≥ 0.99).
- **Held-out (weeks 1–6 vs 7–8, game-grouped):** PPPR rank ρ = **0.27** — a
  real but modest signal over an 8-week sample.
- **No double-counting:** no component pair exceeds |r| > 0.9.

Correlation is evidence of **association**, not causation or proof of
out-of-sample prediction.

---

## The app (4 views)

1. **Play Explorer** — animated 2-D field with a timeline scrubber (snap /
   release / sack markers), the live pocket hull, a frame-by-frame PIS curve,
   and toggleable layers: pocket shape, QB clean-space ring, pressure radius,
   player trails, velocity arrows.
2. **Player Leaderboards** — rank protectors by PPPR and rushers by PCR, with
   filters for week, team, position, formation, coverage, dropback type, play
   action and minimum snaps. Rows link to a representative play.
3. **Matchup Inspector** — blocker-vs-rusher head-to-heads built from PFF
   assignments: who beat whom, how often, and the pocket PIS when they met.
4. **Team / Unit View** — offensive-line and defensive-front rankings, plus how
   PIS shifts by formation, coverage, down and play action, with plain-English
   coach insights.

Three verified example plays ship with the app: a clean pocket (Tagovailoa,
PIS 100), a gradual collapse that still scored a TD (Winston, PIS 51), and an
interior-collapse sack (Cousins sacked by Ogunjobi, PIS 34).

---

## How to run

```bash
# 1. install dependencies (Python 3.11+; built on 3.13)
pip install -r requirements.txt

# 2. build the metric cache (reads data/, writes cache/*.parquet)
python scripts/build_cache.py            # all 122 games, ~3-4 min
# or a quick demo subset:
python scripts/build_cache.py --max-games 10

# 3. launch the dashboard
streamlit run app/Home.py
```

The app reads only the small precomputed Parquet tables plus one tracking file
at a time (for the selected play), so it stays responsive on a laptop.

### Reproduce the analysis

```bash
python scripts/profile_data.py      # data profile  -> reports/data_profile.txt
python scripts/validate_metric.py   # validation    -> reports/validation.txt
python scripts/find_examples.py     # demo plays    -> cache/example_plays.json
pytest -q                           # 18 validation tests
```

---

## Project layout

```
pocket/        metric engine: io, normalize, events, geometry, pis, attribution, pipeline
scripts/       build_cache, validate_metric, find_examples, profile_data, + smoke tests
app/           Streamlit: Home.py + pages/ (4 views) + lib/ (data, field, ui, glossary)
cache/         precomputed Parquet tables + meta.json + example_plays.json
reports/       data profile, validation report, example-play record
docs/          METHODOLOGY.md, ARCHITECTURE.md, DATA_DICTIONARY.md
tests/         pytest validation suite
```

Data flow and performance strategy: **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)**.

---

## Key assumptions

- **Join keys:** `gameId` (+ `playId`, + `nflId`) as documented; tracking rows
  with `nflId = NA` are the football. One QB (`pff_role == "Pass"`) per play.
- **Direction** is normalised so every play attacks left→right (`x → 120 − x`,
  `y → 53.3 − y`, angles + 180°). The NGS `dir` convention (0° = +y, clockwise)
  was verified empirically against actual displacement.
- **The pocket** is the QB plus pass blockers within 4 yd; an expanding hull is
  not credited unless depth behind the QB is maintained.
- **Pressure** uses PFF-credited hits/hurries/sacks (defender side) and
  *allowed* (blocker side); attribution uses PFF block assignments.

## Limitations

- PIS is a **top-down 2-D proxy**: it cannot see hand-fighting, leverage or exact
  contact, so it complements film and PFF grades rather than replacing them.
- **8 weeks** is a modest sample; low-snap player ratings carry wide bootstrap
  bands (shown as `±` in the leaderboards).
- Scramble endpoints are the hardest to detect; those plays are flagged.
- Where PFF block assignments are missing (~3% of blocker rows), individual
  attribution is marked uncertain rather than guessed.

## Future improvements

- Expected-pressure / win-probability-weighted PIS to value pockets by
  situation leverage.
- A learned (rather than hand-weighted) component blend, validated with
  game-grouped cross-validation.
- Stunt and twist detection to sharpen multi-rusher attribution.
- Blocker leverage from orientation (`o`) vs the rusher's path.
- Full-season data to tighten player-rating uncertainty.

---

*Data: NFL Big Data Bowl 2023. Tracking by NFL Next Gen Stats; scouting by
[PFF](https://www.pff.com/). The dataset data dictionary is preserved at
[docs/DATA_DICTIONARY.md](docs/DATA_DICTIONARY.md).*
