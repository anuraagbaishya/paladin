from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from bson import ObjectId
from pydantic import BaseModel

from .enums import FileError, JobStatus, ReviewError


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


@dataclass
class JobResponse:
    repo: Optional[str] = None
    error: Optional[str] = None
    _id: Optional[ObjectId] = None
    status: JobStatus = JobStatus.PENDING
    created_at: int = field(
        default_factory=lambda: int(datetime.now(timezone.utc).timestamp())
    )
    updated_at: int = field(
        default_factory=lambda: int(datetime.now(timezone.utc).timestamp())
    )

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        if isinstance(self.status, Enum):
            d["status"] = self.status.value
        if isinstance(self._id, ObjectId):
            d["_id"] = str(self._id)
        return d
