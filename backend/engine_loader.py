"""Import the real engine (engine/chalk_engine) or, if it is not there yet,
the stub in backend/_stub_engine.py. Everything else imports `engine` from here.

Repo layout: <root>/engine/chalk_engine and <root>/backend/engine_loader.py.
On Modal the same layout is copied to /root/chalk-talk, so one sys.path entry works.
CHALK_ENGINE=stub forces the stub (backend tests in isolation).
"""

import logging
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
log = logging.getLogger("chalk.engine")

if str(ROOT / "engine") not in sys.path:
    sys.path.insert(0, str(ROOT / "engine"))

try:
    if os.environ.get("CHALK_ENGINE") == "stub":
        raise ImportError("CHALK_ENGINE=stub")
    import chalk_engine as engine
    ENGINE_NAME = "chalk_engine"
except ImportError as exc:
    log.warning("chalk_engine not importable (%s); using backend/_stub_engine.py", exc)
    from backend import _stub_engine as engine
    ENGINE_NAME = "stub"
