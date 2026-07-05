"""Loads .env and configures cognee.

Import this module BEFORE doing anything with cognee so provider/key env vars are
visible to LiteLLM and the on-disk location is deterministic.

Two modes (see .env.example):
  * local  — default; cognee runs in-process against pinned on-disk stores using
             the LLM_API_KEY (Gemini) for inference.
  * cloud  — if COGNEE_SERVICE_URL + COGNEE_API_KEY are set, memory.ensure_connected()
             calls cognee.serve() so remember/recall route to your managed tenant and
             inference is billed to Cognee credits (no separate LLM key needed). In
             cloud mode we skip pinning local dirs — the cloud owns storage.
"""
import os
import pathlib
from dotenv import load_dotenv

_HERE = pathlib.Path(__file__).resolve().parent

# Load env vars (LLM_*/EMBEDDING_*/COGNEE_*) before importing cognee.
load_dotenv(_HERE / ".env")

# cognee runs a blocking 30s LLM reachability pre-flight before every pipeline
# (add/cognify). On a flaky link that stalls startup; the real calls still run
# (and fall back on error), so skip the probe unless explicitly re-enabled.
os.environ.setdefault("COGNEE_SKIP_CONNECTION_TEST", "true")

import cognee  # noqa: E402  (must come after load_dotenv)

CLOUD_MODE = bool(os.environ.get("COGNEE_SERVICE_URL") and os.environ.get("COGNEE_API_KEY"))

if not CLOUD_MODE:
    # Pin cognee's local stores inside backend/ so we know exactly what to wipe.
    cognee.config.system_root_directory(str(_HERE / ".cognee_system"))
    cognee.config.data_root_directory(str(_HERE / ".cognee_data"))
