"""Run the REAL game API with cognee STUBBED — no API key, no network.

Use this to play/test the whole game UI instantly:
  * deterministic flow (case generation, schedule, clues, contradictions,
    scoring) is REAL,
  * memory writes + recall + forget are stubbed (instant — no quota),
  * recall returns nothing, so NPC lines come from templated fallbacks
    (badged SCRIPT in the UI).

For live cognee recall + generated lines, set COGNEE_SERVICE_URL+COGNEE_API_KEY
(Cognee Cloud) and run uvicorn normally (see README.md).

    .venv/bin/python devserver_stub.py        # serves on http://127.0.0.1:8000
"""
import os
import sys
from types import ModuleType, SimpleNamespace
from unittest.mock import AsyncMock

# The stub promises "no API key, no network" — force the cognee path even if
# the developer's .env enables the Bedrock backend.
os.environ["LLM_BACKEND"] = ""
os.environ.pop("AWS_BEARER_TOKEN_BEDROCK", None)

# --- Stub cognee BEFORE importing config (config imports cognee at load) ----- #
_c = ModuleType("cognee")
_c.config = SimpleNamespace(
    system_root_directory=lambda *a, **k: None,
    data_root_directory=lambda *a, **k: None,
)
_c.prune = SimpleNamespace(prune_data=AsyncMock(), prune_system=AsyncMock())
_c.remember = AsyncMock(return_value=None)
_c.forget = AsyncMock(return_value=None)
_c.serve = AsyncMock(return_value=None)
_c.recall = AsyncMock(return_value=[])  # empty -> templated fallback lines
sys.modules["cognee"] = _c

import uvicorn  # noqa: E402
import api  # noqa: E402

if __name__ == "__main__":
    print("Stub game server on http://127.0.0.1:8000  (Cognee + LLM stubbed)")
    uvicorn.run(api.app, host="127.0.0.1", port=8000, log_level="warning")
