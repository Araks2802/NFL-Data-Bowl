"""Probe specific assumptions needed to design PIS correctly.

Checks:
1. For a few plays: PFF roles present, blocker->defender assignments, and
   how pff_hit/hurry/sack vs *Allowed are distributed across roles.
2. Event sequence timing on real plays (snap -> pass_forward/sack).
3. Which pff_role rows have the defender-credited vs blocker-credited columns.
4. Football tracking coverage and QB identification.
"""
from __future__ import annotations

from pathlib import Path
import pandas as pd

DATA = Path(__file__).resolve().parents[1] / "data"
TRACKING = DATA / "tracking"

plays = pd.read_csv(DATA / "plays.csv", na_values=["NA"])
pff = pd.read_csv(DATA / "pffScoutingData.csv", na_values=["NA"])

print("=" * 70)
print("1. Which roles carry which PFF outcome columns (non-null counts)")
print("=" * 70)
for role, g in pff.groupby("pff_role"):
    print(f"\n{role} (n={len(g)}):")
    for c in ["pff_hit", "pff_hurry", "pff_sack", "pff_hitAllowed",
              "pff_hurryAllowed", "pff_sackAllowed", "pff_beatenByDefender",
              "pff_nflIdBlockedPlayer", "pff_blockType", "pff_backFieldBlock"]:
        nn = g[c].notna().sum()
        if nn:
            print(f"   {c:<26} nonnull={nn:>6} ({nn/len(g)*100:4.1f}%)")

print("\n" + "=" * 70)
print("2. Blocker->defender assignment: do rushers have hit/hurry/sack and")
print("   blockers have *Allowed? Cross-check on one play.")
print("=" * 70)
gid = 2021090900
sample_play = pff[pff.gameId == gid].playId.iloc[0]
cols = ["nflId", "pff_role", "pff_positionLinedUp", "pff_hit", "pff_hurry",
        "pff_sack", "pff_hitAllowed", "pff_hurryAllowed", "pff_sackAllowed",
        "pff_beatenByDefender", "pff_nflIdBlockedPlayer", "pff_blockType"]
pr = pff[(pff.gameId == gid) & (pff.playId == sample_play)][cols]
print(f"play {gid}/{sample_play}:")
print(pr.to_string(index=False))

print("\n" + "=" * 70)
print("3. Event sequence on first 3 plays of a game (snap/pass/sack timing)")
print("=" * 70)
t = pd.read_csv(TRACKING / f"tracking_{gid}.csv", na_values=["NA"])
for pid in t.playId.unique()[:3]:
    sub = t[(t.playId == pid)]
    # events happen simultaneously across players; take ball or any player
    ev = sub[["frameId", "event"]].drop_duplicates()
    ev = ev[ev.event.notna() & (ev.event != "None")]
    ev = ev.groupby("event").frameId.min().sort_values()
    pres = plays[(plays.gameId == gid) & (plays.playId == pid)]
    pr_txt = pres.passResult.iloc[0] if len(pres) else "?"
    maxf = sub.frameId.max()
    print(f"\nplay {pid}  passResult={pr_txt}  maxFrame={maxf}")
    for e, f in ev.items():
        print(f"   frame {f:>3}: {e}")

print("\n" + "=" * 70)
print("4. QB identification + football coverage on one play")
print("=" * 70)
qb_ids = pff[(pff.pff_role == "Pass")][["gameId", "playId", "nflId"]]
print("QB rows (pff_role=='Pass') per play == 1?",
      (pff[pff.pff_role == "Pass"].groupby(["gameId", "playId"]).size() == 1).all())
sub = t[t.playId == t.playId.unique()[0]]
fb = sub[sub.team == "football"]
print(f"football frames on play {t.playId.unique()[0]}: {len(fb)} "
      f"(play has {sub.frameId.max()} frames)")

print("\n" + "=" * 70)
print("5. How many pass-block rows per play (blockers available for hull)?")
print("=" * 70)
bl = pff[pff.pff_role == "Pass Block"].groupby(["gameId", "playId"]).size()
print(f"blockers/play: min={bl.min()} median={bl.median()} max={bl.max()}")
ru = pff[pff.pff_role == "Pass Rush"].groupby(["gameId", "playId"]).size()
print(f"rushers/play: min={ru.min()} median={ru.median()} max={ru.max()}")
