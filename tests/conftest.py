import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

for relative in (
    "mcp-inspector/src",
    "policy-engine/src",
    "runtime-guard/src",
    "spectrona-gateway/src",
    "spectrona-cli/src",
):
    path = str(ROOT / relative)
    if path not in sys.path:
        sys.path.insert(0, path)
