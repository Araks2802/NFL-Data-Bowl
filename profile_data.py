"""Profile the NFL Big Data Bowl pass-protection dataset.

Reports schemas, row counts, missingness, event coverage, PFF roles, and
pass-result distribution. Writes a human-readable report to
reports/data_profile.txt and prints a summary.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pandas as pd

DATA = Path(__file__).resolve().parents[1] / "data"
TRACKING = DATA / "tracking"
OUT = Path(__file__).resolve().parents[1] / "reports"
OUT.mkdir(parents=True, exist_ok=True)

lines: list[str] = []


def log(*parts) -> None:
    msg = " ".join(str(p) for p in parts)
    print(msg)
    lines.append(msg)


def profile_flat(name: str, path: Path, na_values=("NA",)) -> pd.DataFrame:
    df = pd.read_csv(path, na_values=list(na_values), keep_default_na=True, low_memory=False)
    log(f"\n{'='*70}\n{name}  ({path.name})\n{'='*70}")
    log(f"rows: {len(df):,}  cols: {len(df.columns)}")
    log("columns:", list(df.columns))
    log("\ndtypes:")
    for c in df.columns:
        log(f"  {c:<28} {str(df[c].dtype):<10} nulls={df[c].isna().sum():>8} "
            f"({df[c].isna().mean()*100:5.1f}%)  nunique={df[c].nunique(dropna=True)}")
    return df


def main() -> None:
    games = profile_flat("GAMES", DATA / "games.csv")
    log("weeks:", sorted(games["week"].unique().tolist()))
    log("teams (home):", sorted(games["homeTeamAbbr"].unique().tolist()))

    players = profile_flat("PLAYERS", DATA / "players.csv")
    log("positions:", players["officialPosition"].value_counts().to_dict())

    plays = profile_flat("PLAYS", DATA / "plays.csv")
    log("\npassResult distribution:")
    log(plays["passResult"].value_counts(dropna=False).to_dict())
    log("offenseFormation:", plays["offenseFormation"].value_counts(dropna=False).to_dict())
    log("dropBackType:", plays["dropBackType"].value_counts(dropna=False).to_dict())
    log("pff_passCoverage:", plays["pff_passCoverage"].value_counts(dropna=False).to_dict())
    log("pff_playAction:", plays["pff_playAction"].value_counts(dropna=False).to_dict())
    log("unique plays (gameId,playId):", plays[["gameId", "playId"]].drop_duplicates().shape[0])

    pff = profile_flat("PFF SCOUTING", DATA / "pffScoutingData.csv")
    log("\npff_role distribution:")
    log(pff["pff_role"].value_counts(dropna=False).to_dict())
    log("pff_positionLinedUp:", pff["pff_positionLinedUp"].value_counts(dropna=False).to_dict())
    log("pff_blockType:", pff["pff_blockType"].value_counts(dropna=False).to_dict())
    for c in ["pff_hit", "pff_hurry", "pff_sack", "pff_hitAllowed", "pff_hurryAllowed",
              "pff_sackAllowed", "pff_beatenByDefender"]:
        log(f"  {c}: nonnull={pff[c].notna().sum()}  sum={pd.to_numeric(pff[c], errors='coerce').sum()}")

    # tracking: profile one file in detail, then survey event vocabulary across a few
    track_files = sorted(TRACKING.glob("tracking_*.csv"))
    log(f"\n{'='*70}\nTRACKING\n{'='*70}")
    log(f"num tracking files: {len(track_files)}")
    t0 = pd.read_csv(track_files[0], na_values=["NA"], low_memory=False)
    log(f"sample file: {track_files[0].name}  rows: {len(t0):,}  cols: {len(t0.columns)}")
    log("columns:", list(t0.columns))
    log("playDirection:", t0["playDirection"].value_counts(dropna=False).to_dict())
    log("football rows (nflId NA):", t0["nflId"].isna().sum())
    log("teams in tracking:", t0["team"].value_counts(dropna=False).to_dict())
    log("frames per play (sample):")
    fp = t0.groupby("playId")["frameId"].max()
    log(f"  min={fp.min()} median={fp.median()} max={fp.max()}")

    # event vocabulary across first 5 files
    events = {}
    for f in track_files[:5]:
        ev = pd.read_csv(f, usecols=["event"], na_values=["NA"])  # type: ignore
        for k, v in ev["event"].value_counts(dropna=False).to_dict().items():
            events[k] = events.get(k, 0) + v
    log("\nevent vocabulary (first 5 files):")
    for k, v in sorted(events.items(), key=lambda kv: -kv[1]):
        log(f"  {str(k):<28} {v:>8}")

    (OUT / "data_profile.txt").write_text("\n".join(lines))
    log(f"\nWrote report to {OUT / 'data_profile.txt'}")


if __name__ == "__main__":
    main()
