# Pocket Integrity Score (PIS) — Methodology

This document defines the Pocket Integrity Score and the two player-level
ratings derived from it **before** any rankings are produced, as required by
the brief. Every component below is grounded in facts verified directly
against the supplied data (see `reports/data_profile.txt` and
`scripts/probe_assumptions.py`).

> **Dataset.** NFL Big Data Bowl 2023 pass-protection data: 2021 season,
> weeks 1–8, 122 games, 8,557 pass plays, player tracking at 10 Hz, PFF
> scouting per player-play.

---

## 0. What problem this solves

A coach/scout wants to know **which linemen and protection units create the
cleanest, most sustainable pockets, and which defenders generate pressure
consistently** — not just who shows up on the sack sheet. Sacks are rare
(543 of 8,557 plays) and noisy. PIS measures the *continuous geometry and
dynamics* of the pocket from snap to the throw, so that a quietly collapsing
pocket that ends in a completion is still scored as poor protection, and a
clean pocket that ends in a coverage sack is still scored as good protection.

---

## A. Eligible observation window

For each play we define the scoring window `[t_snap, t_end]` from the tracking
`event` column, with explicit fallbacks that are **labelled as approximations**
when used.

- **Start `t_snap`**: first frame with `ball_snap`; fallback `autoevent_ballsnap`;
  final fallback = first frame (flagged `snap_approx=True`).
- **End `t_end`**: earliest of the play's actual terminating event, chosen by
  `passResult`:
  - `C`/`I`/`IN` → `pass_forward` (fallback `autoevent_passforward`,
    `pass_shovel`); the pocket's job ends at release.
  - `S` (sack) → `qb_sack` / `qb_strip_sack`.
  - `R` (scramble) → the frame the QB crosses the line of scrimmage *or*
    `run`, whichever is first; otherwise `pass_forward` if the scramble ended
    in a throw.
  - If no terminating event is found, `t_end` = last tracking frame and the
    play is flagged `end_approx=True`.
- Plays where neither a snap nor any plausible endpoint can be resolved, or
  where the window is shorter than 5 frames (0.5 s), are marked
  **`scorable=False`** and excluded from scoring and rankings. We never
  substitute zero for missing evidence.

Play direction is normalised so every play attacks **left → right**: for
`playDirection == "left"` we map `x → 120 - x`, `y → 160/3 - y`, and rotate
orientation/direction angles by 180°. All geometry below assumes this frame.

---

## B. Pocket geometry — candidate features (validated, not assumed)

We do **not** assume convex-hull area equals pocket quality. We compute several
defensible features per frame and validate their behaviour on inspected plays
(`scripts/validate_metric.py`). The pocket "cup" is defined from the QB and the
play's **pass blockers** (`pff_role == "Pass Block"`, plus route-runners who are
flagged as blocking, ~5–9 players/play).

Per frame `f`:

1. **Pocket area** `hull_area(f)` — convex-hull area (yd²) of {QB} ∪ {blockers
   still within 4 yd of the QB}. We restrict to nearby blockers so a lineman who
   releases downfield does not inflate the hull. An **expanding** hull is only
   credited if the QB remains inside it and depth behind the QB is maintained;
   pure lateral expansion from a blocker drifting is not rewarded (we track the
   hull centroid relative to the QB).
2. **QB clean space** `clean_dist(f)` — distance from the QB to the nearest
   **pass rusher** (`pff_role == "Pass Rush"`). This is the single most direct
   pressure signal.
3. **Pressure proximity** `n_near(f)` — count of pass rushers within radius `R`
   (default 2.0 yd) of the QB. Sensitivity to `R` is reported in validation.
4. **Closing speed** `closing(f)` — rate of decrease of `clean_dist`, i.e. how
   fast the nearest rusher is collapsing distance (yd/s), using the rusher's
   velocity component toward the QB.
