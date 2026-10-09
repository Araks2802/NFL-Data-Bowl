"""Validation report for PIS (Methodology section F).

Reads the cached tables (run build_cache.py first) and reports:
  1. Scorability / approximation coverage.
  2. Component correlation matrix (double-counting check).
  3. PIS correlation with PFF-credited pressure outcomes.
  4. Outcome rates by PIS band (monotonicity check).
  5. Sensitivity to proximity radius R and component weights (recompute sample).
  6. Held-out rank stability (weeks 1-6 vs 7-8), game-grouped (no leakage).
  7. Player-ranking sample sizes and uncertainty.

Writes reports/validation.txt and prints the summary.
"""
from __future__ import annotations

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd
from scipy.stats import spearmanr, pearsonr

from pocket import config as C
from pocket import io, pipeline, attribution

OUT = C.REPORTS_DIR / "validation.txt"
lines: list[str] = []


def log(*p):
    msg = " ".join(str(x) for x in p)
    print(msg, flush=True)
    lines.append(msg)


def section(t):
    log("\n" + "=" * 72)
    log(t)
    log("=" * 72)


def main():
    plays = pd.read_parquet(C.PLAYS_PIS_PARQUET)
    pp = pd.read_parquet(C.PLAYER_PLAY_PARQUET)
    players = io.load_players()
    sc = plays[plays["scorable"]].copy()

    section("1. SCORABILITY & APPROXIMATION COVERAGE")
    log(f"total plays scored        : {len(plays):,}")
    log(f"scorable                  : {sc.shape[0]:,} "
        f"({sc.shape[0]/len(plays)*100:.1f}%)")
    log("unscorable reasons        :",
        plays[~plays.scorable].unscorable_reason.value_counts().to_dict())
    log(f"snap approximated         : {int(plays.snap_approx.sum())} "
        f"({plays.snap_approx.mean()*100:.1f}%)")
    log(f"end approximated          : {int(plays.end_approx.sum())} "
        f"({plays.end_approx.mean()*100:.1f}%)")
    log("end_kind distribution     :", plays.end_kind.value_counts().to_dict())

    section("2. COMPONENT CORRELATION MATRIX (double-counting check)")
    comps = ["s_clean", "s_press", "s_collapse", "s_closing", "s_final"]
    corr = sc[comps].corr().round(2)
    log(corr.to_string())
    log("\nInterpretation: components should be positively but not perfectly")
    log("correlated. |r|>0.9 would suggest redundancy.")
    hi = [(a, b, corr.loc[a, b]) for a in comps for b in comps
          if a < b and abs(corr.loc[a, b]) > 0.9]
    log("pairs with |r|>0.9:", hi if hi else "none (good)")

    section("3. PIS vs PFF-CREDITED PRESSURE (association)")
    # play-level pressure allowed count from pp table
    pa = (pp[pp.side == "offense"]
          .groupby(["gameId", "playId"])
          .agg(press_allowed=("pressureAllowed", "sum"),
               sacks_allowed=("sackAllowed", "sum"))
          .reset_index())
    m = sc.merge(pa, on=["gameId", "playId"], how="left").fillna(
        {"press_allowed": 0, "sacks_allowed": 0})
    r_p, _ = pearsonr(m["pis"], m["press_allowed"])
    r_s, _ = spearmanr(m["pis"], m["press_allowed"])
    log(f"Pearson  r(PIS, pressures allowed)  = {r_p:+.3f}")
    log(f"Spearman r(PIS, pressures allowed)  = {r_s:+.3f}")
    log("Expect NEGATIVE: higher PIS -> fewer pressures allowed.")
    # also geometry-only PIS (remove outcome adj) to show it's not just the label
    m["pis_geom_only"] = m["pis_geom"]
    r_geom, _ = spearmanr(m["pis_geom_only"], m["press_allowed"])
    log(f"Spearman r(PIS_geom_only, pressures)= {r_geom:+.3f}  "
        "(geometry alone, no outcome adjustment)")

    section("4. OUTCOME RATES BY PIS BAND (monotonicity)")
    bands = pd.cut(m["pis"], [0, 40, 55, 70, 85, 100])
    tbl = m.groupby(bands, observed=True).agg(
        n=("pis", "size"),
        mean_pis=("pis", "mean"),
        sack_rate=("passResult", lambda s: (s == "S").mean()),
        pressure_rate=("press_allowed", lambda s: (s > 0).mean()),
        mean_pressures=("press_allowed", "mean"),
    ).round(3)
    log(tbl.to_string())
    log("\nExpect sack_rate and pressure_rate to FALL as PIS band rises.")

    section("5. SENSITIVITY TO PROXIMITY RADIUS R (recompute on sample)")
    sample_games = io.available_game_ids()[:6]
    base = _recompute(sample_games, C.PISConfig())
    for R in (1.5, 2.0, 2.5, 3.0):
        cfg = C.PISConfig(proximity_radius=R)
        alt = _recompute(sample_games, cfg)
        j = base.merge(alt, on=["gameId", "playId"], suffixes=("_base", "_alt"))
        rho, _ = spearmanr(j["pis_base"], j["pis_alt"])
        log(f"R={R:>3}: mean PIS={alt.pis.mean():5.1f}  "
            f"rank corr vs default R=2.0: rho={rho:.3f}")

    section("5b. SENSITIVITY TO COMPONENT WEIGHTS")
    weight_sets = {
        "default": C.PISConfig(),
        "clean-heavy": C.PISConfig(w_clean=0.5, w_press=0.2, w_collapse=0.1,
                                   w_closing=0.1, w_final=0.1),
        "equal": C.PISConfig(w_clean=0.2, w_press=0.2, w_collapse=0.2,
                             w_closing=0.2, w_final=0.2),
    }
    for name, cfg in weight_sets.items():
        alt = _recompute(sample_games, cfg)
        j = base.merge(alt, on=["gameId", "playId"], suffixes=("_b", "_a"))
        rho, _ = spearmanr(j["pis_b"], j["pis_a"])
        log(f"{name:>12}: mean PIS={alt.pis.mean():5.1f}  rank corr vs default rho={rho:.3f}")

    section("6. HELD-OUT RANK STABILITY (wk1-6 vs wk7-8, game-grouped)")
    _held_out(plays, pp, players)

    section("7. PLAYER RANKING SAMPLE SIZES & UNCERTAINTY")
    pppr = pd.read_parquet(C.PPPR_PARQUET)
    pcr = pd.read_parquet(C.PCR_PARQUET)
    log(f"PPPR qualified players (>= {C.DEFAULT.min_snaps_offense} snaps): "
        f"{int(pppr.qualified.sum())}")
    log(f"PCR  qualified players (>= {C.DEFAULT.min_snaps_defense} snaps): "
        f"{int(pcr.qualified.sum())}")
    if not pppr.empty:
        q = pppr[pppr.qualified]
        log(f"PPPR snaps: min={q.snaps.min()} median={int(q.snaps.median())} "
            f"max={q.snaps.max()}  mean bootstrap_sd={q.bootstrap_sd.mean():.2f}")
    if not pcr.empty:
        q = pcr[pcr.qualified]
        log(f"PCR  snaps: min={q.snaps.min()} median={int(q.snaps.median())} "
            f"max={q.snaps.max()}  mean bootstrap_sd={q.bootstrap_sd.mean():.2f}")

    log("\nNOTE: correlations are evidence of ASSOCIATION, not causation or")
    log("proof of out-of-sample predictive power.")

    OUT.write_text("\n".join(lines))
    log(f"\nWrote {OUT}")


