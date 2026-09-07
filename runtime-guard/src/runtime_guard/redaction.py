try:
    from spectrona_detection.secrets import findings_count, redact_json, redact_text
except ImportError:  # pragma: no cover - exercised by component-only CLI shims
    import sys
    from pathlib import Path

    for parent in Path(__file__).resolve().parents:
        shared_src = parent / "spectrona-detection" / "src"
        if shared_src.exists():
            sys.path.insert(0, str(shared_src))
            break
    from spectrona_detection.secrets import findings_count, redact_json, redact_text

__all__ = ["findings_count", "redact_json", "redact_text"]
