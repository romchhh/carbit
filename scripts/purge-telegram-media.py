#!/usr/bin/env python3
"""Локальний wrapper — делегує в backend/scripts/purge_telegram_media.py."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "backend" / "scripts" / "purge_telegram_media.py"

env = os.environ.copy()
env["PYTHONPATH"] = f"{ROOT / 'backend'}:{ROOT}"

raise SystemExit(subprocess.call([sys.executable, str(TARGET), *sys.argv[1:]], env=env, cwd=ROOT))
