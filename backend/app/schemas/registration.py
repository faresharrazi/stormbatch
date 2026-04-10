from typing import Any

from pydantic import BaseModel


class CreatedJob(BaseModel):
    session_id: str
    job_id: str
    status: str


class RegisterResponse(BaseModel):
    jobs: list[CreatedJob]
    duplicate_emails: list[str]
    row_count: int
    row_results: list[dict[str, Any]]
