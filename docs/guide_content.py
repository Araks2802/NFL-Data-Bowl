"""Content for the beginner's guide PDF.

A structured list of blocks. Each block is a tuple (kind, payload):
  ("h1", str)            top-level section title (new page)
  ("h2", str)            sub-heading
  ("h3", str)            minor heading
  ("p", str)             paragraph (supports **bold** inline)
  ("bullet", [str])      bullet list
  ("note", str)          highlighted callout box
  ("table", (headers, rows))  simple table
  ("spacer", float)      vertical gap in mm

Everything a beginner sees anywhere in the app is explained here.
"""

CONTENT = [
    # ===================================================================
    ("cover", {
        "title": "Pocket Integrity Score",
        "subtitle": "The Complete Beginner's Guide",
        "tagline": "Everything in this app, explained in plain English:\n"
                   "football basics, every metric, every screen, and the data behind it.",
    }),

    # ===================================================================
    ("h1", "1. Start here: what this app is about"),
    ("p", "This app studies one specific part of American football: **pass "
          "protection**. When a team wants to throw the ball, the quarterback "
          "(QB) stands behind a wall of blockers. The defense tries to break "
          "through that wall and reach the QB before he can throw. The "
          "protected space around the QB is called the **pocket**."),
    ("p", "The whole app is built to answer one question a real coach or scout "
          "would ask:"),
    ("note", "Which blockers build the cleanest, longest-lasting pockets, and "
             "which defenders break pockets down most consistently?"),
    ("p", "To answer it, we invented a score called the **Pocket Integrity "
          "Score (PIS)**. Think of it as a 0-to-100 grade for how safe the "
          "quarterback was on each pass play. 100 means a perfectly clean, "
          "roomy pocket; a low number means the QB was crowded, chased, or "
          "sacked."),
    ("p", "You do not need to know any football to use this guide. We will "
          "build up every term from scratch."),

    # ===================================================================
    ("h1", "2. Football basics (zero assumed knowledge)"),
    ("h2", "The field"),
    ("p", "A football field is 120 yards long and about 53 yards wide. The "
          "middle 100 yards is the playing area; the two 10-yard strips at "
          "each end are the **end zones** (where you score). In this app we "
          "always flip plays so the offense is attacking **left to right**, so "
          "every play looks the same direction no matter which way it really "
          "went."),

    ("h2", "The two teams on a passing play"),
    ("p", "On every play there are two sides:"),
    ("bullet", [
        "**Offense** - the team with the ball, trying to move forward and score.",
        "**Defense** - the team trying to stop them.",
    ]),
    ("p", "A **pass play** is simply a play where the offense tries to throw "
          "the ball to a teammate rather than run with it."),

    ("h2", "Offensive positions (the people in gold in the app)"),
    ("table", (
        ["Short code", "Position", "What they do"],
        [
            ["QB", "Quarterback", "Throws the ball. The player we are protecting."],
            ["T", "Tackle", "Blocker on the far left/right end of the line. Protects the edges."],
            ["G", "Guard", "Blocker just inside the tackles."],
            ["C", "Center", "Blocker in the middle; snaps (hikes) the ball to the QB."],
            ["TE", "Tight End", "Hybrid: sometimes blocks, sometimes catches passes."],
            ["RB", "Running Back", "Usually runs/catches, but often stays in to block."],
            ["FB", "Fullback", "A heavier back who mostly blocks."],
        ],
    )),
    ("p", "The five main blockers (two tackles, two guards, one center) are "
          "together called the **offensive line** or **O-line**. Left-to-right "
          "they line up as **LT, LG, C, RG, RT**."),

    ("h2", "Defensive positions (the people in red in the app)"),
    ("table", (
        ["Short code", "Position", "What they do"],
        [
            ["DE", "Defensive End", "Rushes the QB from the edge of the line."],
            ["DT", "Defensive Tackle", "Rushes the QB up the middle (interior)."],
            ["NT", "Nose Tackle", "A DT lined up right over the center."],
            ["OLB", "Outside Linebacker", "Versatile; often rushes off the edge."],
            ["ILB / MLB", "Inside / Middle Linebacker", "Plays behind the line; rushes or covers."],
            ["CB", "Cornerback", "Covers receivers, usually out wide."],
            ["S (FS/SS)", "Safety (Free/Strong)", "Covers deep, the last line of defense."],
        ],
    )),
    ("p", "Defenders who try to reach the QB are called **pass rushers**. "
          "Defenders who guard receivers instead are in **coverage**."),

    ("h2", "The pocket, step by step"),
    ("bullet", [
        "The ball is **snapped** (hiked) to the QB - the play begins.",
        "The QB drops back a few steps; the blockers form a U-shaped wall in "
        "front and around him. That U-shape is the **pocket**.",
        "Pass rushers try to get around or through the blockers.",
        "The play ends when the QB **throws** (releases) the ball, is "
        "**sacked** (tackled before throwing), or **scrambles** (runs).",
    ]),
    ("note", "A clean pocket gives the QB time and space to throw accurately. "
             "A collapsing pocket forces rushed, inaccurate throws, sacks, or "
             "scrambles. PIS measures exactly this."),

    # ===================================================================
    ("h1", "3. Key events on a play"),
    ("p", "The tracking data labels special moments. The app uses these to "
          "know when to start and stop measuring the pocket:"),
    ("table", (
        ["Event", "Plain meaning"],
        [
            ["Snap (ball_snap)", "The ball is hiked; the play starts. PIS starts measuring here."],
            ["Pass forward", "The QB releases the ball. On a normal pass, PIS stops here."],
            ["QB sack", "The QB was tackled before throwing. PIS stops here on a sack."],
            ["Scramble (run)", "The QB gave up on throwing and ran. PIS stops here on a scramble."],
            ["Play action", "A fake handoff to fool the defense before passing."],
            ["Pass arrived / caught / incomplete", "What happened to the thrown ball."],
        ],
    )),
    ("p", "The window from snap to the throw/sack/scramble is the only part of "
          "the play PIS cares about - that is when protection matters."),

    # ===================================================================
    ("h1", "4. Pass-play outcomes (the 'result' filter)"),
    ("p", "Every pass play ends in one of five recorded results. You will see "
          "these codes in the Play Explorer and filters:"),
    ("table", (
        ["Code", "Meaning", "Good for the offense?"],
        [
            ["C", "Complete pass (caught by a teammate)", "Yes"],
            ["I", "Incomplete pass (hit the ground)", "No"],
            ["S", "Sack (QB tackled before throwing)", "Very bad"],
            ["R", "Scramble (QB ran instead of throwing)", "Mixed"],
            ["IN", "Interception (caught by the defense)", "Worst"],
        ],
    )),
    ("note", "Important idea: a completion can still have TERRIBLE protection "
             "(the QB got lucky), and a sack can happen behind GOOD protection "
             "(nobody was open, so the QB held the ball too long). That is why "
             "we measure the pocket itself, not just the result."),

    # ===================================================================
    ("h1", "5. Formations (how the offense lines up)"),
    ("p", "A **formation** is the shape the offense makes before the snap. It "
          "hints at whether they will run or pass and how much protection the "
          "QB has. These are the ones in the app:"),
    ("table", (
        ["Formation", "What it looks like"],
        [
            ["SHOTGUN", "QB stands ~5 yards back to see the field better. The most common passing formation."],
            ["EMPTY", "No running backs behind the QB - everyone is out as a receiver. Fewer blockers, riskier protection."],
            ["SINGLEBACK", "One running back behind the QB. Balanced run/pass look."],
            ["I_FORM", "Two backs lined up in a row behind the QB (an 'I' shape). A traditional, run-friendly look."],
            ["PISTOL", "A shorter shotgun with a back directly behind the QB."],
            ["JUMBO", "Extra big blockers in, almost no receivers. Maximum protection, usually short-yardage."],
            ["WILDCAT", "A trick look where a non-QB takes the snap. Rare."],
        ],
    )),

    # ===================================================================
    ("h1", "6. Dropback types (how the QB sets up to throw)"),
    ("table", (
        ["Dropback type", "Plain meaning"],
        [
            ["TRADITIONAL", "QB drops straight back and throws from the pocket. The standard."],
            ["SCRAMBLE", "The pocket broke down, so the QB took off running."],
            ["DESIGNED_ROLLOUT_LEFT/RIGHT", "The play was DESIGNED for the QB to move sideways to one side before throwing."],
            ["SCRAMBLE_ROLLOUT_LEFT/RIGHT", "The QB improvised a run to the side under pressure."],
            ["DESIGNED_RUN", "A planned QB run (not really a pass)."],
            ["UNKNOWN", "The data could not classify it."],
        ],
    )),
    ("p", "Rollouts and scrambles move the QB out of the normal pocket, so PIS "
          "handles them a little differently (it credits a QB who escapes "
          "trouble rather than blaming the pocket)."),

    # ===================================================================
    ("h1", "7. Pass coverages (how the defense guards receivers)"),
    ("p", "**Coverage** is the defense's plan for guarding the receivers while "
          "(or instead of) rushing the QB. You do not need these to understand "
          "PIS, but they appear in filters, so here is the plain version. The "
          "number usually tells you how many defenders are guarding the deep "
          "part of the field."),
    ("table", (
        ["Coverage", "Simple idea"],
        [
            ["Cover-0", "Everyone guards a man, NOBODY deep. All-out aggression, often a blitz. Hardest on protection."],
            ["Cover-1", "One deep safety; everyone else guards a man."],
            ["Cover-2", "Two deep safeties split the deep field."],
            ["Cover-3", "Three defenders split the deep field. Very common."],
            ["Cover-6 / Quarters", "The deep field split into quarters by 2-4 defenders."],
            ["2-Man", "Two deep safeties, man coverage underneath."],
            ["Bracket", "Two defenders double-team one dangerous receiver."],
            ["Prevent", "Soft, deep coverage to stop a long play at the end of a half."],
            ["Red Zone / Goal Line", "Special packages near the end zone."],
        ],
    )),
    ("p", "**Man coverage** means a defender follows one specific receiver. "
          "**Zone coverage** means a defender guards an area of the field. "
          "**Blitz** means the defense sends extra rushers at the QB - great "
          "for pressure, risky because fewer defenders are left in coverage."),

    # ===================================================================
    ("h1", "8. The star of the show: Pocket Integrity Score (PIS)"),
    ("p", "**PIS is a 0-100 grade of how well the offense protected the QB on a "
          "single pass play.** Higher is better protection."),
    ("h3", "How to read a PIS number"),
    ("table", (
        ["PIS range", "What it means", "Colour in app"],
        [
            ["85 - 100", "Pristine pocket; QB had all day", "Green"],
            ["70 - 85", "Solid protection", "Light green"],
            ["55 - 70", "Shaky; pressure was building", "Yellow"],
            ["40 - 55", "Poor; QB under real duress", "Orange"],
            ["0 - 40", "Pocket collapsed; sack or heavy pressure", "Red"],
        ],
    )),
    ("h3", "What goes into the score"),
    ("p", "PIS blends five things we measure every tenth of a second from the "
          "player tracking data, each phrased as 'bigger is better':"),
    ("table", (
        ["Ingredient (weight)", "Plain-English question it answers"],
        [
            ["Clean-space sustain (30%)", "On average, how much open space did the QB have from the nearest rusher?"],
            ["Pressure load (20%)", "How few rushers got right up in the QB's face?"],
            ["Collapse resistance (20%)", "Did the pocket keep its size and depth, or shrink toward the QB?"],
            ["Closing control (15%)", "How well did blockers slow down rushers charging at the QB?"],
            ["Last-second integrity (15%)", "Was the pocket still clean in the final half-second before the throw?"],
        ],
    )),
    ("p", "Those five combine into a 'geometry score'. Then we nudge it a "
          "little by what actually happened, so the number agrees with reality:"),
    ("table", (
        ["Outcome", "Adjustment to PIS"],
        [
            ["Sack", "-12 points"],
            ["QB was hit", "-6 points"],
            ["Hurry (QB rushed)", "-4 points"],
            ["Scramble", "-3 points"],
            ["Clean throw, no pressure", "+2 points"],
        ],
    )),
    ("note", "The adjustment is small on purpose. PIS is driven mainly by the "
             "tracking geometry, not by the box score. That is what makes it "
             "more honest than just counting sacks."),
    ("p", "If a play is missing too much data to measure fairly, we mark it "
          "'unscorable' and leave it out rather than guessing. About 100% of "
          "plays in this dataset were scorable."),

    # ===================================================================
    ("h1", "9. The two player ratings: PPPR and PCR"),
    ("h2", "PPPR - Player Pocket Preservation Rating (for blockers)"),
    ("p", "A 0-100 rating of how well an **offensive blocker** (tackle, guard, "
          "center, tight end, back) protects the pocket. We take the pocket "
          "quality (PIS) on his plays and subtract penalties for the hits, "
          "hurries and sacks he personally allowed. Higher = better protector. "
          "It is a per-snap average, so a steady, reliable blocker beats one "
          "who has a few great plays and several disasters."),
    ("h2", "PCR - Pressure Creation Rating (for pass rushers)"),
    ("p", "A 0-100 rating of how consistently a **defender** disrupts pockets: "
          "how close and fast he gets to the QB plus the hits, hurries and "
          "sacks he produces. Higher = better rusher. Again it rewards doing it "
          "**consistently**, not one highlight sack."),
    ("note", "Both ratings use a minimum snap count (default 50) so we only "
             "rank players with enough evidence, and each carries an "
             "uncertainty band (the '±' column) - wider means less certain."),

    # ===================================================================
    ("h1", "10. The supporting stats (every column you'll see)"),
    ("h2", "The pressure vocabulary"),
    ("table", (
        ["Term", "Plain meaning"],
        [
            ["Sack", "QB tackled behind the line before throwing. The worst outcome for protection."],
            ["Hit", "A rusher hit the QB as or just after he threw."],
            ["Hurry", "A rusher got close enough to rush/disrupt the throw."],
            ["Pressure", "Any of the above (hit OR hurry OR sack). The catch-all."],
            ["Beaten", "PFF judged that a blocker was clearly beaten by his defender."],
        ],
    )),
    ("p", "For blockers these are 'allowed' (bad for them); for rushers they "
          "are 'created' (good for them). It is the same event seen from the "
          "two sides."),
    ("h2", "Leaderboard & table columns"),
    ("table", (
        ["Column", "What it tells you"],
        [
            ["Snaps", "How many plays the player was involved in. More = more reliable rating."],
            ["Avg PIS", "Average pocket quality on that player's plays."],
            ["Press / Press%", "Pressures (count) and the share of snaps with a pressure."],
            ["Hits / Hur / Sacks", "Counts of each pressure type (allowed or created)."],
            ["Def win% / Rush win%", "In matchups: share of reps the defender/rusher won (got a pressure)."],
            ["ProxImpact", "A 0-1 tracking measure of how close and fast a rusher got to the QB."],
            ["MinDist", "On average, the closest a rusher got to the QB each play, in yards."],
            ["Reps", "In matchups: how many times a specific blocker and rusher faced each other."],
            ["± (bootstrap SD)", "Uncertainty of the rating. Smaller = more confident."],
        ],
    )),

    # ===================================================================
    ("h1", "11. The app, screen by screen"),
    ("h2", "Home"),
    ("p", "The front page: top-line counts, a plain explanation of PIS, a "
          "validation summary (proof the metric is meaningful), and three "
          "ready-made example plays you can open with one click."),
    ("h2", "Play Explorer"),
    ("p", "The heart of the app. Pick a play and watch it animate on a football "
          "field."),
    ("bullet", [
        "**Gold dots** = pass blockers. **Red dots** = pass rushers. "
        "**White dot** = the QB. **Grey dots** = receivers/coverage. "
        "**Brown diamond** = the ball.",
        "**Press Play** or drag the timeline slider to move through the play. "
        "The slider marks the snap and the end of the play.",
        "The shaded shape around the QB is the **pocket**. Watch it shrink when "
        "protection breaks down.",
        "The chart below shows PIS and the QB's open space second-by-second - "
        "you can literally see a collapse happen.",
    ]),
    ("h3", "The layer toggles (left sidebar)"),
    ("table", (
        ["Layer", "What it draws"],
        [
            ["Pocket shape", "The U-shaped protected area around the QB."],
            ["QB clean-space ring", "A circle showing the 'comfortable' space the QB wants."],
            ["Pressure radius", "A small circle; rushers inside it are crowding the QB."],
            ["Player trails", "Short tails showing where each player just came from."],
            ["Velocity arrows", "Arrows showing each player's speed and direction."],
        ],
    )),
    ("h2", "Player Leaderboards"),
    ("p", "Two ranked tables: blockers by PPPR and rushers by PCR. Use the "
          "filters (week, team, position, formation, coverage, dropback, play "
          "action, minimum snaps) to narrow things down. Click a player button "
          "to jump to one of their plays in the Play Explorer."),
    ("h2", "Matchup Inspector"),
    ("p", "Head-to-head battles. Pick an offensive lineman to see which rushers "
          "he faced and how often he held up, or pick a rusher to see which "
          "blockers he beat. 'Win%' is how often the rusher got a pressure in "
          "that matchup. We only trust matchups with a few reps behind them."),
    ("h2", "Team / Unit View"),
    ("p", "The big picture. Rank every team's offensive line (who protects "
          "best) and every defense's front (who pressures best), and see how "
          "pocket quality changes by formation, coverage, down, and play "
          "action, with a plain-English takeaway on each chart."),

    # ===================================================================
    ("h1", "12. Where the numbers come from (the data)"),
    ("p", "Everything is built from the NFL's Big Data Bowl 2023 dataset: the "
          "2021 season, weeks 1-8, 122 games, 8,557 pass plays. Five files feed "
          "the app:"),
    ("table", (
        ["File", "What's in it"],
        [
            ["games", "One row per game: teams, week, date."],
            ["plays", "One row per play: formation, coverage, result, down, etc."],
            ["players", "One row per player: name, position, height, weight."],
            ["pffScoutingData", "Expert PFF grades: each player's role and the pressures they created/allowed, plus who blocked whom."],
            ["tracking", "The GPS-style data: every player's position 10 times per second. This is what powers the animation and PIS."],
        ],
    )),
    ("p", "In the tracking data, the ball is a special row with no player ID. "
          "Players are matched across files by their IDs, and we carefully "
          "handle missing data, duplicate rows, and players running on or off "
          "the screen."),

    # ===================================================================
    ("h1", "13. Honest limitations (what PIS can't see)"),
    ("bullet", [
        "PIS is a **top-down 2-D view**. It cannot see hand-fighting, "
        "leverage, or exactly who touched whom - it complements expert film "
        "and PFF grades, it does not replace them.",
        "**Eight weeks is a small sample.** Ratings for players with few snaps "
        "are uncertain (that is what the '±' band is for).",
        "**Scrambles are the hardest plays to measure** cleanly, so those are "
        "flagged.",
        "When the data does not say which blocker was assigned to which rusher, "
        "we mark the matchup 'uncertain' instead of guessing.",
    ]),
    ("note", "The golden rule: PIS tells you how clean the pocket was, which is "
             "strongly linked to pressure - but a link is not proof of cause. "
             "Use it as a smart starting point, then watch the play."),

    ("h1", "14. One-page cheat sheet"),
    ("table", (
        ["If you see...", "Think..."],
        [
            ["PIS 90", "Great protection, QB was comfortable."],
            ["PIS 40", "Pocket collapsed, QB in trouble."],
            ["High PPPR", "A reliable, high-quality blocker."],
            ["High PCR", "A consistent pressure-creating rusher."],
            ["Gold dot", "A blocker (offense)."],
            ["Red dot", "A pass rusher (defense)."],
            ["White dot", "The quarterback."],
            ["'Sack' (S)", "QB tackled before throwing - worst protection outcome."],
            ["'Pressure'", "A hit, hurry, or sack - any disruption of the QB."],
            ["Cover-0 / blitz", "Aggressive defense; expect pressure."],
            ["Shotgun / Empty", "Passing looks; Empty has fewer blockers."],
            ["Wide '±' band", "Rating is uncertain (few snaps)."],
        ],
    )),
    ("p", "That's everything. Keep this guide open next to the app, and within "
          "a few plays the terms will feel natural. Enjoy exploring the "
          "pocket!"),
]
