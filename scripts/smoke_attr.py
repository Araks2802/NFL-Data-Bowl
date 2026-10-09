"""Smoke-test attribution on a few games: player-play rows + PPPR/PCR aggregation."""
from __future__ import annotations

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd
pd.set_option("display.width", 200)
pd.set_option("display.max_columns", 40)

from pocket import pipeline, io, attribution
import pocket.config as C

gids = io.available_game_ids()[:3]
players = io.load_players()

all_pp = []
for gid in gids:
    plays, pp, _ = pipeline.score_game_full(gid)
    all_pp.append(pp)
    print(f"game {gid}: {len(plays)} plays, {len(pp)} player-play rows")
pp = pd.concat(all_pp, ignore_index=True)

print("\n--- player-play row columns ---")
print(sorted(pp.columns.tolist()))
print("\nsides:", pp.side.value_counts().to_dict())
print("offense roles:", pp[pp.side == "offense"].role.value_counts().to_dict())
print("attribution_uncertain (offense):",
      round(pp[pp.side == "offense"].attribution_uncertain.mean(), 3))

cfg = C.PISConfig(min_snaps_offense=10, min_snaps_defense=10)
off = attribution.aggregate_offense(pp, players, cfg)
dfn = attribution.aggregate_defense(pp, players, cfg)

print("\nOFF cols:", off.columns.tolist())
print("DEF cols:", dfn.columns.tolist())

print("\n--- top 8 PPPR (offense, >=10 snaps) ---")
cols_o = ["displayName", "officialPosition", "snaps", "PPPR", "avg_pis",
          "pressures_allowed", "sacks_allowed", "bootstrap_sd"]
print(off[off.qualified].head(8)[cols_o].round(2).to_string(index=False))

print("\n--- bottom 5 PPPR (worst protectors) ---")
print(off[off.qualified].tail(5)[cols_o].round(2).to_string(index=False))

print("\n--- top 8 PCR (defense, >=10 snaps) ---")
cols_d = ["displayName", "officialPosition", "snaps", "PCR", "pressures",
          "sacks", "pressure_rate", "avg_prox_impact", "bootstrap_sd"]
print(dfn[dfn.qualified].head(8)[cols_d].round(2).to_string(index=False))

mu = attribution.matchup_rows(pp)
print(f"\nmatchup rows: {len(mu)}  (blocker<->assigned defender pairings)")

assert off[off.qualified].PPPR.between(0, 100).all()
assert dfn[dfn.qualified].PCR.between(0, 100).all()
print("\nPPPR and PCR within [0,100]  OK")