def _recompute(game_ids, cfg) -> pd.DataFrame:
    chunks = []
    for g in game_ids:
        pl, _ = pipeline.score_game(g, cfg=cfg, want_frames=False)
        chunks.append(pl[["gameId", "playId", "pis", "scorable"]])
    df = pd.concat(chunks, ignore_index=True)
    return df[df.scorable][["gameId", "playId", "pis"]]


def _held_out(plays, pp, players):
    off_rows = pp[(pp.side == "offense") & pp.scorable]
    plays_wk = plays[["gameId", "playId", "week"]]
    off = off_rows.merge(plays_wk, on=["gameId", "playId"], how="left")
    early = off[off.week <= 6]
    late = off[off.week >= 7]
    cfg = C.PISConfig(min_snaps_offense=25)
    a = attribution.aggregate_offense(early, players, cfg)
    b = attribution.aggregate_offense(late, players, cfg)
    if a.empty or b.empty:
        log("insufficient data for held-out split")
        return
    j = a[a.qualified].merge(b[b.qualified], on="nflId", suffixes=("_early", "_late"))
    if len(j) >= 5:
        rho, _ = spearmanr(j["PPPR_early"], j["PPPR_late"])
        log(f"PPPR rank stability: n={len(j)} players in both halves, "
            f"Spearman rho(early, late) = {rho:.3f}")
    else:
        log(f"only {len(j)} players qualified in both halves (min_snaps=25)")


if __name__ == "__main__":
    main()
