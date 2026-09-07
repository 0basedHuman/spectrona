import json
import sys
from pathlib import Path


def tail(n: int = 20) -> None:
    log = Path.home() / ".spectrona" / "logs" / "audit.jsonl"
    if not log.exists():
        print("No audit log found. Start the gateway and make some requests.")
        return

    lines = log.read_text().splitlines()
    for line in lines[-n:]:
        try:
            print(json.dumps(json.loads(line), indent=2))
        except Exception:
            print(line)
