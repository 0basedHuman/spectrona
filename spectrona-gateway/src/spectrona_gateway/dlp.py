"""Local DLP wrappers over Spectrona's shared secret detector."""

try:
    from spectrona_detection.secrets import findings_count, redact_text, scan_text
except ImportError:  # pragma: no cover - exercised by component-only CLI shims
    import sys
    from pathlib import Path

    for parent in Path(__file__).resolve().parents:
        shared_src = parent / "spectrona-detection" / "src"
        if shared_src.exists():
            sys.path.insert(0, str(shared_src))
            break
    from spectrona_detection.secrets import findings_count, redact_text, scan_text

__all__ = ["findings_count", "redact_text", "scan_text"]
