from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field

from .response_models import AiReview


class ScanResult(BaseModel):
    scan_id: str
    fingerprint: str
    file: str
    start_line: int
    end_line: int
    rule_id: str
    snippet: str
    description: str
    severity: str
    dataflows: Optional[list] = Field(default=None)
    suppressed: bool = Field(default=False)
    ai_review: AiReview = Field(
        default_factory=lambda: AiReview(verdict=False, reason="")
    )

    def to_api_dict(self) -> dict:
        return {
            "fingerprint": self.fingerprint,
            "file": self.file,
            "startLine": self.start_line,
            "endLine": self.end_line,
            "ruleId": self.rule_id,
            "snippet": self.snippet,
            "description": self.description,
            "severity": self.severity,
            "dataflows": self.dataflows,
            "suppressed": self.suppressed,
            "aiReview": self.ai_review.model_dump(),
        }


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


class ScanMetadata(BaseModel):
    scan_id: str
    repo: str
    timestamp: int = Field(
        default_factory=lambda: int(datetime.now(timezone.utc).timestamp())
    )
    languages: list[str] = Field(default_factory=list)
    findings_count: int = 0


class FindingForReview(BaseModel):
    repo: str
    scan_result: ScanResult
