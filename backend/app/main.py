#!/usr/bin/env python3
"""
Alchemux - URL to MP3 Converter CLI (dev convenience entry).

When run as __main__ (e.g. python backend/app/main.py), adds backend to path
and delegates to the package-native entrypoint. Installed console scripts
use app.entrypoint:main directly and do not load this file.
"""

import sys
from pathlib import Path

if __name__ == "__main__":
    # Dev convenience: run from repo root without installing the package
    backend = Path(__file__).resolve().parent.parent
    if str(backend) not in sys.path:
        sys.path.insert(0, str(backend))
    from app.entrypoint import main

    main()
