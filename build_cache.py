"""Precompute PIS metrics for all games into Parquet cache tables.

Streams one game tracking file at a time (never loads all 122 at once) and
writes:
  cache/plays_pis.parquet       one row per scored play
  cache/player_play.parquet     one row per player-per-play contribution
  cache/player_pppr.parquet     offensive player ratings (PPPR)
  cache/player_pcr.parquet      defensive player ratings (PCR)
  cache/matchups.parquet        blocker<->defender pairing outcomes
  cache/meta.json               config + build metadata

Per-frame geometry (large) is NOT cached for all plays; the app computes it
on demand for the single selected play. find_examples.py caches frames for the
demo plays only.

Usage:
  python scripts/build_cache.py                 # all games
  python scripts/build_cache.py --max-games 10  # quick subset
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from pocket import config as C
from pocket import io, pipeline, attribution


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-games", type=int, default=None,
                    help="limit number of games (for quick iteration)")
    args = ap.parse_args()

    gids = io.available_game_ids()
    if args.max_games:
        gids = gids[: args.max_games]
    players = io.load_players()

    t0 = time.time()
    plays_chunks, pp_chunks = [], []
    for i, gid in enumerate(gids, 1):
        try:
            plays, pp, _ = pipeline.score_game_full(gid, want_frames=False)
        except Exception as e:  # keep going; record which game failed
            print(f"[{i}/{len(gids)}] game {gid} FAILED: {e}", flush=True)
            continue
        plays_chunks.append(plays)
        pp_chunks.append(pp)
        print(f"[{i}/{len(gids)}] game {gid}: {len(plays)} plays, "
              f"{len(pp)} player-play rows  ({time.time()-t0:5.1f}s)", flush=True)

    plays_df = pd.concat(plays_chunks, ignore_index=True)
    pp_df = pd.concat(pp_chunks, ignore_index=True)

    # ratings
    pppr = attribution.aggregate_offense(pp_df, players, C.DEFAULT)
    pcr = attribution.aggregate_defense(pp_df, players, C.DEFAULT)
    matchups = attribution.matchup_rows(pp_df)

    # add team labels to ratings via most-common team on their player-play rows
    team_of = _player_team(pp_df, plays_df)
    for tbl in (pppr, pcr):
        if not tbl.empty:
            tbl["team"] = tbl["nflId"].map(team_of)

    # write parquet
    plays_df.to_parquet(C.PLAYS_PIS_PARQUET, index=False)
    pp_df.to_parquet(C.PLAYER_PLAY_PARQUET, index=False)
    pppr.to_parquet(C.PPPR_PARQUET, index=False)
    pcr.to_parquet(C.PCR_PARQUET, index=False)
    matchups.to_parquet(C.MATCHUPS_PARQUET, index=False)

    scorable = int(plays_df["scorable"].sum())
    meta = {
        "built_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "n_games": len(gids),
        "n_plays": int(len(plays_df)),
        "n_scorable": scorable,
        "scorable_frac": round(scorable / max(len(plays_df), 1), 4),
        "n_player_play_rows": int(len(pp_df)),
        "n_pppr_qualified": int(pppr["qualified"].sum()) if not pppr.empty else 0,
        "n_pcr_qualified": int(pcr["qualified"].sum()) if not pcr.empty else 0,
        "n_matchups": int(len(matchups)),
        "config": C.DEFAULT.as_dict(),
        "build_seconds": round(time.time() - t0, 1),
    }
    C.META_JSON.write_text(json.dumps(meta, indent=2))

    print("\n=== CACHE BUILD COMPLETE ===", flush=True)
    print(json.dumps(meta, indent=2), flush=True)


def _player_team(pp_df: pd.DataFrame, plays_df: pd.DataFrame) -> dict:
    """Map nflId -> team using play possession/defensive team by side."""
    pl = plays_df[["gameId", "playId", "possessionTeam", "defensiveTeam"]]
    m = pp_df.merge(pl, on=["gameId", "playId"], how="left")
    m["team"] = m.apply(
        lambda r: r["possessionTeam"] if r["side"] == "offense" else r["defensiveTeam"],
        axis=1,
    )
    mode = (m.groupby("nflId")["team"]
            .agg(lambda s: s.mode().iloc[0] if not s.mode().empty else None))
    return mode.to_dict()


if __name__ == "__main__":
    main()
