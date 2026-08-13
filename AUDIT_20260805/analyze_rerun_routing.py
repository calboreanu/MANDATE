#!/usr/bin/env python3
"""Compatibility wrapper for the strict V3 rerun routing analyzer."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CODE = ROOT / "code"
if str(CODE) not in sys.path:
    sys.path.insert(0, str(CODE))

from apparatus.rerun_analysis import main


if __name__ == "__main__":
    raise SystemExit(main())
