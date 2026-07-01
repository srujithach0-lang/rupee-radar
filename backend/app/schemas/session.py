from datetime import datetime

from pydantic import BaseModel, Field


class SessionResponse(BaseModel):
    id: str
    filename: str
    file_type: str
    status: str
    uploaded_at: datetime
    expires_at: datetime | None
    row_count: int
    error_message: str | None
    parse_warnings: list[str] = Field(default_factory=list)


class UploadResponse(BaseModel):
    session_id: str
    status: str
    message: str = "Processing complete"
