#!/usr/bin/env python3
"""LaserCtrl unified entrypoint.

Run from Code/Python/LaserCtrl:

    python laser_app.py
"""

from __future__ import annotations

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from app_shell import main


if __name__ == "__main__":
    main()
