"""Run every Streamlit page headless via AppTest and report any exceptions."""
from __future__ import annotations

import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from streamlit.testing.v1 import AppTest

PAGES = [
    "app/Home.py",
    "app/pages/1_Play_Explorer.py",
    "app/pages/2_Leaderboards.py",
    "app/pages/3_Matchup_Inspector.py",
    "app/pages/4_Team_Unit_View.py",
]

all_ok = True
for p in PAGES:
    try:
        at = AppTest.from_file(str(ROOT / p), default_timeout=120)
        at.run()
        excs = list(at.exception)
        if excs:
            all_ok = False
            print(f"[FAIL] {p}: {len(excs)} exception(s)")
            for e in excs:
                print("       ", repr(e.value)[:300])
        else:
            print(f"[ OK ] {p}: no exceptions "
                  f"(markdowns={len(at.markdown)}, dfs={len(at.dataframe)})")
    except Exception as e:  # harness-level failure
        all_ok = False
        print(f"[ERR ] {p}: {type(e).__name__}: {e}")

print("SCRIPT_OK" if all_ok else "SCRIPT_HAS_FAILURES")
