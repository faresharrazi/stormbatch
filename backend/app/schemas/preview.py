from pydantic import BaseModel


class PreviewResponse(BaseModel):
    headers: list[str]
    preview_rows: list[dict[str, str]]
    normalized_headers: dict[str, str]
    suggestions: dict[str, str]
    row_count: int
    duplicate_email_columns: dict[str, list[str]]
