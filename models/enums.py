from enum import Enum


class FileError(str, Enum):
    INVALID_PATH = "invalid file path"
    NOT_FOUND = "file not found"
    READ_FAIL = "failed to read file"


class ReviewError(str, Enum):
    REVIEW_FAIL = "gemini review failed"
    SCAN_NOT_FOUND = "scan not found for given scan id"
    NO_FINDING = "no finding found for provided scan id and fingerprint id"
    INCOMPLETE_FINDING = "finding is missing required fields"
    NO_ANSWER = "no response from gemini"
    NO_API_KEY = "gemini api key not configured"


class JobStatus(str, Enum):
    PENDING = "pending"
    DONE = "done"
    ERROR = "error"
    RUNNING = "running"
