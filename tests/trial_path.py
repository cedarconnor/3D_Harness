"""Make dcc_harness_trials importable from a checkout without shadowing an installed dcc_harness.

Appended, not inserted: when the suite runs against an installed wheel, dcc_harness must still resolve there.
"""
from pathlib import Path
import sys

ROOT = str(Path(__file__).resolve().parents[1])
if ROOT not in sys.path:
    sys.path.append(ROOT)
