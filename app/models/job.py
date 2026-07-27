from typing import Any, Optional, Dict
from pydantic import BaseModel

class SendToOrthancResponse(BaseModel):
    status: str
    job_id: str

class JobStatusResponse(BaseModel):
    id: str
    status: str  # "pending", "processing", "completed", "failed"
    progress: int
    created_at: str
    updated_at: str
    result: Optional[Any] = None
    error: Optional[str] = None
