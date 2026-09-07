from dataclasses import dataclass
from typing import Literal

Severity = Literal["critical", "high", "medium", "low"]
Confidence = Literal["high", "medium", "low"]


@dataclass
class Finding:
    id: str
    title: str
    severity: Severity
    category: str
    source: str
    evidence: str
    why_it_matters: str
    recommended_fix: str
    confidence: Confidence
