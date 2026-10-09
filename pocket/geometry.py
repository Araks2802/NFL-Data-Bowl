"""Per-frame pocket geometry features (Methodology section B).

Given one play's normalised tracking rows plus role lookups, compute, for every
frame in the observation window, a set of defensible pocket features:

  hull_area      convex-hull area (yd^2) of QB + nearby blockers
  clean_dist     QB distance to nearest pass rusher (yd)
  n_near         # rushers within proximity_radius of QB
  closing        closing speed of nearest rusher toward QB (yd/s)
  edge_dist      nearest rusher attacking from the edge, behind the QB's depth
  interior_dist  nearest rusher penetrating the interior gap
  depth_cushion  QB x minus deepest threatening rusher x (yd)
  qb_x, qb_y     QB position (for app overlays)
  hull_xy        hull polygon vertices (for app overlays)
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy.spatial import ConvexHull, QhullError

from . import config as C


@dataclass
class Roles:
    qb_id: int
    blocker_ids: set[int]
    rusher_ids: set[int]


def roles_from_pff(pff_play: pd.DataFrame) -> Roles:
    qb_rows = pff_play[pff_play["pff_role"] == C.ROLE_QB]["nflId"]
    qb_id = int(qb_rows.iloc[0]) if len(qb_rows) else -1
    blockers = set(pff_play[pff_play["pff_role"] == C.ROLE_BLOCK]["nflId"].astype(int))
    # route-runners who are credited with blocking (chips) also help the cup
    chip = pff_play[(pff_play["pff_role"] == C.ROLE_ROUTE)
                    & (pff_play["pff_blockType"].notna())]["nflId"].astype(int)
    blockers |= set(chip)
    rushers = set(pff_play[pff_play["pff_role"] == C.ROLE_RUSH]["nflId"].astype(int))
    return Roles(qb_id=qb_id, blocker_ids=blockers, rusher_ids=rushers)


def _poly_area(points: np.ndarray) -> tuple[float, np.ndarray | None]:
    """Convex-hull area and hull vertices for an (n,2) array."""
    if points.shape[0] < 3:
        return 0.0, None
    try:
        hull = ConvexHull(points)
        return float(hull.volume), points[hull.vertices]  # 2D: volume == area
    except (QhullError, ValueError):
        return 0.0, None


def per_frame_features(play_norm: pd.DataFrame, roles: Roles,
                       snap_frame: int, end_frame: int,
                       cfg: C.PISConfig = C.DEFAULT) -> pd.DataFrame:
    """Compute per-frame features over [snap_frame, end_frame] inclusive.

    play_norm: normalised tracking rows for ONE play (players + football).
    Returns a DataFrame indexed by frameId with one row per frame.
    """
    df = play_norm[(play_norm["frameId"] >= snap_frame)
                   & (play_norm["frameId"] <= end_frame)].copy()
    rows = []
    for fid, fr in df.groupby("frameId"):
        qb = fr[fr["nflId"] == roles.qb_id]
        if qb.empty:
            rows.append(dict(frameId=int(fid), usable=False))
            continue
        qx, qy = float(qb["x"].iloc[0]), float(qb["y"].iloc[0])

        blockers = fr[fr["nflId"].isin(roles.blocker_ids)]
        rushers = fr[fr["nflId"].isin(roles.rusher_ids)]

        # --- hull of QB + blockers within radius of QB ---
        bl_xy = blockers[["x", "y"]].to_numpy()
        if bl_xy.size:
            d = np.hypot(bl_xy[:, 0] - qx, bl_xy[:, 1] - qy)
            near_bl = bl_xy[d <= cfg.hull_blocker_radius]
        else:
            near_bl = np.empty((0, 2))
        hull_pts = np.vstack([[qx, qy], near_bl]) if near_bl.size else np.array([[qx, qy]])
        hull_area, hull_vertices = _poly_area(hull_pts)

        # --- rushers relative to QB ---
        if not rushers.empty:
            rxy = rushers[["x", "y"]].to_numpy()
            rv = rushers[["vx", "vy"]].to_numpy()
            dvec = np.column_stack([qx - rxy[:, 0], qy - rxy[:, 1]])  # rusher->QB
            dist = np.hypot(dvec[:, 0], dvec[:, 1])
            dist = np.where(dist < 1e-6, 1e-6, dist)
            # closing speed = component of rusher velocity toward QB
            closing_all = (rv[:, 0] * dvec[:, 0] + rv[:, 1] * dvec[:, 1]) / dist
            nearest = int(np.argmin(dist))
            clean_dist = float(dist[nearest])
            closing = float(max(closing_all[nearest], 0.0))
            n_near = int(np.sum(dist <= cfg.proximity_radius))

            # edge vs interior: y-offset from QB and x relative to QB
            dy = np.abs(rxy[:, 1] - qy)
            past_depth = rxy[:, 0] >= qx - 1.0  # rusher at/behind QB's depth
            edge_mask = (dy > 2.5) & past_depth
            int_mask = (dy <= 2.5) & past_depth
            edge_dist = float(dist[edge_mask].min()) if edge_mask.any() else np.nan
            interior_dist = float(dist[int_mask].min()) if int_mask.any() else np.nan
            # depth cushion vs deepest threatening rusher (closest in x to QB)
            threat = rxy[dist <= cfg.proximity_radius * 2]
            if threat.size:
                deepest_rx = float(threat[:, 0].max())
                depth_cushion = float(qx - deepest_rx)
            else:
                depth_cushion = float(cfg.d_depth)
        else:
            clean_dist = float(cfg.d_clean * 2)
            closing = 0.0
            n_near = 0
            edge_dist = np.nan
            interior_dist = np.nan
            depth_cushion = float(cfg.d_depth)

        rows.append(dict(
            frameId=int(fid), usable=True,
            qb_x=qx, qb_y=qy,
            hull_area=hull_area,
            n_blockers_in_cup=int(near_bl.shape[0]),
            clean_dist=clean_dist, closing=closing, n_near=n_near,
            edge_dist=edge_dist, interior_dist=interior_dist,
            depth_cushion=depth_cushion,
            hull_vertices=hull_vertices.tolist() if hull_vertices is not None else None,
        ))
    out = pd.DataFrame(rows).sort_values("frameId").reset_index(drop=True)
    return out
