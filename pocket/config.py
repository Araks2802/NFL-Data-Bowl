"""Central configuration: paths, field constants, and tunable PIS parameters.

All tunable constants live here so they can be surfaced in the app's
"How PIS works" panel and swept in sensitivity analysis.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
TRACKING_DIR = DATA_DIR / "tracking"
CACHE_DIR = ROOT / "cache"
REPORTS_DIR = ROOT / "reports"

GAMES_CSV = DATA_DIR / "games.csv"
PLAYS_CSV = DATA_DIR / "plays.csv"
PLAYERS_CSV = DATA_DIR / "players.csv"
PFF_CSV = DATA_DIR / "pffScoutingData.csv"

CACHE_DIR.mkdir(exist_ok=True)
REPORTS_DIR.mkdir(exist_ok=True)

# Cache table paths
PLAYS_PIS_PARQUET = CACHE_DIR / "plays_pis.parquet"
FRAMES_PARQUET = CACHE_DIR / "frames_geometry.parquet"
PPPR_PARQUET = CACHE_DIR / "player_pppr.parquet"
PCR_PARQUET = CACHE_DIR / "player_pcr.parquet"
MATCHUPS_PARQUET = CACHE_DIR / "matchups.parquet"
PLAYER_PLAY_PARQUET = CACHE_DIR / "player_play.parquet"
META_JSON = CACHE_DIR / "meta.json"

# ---------------------------------------------------------------------------
# Field geometry (yards). Standard NFL field in tracking coords.
# x in [0, 120] (incl. two 10-yd end zones); y in [0, 53.3].
# ---------------------------------------------------------------------------
FIELD_LENGTH = 120.0
FIELD_WIDTH = 160.0 / 3.0  # 53.333...
TRACKING_HZ = 10.0         # frames per second
DT = 1.0 / TRACKING_HZ

# ---------------------------------------------------------------------------
# Role / event vocabulary (verified against the data)
# ---------------------------------------------------------------------------
ROLE_QB = "Pass"
ROLE_BLOCK = "Pass Block"
ROLE_RUSH = "Pass Rush"
ROLE_ROUTE = "Pass Route"
ROLE_COVER = "Coverage"

SNAP_EVENTS = ("ball_snap", "autoevent_ballsnap")
PASS_EVENTS = ("pass_forward", "autoevent_passforward", "pass_shovel")
SACK_EVENTS = ("qb_sack", "qb_strip_sack")
SCRAMBLE_EVENTS = ("run",)
# events that help interpret the end of a play
END_HINT_EVENTS = PASS_EVENTS + SACK_EVENTS + (
    "pass_outcome_incomplete", "pass_outcome_caught", "pass_outcome_touchdown",
    "pass_outcome_interception", "fumble", "qb_spike",
)

OFFENSE_POS = {"T", "G", "C", "TE", "RB", "FB", "QB"}
DEFENSE_POS = {"DE", "DT", "NT", "OLB", "ILB", "MLB", "LB", "CB", "FS", "SS", "DB"}


@dataclass
class PISConfig:
    """Tunable parameters for the Pocket Integrity Score.

    Defaults match docs/METHODOLOGY.md. The app and sensitivity analysis can
    override any of these.
    """
    # --- per-frame normalisation scales ---
    d_clean: float = 3.5        # yd; QB->nearest rusher distance that scores 1.0
    n_max: float = 3.0          # rushers within proximity radius that scores 0.0
    proximity_radius: float = 2.0  # yd; "near the QB" radius
    c_max: float = 6.0          # yd/s; closing speed that scores 0.0
    d_depth: float = 3.0        # yd; depth cushion that scores 1.0
    hull_blocker_radius: float = 4.0  # yd; blockers within this of QB form the cup

    # --- play-level component weights (sum to 1.0) ---
    w_clean: float = 0.30       # sustained clean space
    w_press: float = 0.20       # pressure load
    w_collapse: float = 0.20    # collapse resistance
    w_closing: float = 0.15     # closing control
    w_final: float = 0.15       # last-second integrity

    final_window_s: float = 0.5  # seconds before t_end for S_final

    # --- outcome adjustment (bounded, small vs geometry) ---
    adj_sack: float = -12.0
    adj_hit: float = -6.0
    adj_hurry: float = -4.0
    adj_scramble: float = -3.0
    adj_clean: float = 2.0

    # --- eligibility ---
    min_window_frames: int = 5          # < 0.5 s window => unscorable
    max_missing_frac: float = 0.40      # > 40% unusable frames => unscorable

    # --- player rating penalties / bonuses ---
    k_hit: float = 6.0
    k_hurry: float = 4.0
    k_sack: float = 12.0
    k_beat: float = 3.0
    m_hit: float = 6.0
    m_hurry: float = 4.0
    m_sack: float = 12.0
    m_prox: float = 20.0        # scales tracking proximity_impact into points

    min_snaps_offense: int = 50
    min_snaps_defense: int = 50

    def weights(self) -> dict:
        return {
            "clean": self.w_clean, "press": self.w_press,
            "collapse": self.w_collapse, "closing": self.w_closing,
            "final": self.w_final,
        }

    def as_dict(self) -> dict:
        return asdict(self)


DEFAULT = PISConfig()
