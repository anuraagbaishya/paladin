from typing import Optional
from pydantic import BaseModel, Field


class AiReview(BaseModel):
    verdict: bool
    reason: str


class ClaudeResponse(BaseModel):
    error: Optional[str] = None
    review: Optional[AiReview] = None


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


class FindingForReview(BaseModel):
    repo: str
    scan_result: ScanResult
