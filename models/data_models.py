from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field
from pysarif import Result

from .response_models import GeminiReview


class ScanResult(BaseModel):
    scan_id: str
    repo: str
    result: Result
    severity: str
    timestamp: int = Field(
        default_factory=lambda: int(datetime.now(timezone.utc).timestamp())
    )
    suppressed: bool = Field(default=False)
    ai_review: GeminiReview = Field(
        default_factory=lambda: GeminiReview(verdict=False, reason="")
    )


class RepoInfo(BaseModel):
    repo: str
    stars: int
    forks: int


class Cwe(BaseModel):
    id: str
    title: str


class VulnReport(BaseModel):
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


class FindingForReview(BaseModel):
    rule_id: str
    snippet: str
    description: str
