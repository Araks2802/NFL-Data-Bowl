"""Plain-English metric definitions for tooltips and the How-PIS-works panel."""

PIS = (
    "Pocket Integrity Score (0-100). How well the offense preserved a usable "
    "throwing pocket from snap to the throw or sack. High = clean, sustained "
    "pocket; low = the pocket collapsed or the QB was pressured. It is driven "
    "by tracking geometry (QB space, pressure, collapse) and only lightly "
    "nudged by the recorded outcome."
)

PPPR = (
    "Player Pocket Preservation Rating (0-100). For blockers (and chipping "
    "backs/TEs): how much the player contributed to clean pockets, after "
    "subtracting the hits, hurries and sacks PFF credited them with allowing. "
    "Snap-weighted average, so consistency matters more than any single play."
)

PCR = (
    "Pressure Creation Rating (0-100). For pass rushers: how consistently the "
    "player compressed the pocket, closed on the QB, and produced hits, "
    "hurries and sacks. Snap-weighted, rewarding steady pressure over "
    "one-off splash plays."
)

COMPONENTS = {
    "Clean-space sustain (30%)": "Average distance kept between the QB and the "
        "nearest rusher across the play. More space, higher score.",
    "Pressure load (20%)": "How few rushers got within ~2 yards of the QB over "
        "the play. Fewer bodies in the QB's lap, higher score.",
    "Collapse resistance (20%)": "How well the pocket held its shape and depth "
        "instead of shrinking toward the QB from snap to throw.",
    "Closing control (15%)": "How well blockers slowed rushers' closing speed "
        "toward the QB.",
    "Last-second integrity (15%)": "Cleanliness in the final half-second before "
        "the throw or sack: the moment that decides the play.",
}

OUTCOME_ADJ = (
    "After the geometry score, a small bounded adjustment is applied: sack -12, "
    "QB hit -6, hurry -4, scramble -3, clean throw +2. This calibrates the "
    "score to what actually happened without turning PIS into a yes/no sack flag."
)

SUPPORTING = {
    "avg_pis": "Average Pocket Integrity Score across the player's plays.",
    "pressures_allowed": "PFF-credited hits + hurries + sacks allowed by this blocker.",
    "sacks_allowed": "PFF-credited sacks allowed.",
    "beaten": "Plays where PFF marked the blocker beaten by his defender.",
    "pressure_rate_allowed": "Share of the player's blocking snaps with a pressure allowed.",
    "pressures": "PFF-credited hits + hurries + sacks produced by this rusher.",
    "pressure_rate": "Share of the player's rush snaps that produced a pressure.",
    "avg_prox_impact": "Tracking measure (0-1) of how close/fast the rusher got to the QB.",
    "avg_min_dist": "Average of the closest the rusher got to the QB each play (yd).",
    "bootstrap_sd": "Uncertainty band: bootstrap standard deviation of the rating. "
        "Wider = less certain (usually fewer snaps).",
    "time_to_pressure_s": "Seconds from snap until a rusher first got within the "
        "pressure radius of the QB (blank = never pressured).",
}

LIMITATIONS = (
    "PIS is a top-down 2-D proxy. It cannot see hand-fighting, leverage or exact "
    "contact, and 8 weeks is a modest sample, so low-snap ratings carry wide "
    "uncertainty. Attribution leans on PFF assignments; where those are missing "
    "the contribution is flagged uncertain. Treat PIS as a complement to film "
    "and PFF grades, not a replacement."
)
