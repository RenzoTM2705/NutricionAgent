"""Entry point para el ejecutable de NutricionAgent.

PyInstaller empaqueta este archivo como ejecutable. En desarrollo se
puede ejecutar con `python run.py`, pero el modo normal es `python -m app.main`.
"""

from __future__ import annotations

import sys

from app.main import main

if __name__ == "__main__":
    sys.exit(main())