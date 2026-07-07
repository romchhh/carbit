from __future__ import annotations

import sys
from pathlib import Path

from app.core.config import ROOT_DIR

_BOOTSTRAPPED = False


def ensure_parser_path() -> Path:
    global _BOOTSTRAPPED
    root = ROOT_DIR.resolve()
    path = str(root)
    if path not in sys.path:
        sys.path.insert(0, path)
    _BOOTSTRAPPED = True
    return root
