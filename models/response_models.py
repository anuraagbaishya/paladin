from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class FileError(Enum):
    INVALID_PATH = "invalid file path"
    NOT_FOUND = "file not found"
    READ_FAIL = "failed to read file"


class ReviewError(Enum):
    REVIEW_FAIL = "gemini review failed"
    SCAN_NOT_FOUND = "scan not found for given scan id"
    NO_FINDING = "no finding found for provided scan id and fingerprint id"
    INCOMPLETE_FINDING = "finding is missing required fields"
    NO_ANSWER = "no response from gemini"
    NO_API_KEY = "gemini api key not configured"


@dataclass
class FileResponse:
    error: Optional[FileError] = None
    file: Optional[List[str]] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        if isinstance(self.error, Enum):
            d["error"] = self.error.value
        return d


# gemini structured output expects pydantic basemodels
class GeminiReview(BaseModel):
    verdict: bool
    reason: str


@dataclass
class ReviewResponse:
    error: Optional[ReviewError] = None
    review: Optional[GeminiReview] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        if isinstance(self.review, GeminiReview):
            d["review"] = self.review.model_dump()

        if isinstance(self.error, Enum):
            d["error"] = self.error.value

        return d
