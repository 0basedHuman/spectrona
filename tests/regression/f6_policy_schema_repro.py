#!/usr/bin/env python3
"""Regression for F6: invalid policies fail at load time."""

from policy_engine import load_policy_text


def main() -> int:
    _assert_load_error(
        "version: 1\n"
        "default_action: allow\n"
        "rules:\n"
        "  - id: t\n"
        "    action: deny\n",
        "non-empty match",
    )
    _assert_load_error(
        "version: 1\n"
        "default_action: allow\n"
        "rules:\n"
        "  - id: s\n"
        "    action: deny\n"
        "    match:\n"
        "      shel_risk: true\n",
        "Unknown match key",
    )
    load_policy_text(
        "version: 1\n"
        "default_action: allow\n"
        "rules:\n"
        "  - id: valid-shell-deny\n"
        "    action: deny\n"
        "    match:\n"
        "      shell_risk: true\n"
    )
    print("f6 policy schema regression passed")
    return 0


def _assert_load_error(text: str, expected_fragment: str) -> None:
    try:
        load_policy_text(text)
    except ValueError as exc:
        assert expected_fragment in str(exc), str(exc)
        return
    raise AssertionError("policy loaded but should have failed validation")


if __name__ == "__main__":
    raise SystemExit(main())
