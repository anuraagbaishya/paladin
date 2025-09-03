from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional

from bson import ObjectId


class JobStatus(Enum):
    PENDING = "pending"
    DONE = "done"
    ERROR = "error"
    RUNNING = "running"


@dataclass
class ScanResult:
    repo: str
    scan_result: Dict[str, Any]  # SARIF is stored as a generic dict
    timestamp: int = field(
        default_factory=lambda: int(datetime.now(timezone.utc).timestamp())
    )


@dataclass
class Job:
    repo: str
    error: Optional[str] = None
    _id: Optional[ObjectId] = None
    status: JobStatus = JobStatus.PENDING
    created_at: int = field(
        default_factory=lambda: int(datetime.now(timezone.utc).timestamp())
    )
    updated_at: int = field(
        default_factory=lambda: int(datetime.now(timezone.utc).timestamp())
    )


@dataclass
class RepoInfo:
    repo: str
    stars: int
    forks: int


@dataclass
class Cwe:
    id: int
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