5. **Edge integrity** — minimum distance from the QB to any rusher who has
   crossed **behind** the tackle box laterally (|y − y_QB| large, x past the
   QB's depth) on either edge. Captures edge rushers turning the corner.
6. **Interior collapse** — minimum distance from the QB to any rusher
   penetrating the **interior** gap (between the guards, i.e. small |y − y_QB|,
   x at or past the QB). Captures DT push up the middle.
7. **Depth cushion** — longitudinal distance (x) the QB has behind the deepest
   threatening rusher; a pocket that keeps the rush in front of the QB is better
   than one where a rusher is level with or behind him.

Each feature is validated for sensible behaviour (clean plays score high,
sack plays collapse) before it is allowed into the score.

---

## C. PIS definition (interpretable, 0–100)

PIS aggregates the per-frame features over the eligible window into a single
0–100 score. It is a **weighted blend of normalised sub-scores**, each in
[0, 1], then scaled ×100 and adjusted for outcome.

### Per-frame cleanliness `c(f) ∈ [0,1]`

A smooth blend of the proximity-based signals (the components most directly
tied to "is the QB about to get hit"):

```
clean_space_score(f)  = clamp(clean_dist(f) / D_clean, 0, 1)      # D_clean = 3.5 yd
proximity_score(f)    = 1 - clamp(n_near(f) / N_max, 0, 1)        # N_max = 3 rushers
closing_score(f)      = 1 - clamp(closing(f) / C_max, 0, 1)       # C_max = 6 yd/s
depth_score(f)        = clamp(depth_cushion(f) / D_depth, 0, 1)   # D_depth = 3 yd
```

### Play-level components (window aggregates)

| Component | Symbol | Definition | Weight |
|-----------|--------|------------|--------|
| Clean-space sustain | `S_clean` | time-weighted mean of `clean_space_score` | 0.30 |
| Pressure load | `S_press` | time-weighted mean of `proximity_score` | 0.20 |
| Collapse resistance | `S_collapse` | 1 − normalised pocket-area shrink rate (area at end ÷ area at peak, floored) | 0.20 |
| Closing control | `S_closing` | time-weighted mean of `closing_score` | 0.15 |
| Last-second integrity | `S_final` | mean cleanliness over the final 0.5 s before `t_end` (the throw/sack moment) | 0.15 |

`PIS_geom = 100 × (0.30 S_clean + 0.20 S_press + 0.20 S_collapse + 0.15 S_closing + 0.15 S_final)`

Weights are **initial, interpretable priors** chosen after inspecting feature
distributions and pairwise correlations (`scripts/validate_metric.py` reports
the correlation matrix so we can confirm each component adds distinct
information and is not double-counting). They are documented and surfaced in the
app's "How PIS works" panel, and the app lets analysts re-weight live.

### Outcome adjustment

The geometry score is nudged by the recorded outcome so that the metric agrees
with what actually happened, without collapsing to a binary sack flag:

```
PIS = clamp( PIS_geom + Δ_outcome , 0, 100 )
Δ_outcome:  sack           −12
            QB hit          −6
            hurry           −4
            scramble        −3   (pocket forced QB to leave)
            clean throw     +2
```

The adjustment is bounded and small relative to the geometry score, so PIS is
**primarily tracking-derived** and only *calibrated* by outcomes. A clean-pocket
sack (coverage sack) keeps a high geometry score minus a modest penalty; a
collapsing-pocket completion keeps a low geometry score plus a small bonus.

### Missing-data rule

If a required per-frame feature cannot be computed for > 40 % of the window
(e.g. no rushers tracked, QB missing), the play is **`scorable=False`** rather
than scored with substituted zeros.

---

## D. Individual outcomes vs causal attribution

We keep three clearly separated layers and never conflate them:

1. **Recorded individual outcomes** (ground truth from PFF):
   - Blockers: `pff_hitAllowed`, `pff_hurryAllowed`, `pff_sackAllowed`,
     `pff_beatenByDefender`, `pff_nflIdBlockedPlayer` (who they blocked),
     `pff_blockType` (incl. `SW` switch, `CH` chip).
   - Rushers/defenders: `pff_hit`, `pff_hurry`, `pff_sack`.
2. **Tracking-derived observations**: defender proximity, closing speed, which
   gap a rusher won, time-to-pressure.
3. **Estimated contributions**: a player's share of the play's pocket integrity.

**Attribution rules** (we do *not* assign pressure to the nearest defender):

- Blocker↔rusher pairing uses **`pff_nflIdBlockedPlayer`**, which handles double
  teams (two blockers → one rusher), switches (`SW`) and chips (`CH`).
- A pressure is attributed to a blocker only when PFF credits them
  (`*Allowed == 1`) or when they are the assigned blocker on the rusher who
  recorded the pressure. Where assignment is missing (3.3 % of blocker rows) or
  ambiguous (stunts with unclear hand-off), the contribution is marked
  **`attribution_uncertain`** and excluded from the causal rate, though the play
  still contributes to the player's team-level pocket exposure.

---

## E. Player ratings

### PPPR — Player Pocket Preservation Rating (offense: T, G, C, TE, RB, FB, QB)

Per blocker-play contribution:

```
contrib = PIS(play)                               # the pocket they helped build
        − k_hit  · hitAllowed
        − k_hur  · hurryAllowed
        − k_sack · sackAllowed
        − k_beat · beatenByDefender
```

A player's PPPR is the **snap-weighted mean contribution**, scaled to 0–100
across qualifying players (min-snap threshold, default 50). QBs get a mobility
adjustment: a QB who routinely preserves/extends the pocket with movement is
credited; one who holds the ball into sacks behind a clean pocket is penalised
(QB-attributed collapse).

### PCR — Pressure Creation Rating (defense: DE, DT, NT, OLB, ILB, MLB, DB...)

Per rusher-play contribution:

```
contrib = (100 − PIS(play, attributable_share))   # pocket they helped break
        + m_hit  · hit
        + m_hur  · hurry
        + m_sack · sack
        + m_prox · proximity_impact               # tracking: how close/fast they got
```

PCR rewards **consistency** (snap-weighted mean, not totals) so a defender who
pressures on many plays outranks one with a single splash sack. Rankings carry
**sample size and a bootstrap uncertainty band**; players below the min-snap
threshold are shown separately.

---

## F. Validation (must pass before rankings are trusted)

`scripts/validate_metric.py` reports, and the README summarises:

1. **Feature sanity** on manually inspected plays (clean/collapse/sack).
2. **Correlation** of PIS with PFF-credited pressure (hit/hurry/sack allowed).
   Expect strong negative correlation if PIS is meaningful.
3. **Outcome rates by PIS band** (0–20, 20–40, …): sack/pressure rate should
   fall monotonically as PIS rises.
4. **Sensitivity** to `R` (proximity radius), `D_clean`, and component weights.
5. **Component correlation matrix** to check for double-counting.
6. **Held-out check**: compute player ratings on weeks 1–6, confirm rank
   stability on weeks 7–8 (game-grouped split to avoid leakage).
7. **Sample sizes / uncertainty** for every ranked player.

Correlation is reported as evidence of **association**, not causation or proof
of predictive power — stated explicitly in the README.

---

## G. Known limitations (carried into the README)

- PFF assignments are the attribution backbone; where they are missing we flag
  uncertainty rather than guess.
- 8 weeks is a modest sample; player ratings carry wide bands for low-snap
  players.
- Pocket geometry is a 2-D top-down proxy; it cannot see hand-fighting, leverage
  or exact contact, so it complements rather than replaces film/PFF grades.
- Scramble endpoints are the least clean to detect; those plays are flagged.
