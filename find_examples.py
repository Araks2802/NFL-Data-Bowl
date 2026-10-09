"""Select and verify three real demonstration plays from the cached metrics.

Required narratives (deliverable 5):
  1. CLEAN   : highly protected, clean-pocket completion.
  2. COLLAPSE: gradual pocket-collapse play that still ends in a completion.
  3. SACK    : pressure/sack play caused by edge or interior collapse.

Plays are chosen by querying the actual data (no fabrication) and then verified
by recomputing their per-frame geometry and confirming event sequence, tracking
coverage, outcome, and metric behaviour. Results are written to
cache/example_plays.json for the app and reports/examples.txt for the record.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd

from pocket import config as C
from pocket import io, pipeline

lines: list[str] = []


def log(*p):
    msg = " ".join(str(x) for x in p)
    print(msg, flush=True)
    lines.append(msg)


def _curve_decline(gid, pid):
    """Recompute per-frame clean distance; return (early_mean, late_mean, min)."""
    track = io.load_tracking_game(gid)
    pt = track[track.playId == pid]
    pff = io.pff_for_game(gid)
    pffp = pff[pff.playId == pid]
    plays = io.plays_for_game(gid)
    pr = plays[plays.playId == pid].passResult.iloc[0]
    win, roles, res, frames = pipeline.score_single(pt, pffp, pr, want_frames=True)
    f = frames[frames.usable]
    if len(f) < 6:
        return None
    n = len(f)
    early = f.iloc[: n // 3]["clean_dist"].mean()
    late = f.iloc[-n // 3:]["clean_dist"].mean()
    return dict(win=win, res=res, frames=frames,
                early_clean=float(early), late_clean=float(late),
                min_clean=float(f["clean_dist"].min()),
                edge_min=float(np.nanmin(f["edge_dist"])) if f["edge_dist"].notna().any() else np.nan,
                int_min=float(np.nanmin(f["interior_dist"])) if f["interior_dist"].notna().any() else np.nan)


def verify(gid, pid, label):
    track = io.load_tracking_game(gid)
    pt = track[track.playId == pid]
    ev = (pt[["frameId", "event"]].dropna()
          .query("event != 'None'").groupby("event").frameId.min().sort_values())
    plays = io.plays_for_game(gid)
    prow = plays[plays.playId == pid].iloc[0]
    det = _curve_decline(gid, pid)
    log(f"\n--- {label}: game {gid} play {pid} ---")
    log(f"  desc: {prow.playDescription}")
    log(f"  passResult={prow.passResult}  formation={prow.offenseFormation}  "
        f"coverage={prow.pff_passCoverage}  week={prow.week}")
    log(f"  PIS={det['res'].pis:.1f} (geom={det['res'].pis_geom:.1f}, adj={det['res'].outcome_adj:+.0f})")
    log(f"  clean_dist early={det['early_clean']:.2f} -> late={det['late_clean']:.2f} "
        f"(min={det['min_clean']:.2f})  edge_min={det['edge_min']:.2f}  int_min={det['int_min']:.2f}")
    log(f"  window: snap={det['win'].snap_frame} end={det['win'].end_frame} "
        f"({det['win'].end_kind}, approx snap={det['win'].snap_approx}/end={det['win'].end_approx})")
    log(f"  events: {dict(ev)}")
    return det


def main():
    plays = pd.read_parquet(C.PLAYS_PIS_PARQUET)
    pp = pd.read_parquet(C.PLAYER_PLAY_PARQUET)
    sc = plays[plays.scorable & ~plays.snap_approx & ~plays.end_approx].copy()

    # pressures allowed per play (for narrative selection)
    pa = (pp[pp.side == "offense"].groupby(["gameId", "playId"])
          .pressureAllowed.sum().rename("press_allowed").reset_index())
    sc = sc.merge(pa, on=["gameId", "playId"], how="left").fillna({"press_allowed": 0})

    chosen = {}

    # 1. CLEAN completion: high PIS, completion, no pressure allowed, decent length
    clean = sc[(sc.passResult == "C") & (sc.press_allowed == 0)
               & (sc.end_kind == "pass")
               & ((sc.end_frame - sc.snap_frame) >= 20)]  # >= ~2s to the throw
    clean = clean.sort_values("pis", ascending=False)
    # verify top candidates' geometry really stays clean
    for _, r in clean.head(10).iterrows():
        det = _curve_decline(int(r.gameId), int(r.playId))
        if det and det["min_clean"] > 3.0 and det["late_clean"] > 3.0:
            chosen["clean"] = (int(r.gameId), int(r.playId))
            break

    # 2. COLLAPSE completion: completion, but clean distance declines a lot and
    #    the pocket got tight late, mid PIS (not elite, not sack).
    comp = sc[(sc.passResult == "C") & (sc.end_kind == "pass")
              & (sc.press_allowed >= 1)
              & ((sc.end_frame - sc.snap_frame) >= 25)]
    best = None
    for _, r in comp.sort_values("pis").head(60).iterrows():
        det = _curve_decline(int(r.gameId), int(r.playId))
        if det is None:
            continue
        decline = det["early_clean"] - det["late_clean"]
        # want: started clean, collapsed late, still completed
        if det["early_clean"] > 3.0 and det["late_clean"] < 1.8 and decline > 1.5:
            score = decline
            if best is None or score > best[0]:
                best = (score, int(r.gameId), int(r.playId))
    if best:
        chosen["collapse"] = (best[1], best[2])

    # 3. SACK from edge/interior collapse: sack with a rusher penetrating edge or
    #    interior and very low clean distance.
    sack = sc[(sc.passResult == "S") & (sc.end_kind == "sack")]
    best = None
    for _, r in sack.sort_values("pis").head(40).iterrows():
        det = _curve_decline(int(r.gameId), int(r.playId))
        if det is None:
            continue
        penetration = np.nanmin([det["edge_min"], det["int_min"]])
        if det["min_clean"] < 1.2 and penetration < 1.5:
            kind = "edge" if (not np.isnan(det["edge_min"])
                              and det["edge_min"] <= np.nan_to_num(det["int_min"], nan=1e9)) else "interior"
            if best is None or det["min_clean"] < best[0]:
                best = (det["min_clean"], int(r.gameId), int(r.playId), kind)
    if best:
        chosen["sack"] = (best[1], best[2])
        chosen["_sack_kind"] = best[3]

    # verify + record
    log("=" * 72)
    log("SELECTED DEMONSTRATION PLAYS (queried & verified from the dataset)")
    log("=" * 72)
    out = {}
    labels = {"clean": "1. CLEAN POCKET (completion)",
              "collapse": "2. GRADUAL COLLAPSE (still completed)",
              "sack": f"3. SACK via {chosen.get('_sack_kind','?')} collapse"}
    for key in ("clean", "collapse", "sack"):
        if key not in chosen:
            log(f"\n[WARN] no play matched narrative '{key}'")
            continue
        gid, pid = chosen[key]
        det = verify(gid, pid, labels[key])
        out[key] = {
            "gameId": gid, "playId": pid,
            "narrative": labels[key],
            "pis": round(det["res"].pis, 1),
            "pis_geom": round(det["res"].pis_geom, 1),
            "end_kind": det["win"].end_kind,
            "min_clean_dist": round(det["min_clean"], 2),
            "early_clean": round(det["early_clean"], 2),
            "late_clean": round(det["late_clean"], 2),
        }
        if key == "sack":
            out[key]["collapse_type"] = chosen.get("_sack_kind")

    (C.CACHE_DIR / "example_plays.json").write_text(json.dumps(out, indent=2))
    (C.REPORTS_DIR / "examples.txt").write_text("\n".join(lines))
    log(f"\nWrote {C.CACHE_DIR/'example_plays.json'} and reports/examples.txt")
    log("SCRIPT_OK")


if __name__ == "__main__":
    main()
