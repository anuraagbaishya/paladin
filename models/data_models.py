from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional


@dataclass
class ScanResult:
    repo: str
    scan_result: Dict[str, Any]  # SARIF is stored as a generic dict
    timestamp: int = field(
        default_factory=lambda: int(datetime.now(timezone.utc).timestamp())
    )


@dataclass
class RepoInfo:
    repo: str
    stars: int
    forks: int


@dataclass
class Cwe:
    id: str
    title: str


@dataclass
class VulnReport:
    package: str
    repo: Optional[str]
    ecosystem: str  # TODO: make this enum
    title: str
    ghsa: str
    cve: Optional[str]
    cwe: Optional[Cwe]
    stars: Optional[int]
    forks: Optional[int]
    severity: str  # TODO: make this enum
    cvss_score: Optional[float]
    cvss_vector: Optional[str]


@dataclass
class FindingForReview:
    rule_id: str
    snippet: str
    description: str


@dataclass
class LocationFromSarif:
    filepath: str
    snippet: str
    description: str
