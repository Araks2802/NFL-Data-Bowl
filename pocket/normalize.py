"""Play-direction normalisation so every play attacks left -> right.

For playDirection == 'left':
    x -> FIELD_LENGTH - x
    y -> FIELD_WIDTH  - y
    o, dir -> (angle + 180) mod 360   (both are compass degrees, 0 = +y)

After normalisation the offense always moves toward increasing x. Velocity
components (vx, vy) are derived from speed `s` and the (normalised) direction
`dir`, which in this dataset is the compass bearing of motion where 0 deg points
toward the +y sideline and 90 deg toward +x. We convert to field vx/vy.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import config as C


def normalize_tracking(df: pd.DataFrame) -> pd.DataFrame:
    """Return a copy with coordinates/angles flipped to left->right.

    Adds columns: vx, vy (yd/s field-frame velocity components).
    """
    out = df.copy()
    left = out["playDirection"] == "left"

    out.loc[left, "x"] = C.FIELD_LENGTH - out.loc[left, "x"]
    out.loc[left, "y"] = C.FIELD_WIDTH - out.loc[left, "y"]
    for c in ("o", "dir"):
        out.loc[left, c] = (out.loc[left, c] + 180.0) % 360.0

    out["playDirection_norm"] = "right"

    # velocity components. dir is compass degrees: 0 -> +y, 90 -> +x (NGS convention).
    # vx = s * sin(theta), vy = s * cos(theta) with theta in radians.
    theta = np.deg2rad(out["dir"].to_numpy())
    s = out["s"].to_numpy()
    out["vx"] = s * np.sin(theta)
    out["vy"] = s * np.cos(theta)
    return out


def normalize_play(df_play: pd.DataFrame) -> pd.DataFrame:
    """Normalise a single play's tracking rows (direction is constant per play)."""
    return normalize_tracking(df_play)
