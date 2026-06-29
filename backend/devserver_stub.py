"""Run the REAL game API with cognee STUBBED — no API key, no heavy install.

Use this to play/test the whole game UI instantly:
  * deterministic flow (flags, relationships, branching, ledger, endings) is REAL,
  * memory writes + recall are stubbed (instant — no quota, no retry backoff),
  * recall returns nothing, so NPC lines come from the authored fallbacks
    (badged TEMPLATE in the UI).

This is NOT the real memory path — for live cognee recall + generated lines, install
requirements.txt and either set COGNEE_SERVICE_URL+COGNEE_API_KEY (Cognee Cloud) or a
Gemini key (local), then run uvicorn normally (see README.md).

    .venv/bin/python devserver_stub.py        # serves on http://127.0.0.1:8000
"""
import sys
from types import ModuleType, SimpleNamespace
from unittest.mock import AsyncMock

# --- Stub cognee BEFORE importing config (config imports cognee at load) ----- #
_c = ModuleType("cognee")
_c.config = SimpleNamespace(
    system_root_directory=lambda *a, **k: None,
    data_root_directory=lambda *a, **k: None,
)
_c.prune = SimpleNamespace(prune_data=AsyncMock(), prune_system=AsyncMock())
_c.remember = AsyncMock(return_value=None)
_c.serve = AsyncMock(return_value=None)
_c.recall = AsyncMock(return_value=[])  # empty -> authored fallback lines
sys.modules["cognee"] = _c

import uvicorn  # noqa: E402
import api  # noqa: E402

if __name__ == "__main__":
    print("Stub game server on http://127.0.0.1:8000  (Cognee + LLM stubbed)")
    uvicorn.run(api.app, host="127.0.0.1", port=8000, log_level="warning")
