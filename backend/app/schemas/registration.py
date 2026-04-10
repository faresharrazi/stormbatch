from typing import Any

from pydantic import BaseModel, Field


class CreatedJob(BaseModel):
    session_id: str
    job_id: str
    status: str
    chunk_index: int = 1
    chunk_count: int = 1
    row_start: int = 2
    row_count: int = 0
    row_results: list[dict[str, Any]] = Field(default_factory=list)


class RegisterResponse(BaseModel):
    jobs: list[CreatedJob]
    duplicate_emails: list[str]
    row_count: int
    row_results: list[dict[str, Any]]
