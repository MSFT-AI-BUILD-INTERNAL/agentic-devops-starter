"""Pydantic models for Fleet and Infinite Session features."""

from pydantic import BaseModel, Field


class FleetItem(BaseModel):
    """Single item in a fleet batch."""

    prompt: str
    system_message: str | None = None


class FleetRequest(BaseModel):
    """Request to start a fleet job."""

    items: list[FleetItem] = Field(..., min_length=1, max_length=20)
    callback_url: str | None = None


class InfiniteSessionRequest(BaseModel):
    """Request for chained reasoning."""

    prompt: str
    iterations: int = Field(default=3, ge=1, le=10)
    system_message: str | None = None
    callback_url: str | None = None


class JobStatusResponse(BaseModel):
    """Response for job status polling."""

    job_id: str
    status: str
    result: str | None = None
    results: list[str] | None = None
    error: str | None = None
    created_at: str
    completed_at: str | None = None



class FileAttachment(BaseModel):
    """Represents a file that has been uploaded to Azure Blob Storage."""

    blob_name: str
    original_filename: str
    content_type: str
    size_bytes: int = Field(ge=1, le=10_485_760)


class UploadResult(BaseModel):
    """Response from a successful file upload."""

    blob_name: str
    original_filename: str
    content_type: str
    size_bytes: int


class TeamsRequest(BaseModel):
    """Request to execute a multi-agent pattern."""

    pattern_id: str
    prompt: str
    max_rounds: int = Field(default=3, ge=1, le=10)
    thread_id: str | None = None
    attachments: list[FileAttachment] | None = None


class SkillInfo(BaseModel):
    """Summary of an agent skill for listing via the REST API."""

    id: str
    name: str
    description: str
    keywords: list[str]
    tags: list[str]
    version: str


class PatternInfo(BaseModel):
    """Summary of an agent team pattern for listing."""

    id: str
    name: str
    description: str
    roles: list[str]


class AgentEvent(BaseModel):
    """SSE event emitted during agent team execution."""

    type: str
    agent_role: str | None = None
    round: int | None = None
    delta: str | None = None
    content: str | None = None
    pattern_id: str | None = None
    run_id: str | None = None
    converged: bool | None = None
    summary: str | None = None
    message: str | None = None
