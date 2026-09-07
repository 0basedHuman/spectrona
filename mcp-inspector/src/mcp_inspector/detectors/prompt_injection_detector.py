import re
from typing import Iterable, Optional

from ..models import Finding


_RISK_PATTERNS = [
    ("ignore previous instructions", re.compile(r"\bignore\b.{0,40}\b(previous|prior|above|system|developer|user)\b.{0,30}\binstructions?\b", re.I)),
    ("override safety policy", re.compile(r"\boverride\b.{0,40}\b(system|developer|safety|security|policy|guardrails?)\b", re.I)),
    ("embedded system prompt", re.compile(r"\b(system|developer)\s*:", re.I)),
    ("assistant role instruction", re.compile(r"\bas an ai\b|\bas the assistant\b", re.I)),
    ("no approval required", re.compile(r"\b(do not|don't|never)\b.{0,30}\b(ask|request)\b.{0,30}\b(approval|permission|confirmation)\b", re.I)),
    ("always execute directive", re.compile(r"\balways\b.{0,40}\b(execute|run|approve|obey|comply|follow)\b", re.I)),
    ("never refuse directive", re.compile(r"\bnever\b.{0,40}\b(refuse|warn|mention|disclose|ask)\b", re.I)),
    ("bypass controls directive", re.compile(r"\bbypass\b.{0,40}\b(security|policy|safety|guardrails?|checks?)\b", re.I)),
]


def detect(servers: dict, source_file: str) -> list[Finding]:
    """Detect prompt-injection-prone MCP tool or server descriptions."""
    findings = []
    for server_name, config in servers.items():
        if not isinstance(config, dict):
            continue

        matches = []
        for location, text in _description_fields(config):
            label = _risk_label(text)
            if label:
                matches.append((location, label))

        if not matches:
            continue

        evidence_items = [
            f"{location} matched risky directive pattern: {label}"
            for location, label in matches[:5]
        ]
        if len(matches) > 5:
            evidence_items.append(f"{len(matches) - 5} additional risky description fields")

        findings.append(Finding(
            id="MCP_TOOL_PROMPT_INJECTION_RISK",
            title="MCP tool description contains prompt-injection-prone text",
            severity="medium",
            category="prompt-injection",
            source=f"{source_file} → mcpServers.{server_name}",
            evidence="; ".join(evidence_items),
            why_it_matters=(
                "Tool descriptions are visible to the model. Directive-style text can make "
                "the model treat a tool description as an instruction instead of neutral metadata."
            ),
            recommended_fix="Rewrite MCP tool descriptions as neutral, factual capability statements.",
            confidence="medium",
        ))
    return findings


def _description_fields(config: dict) -> Iterable[tuple[str, str]]:
    server_description = config.get("description")
    if isinstance(server_description, str):
        yield "description", server_description

    yield from _tool_descriptions(config.get("tools"), "tools")
    yield from _tool_descriptions(config.get("toolDescriptions"), "toolDescriptions")


def _tool_descriptions(value: object, base_path: str) -> Iterable[tuple[str, str]]:
    if isinstance(value, list):
        for index, item in enumerate(value):
            path = f"{base_path}[{index}]"
            description = _item_description(item)
            if description:
                yield f"{path}.description", description
    elif isinstance(value, dict):
        for name, item in value.items():
            path = f"{base_path}.{name}"
            description = _item_description(item)
            if description:
                yield f"{path}.description", description


def _item_description(item: object) -> Optional[str]:
    if isinstance(item, str):
        return item
    if isinstance(item, dict):
        description = item.get("description")
        if isinstance(description, str):
            return description
    return None


def _risk_label(text: str) -> Optional[str]:
    for label, pattern in _RISK_PATTERNS:
        if pattern.search(text):
            return label
    return None
