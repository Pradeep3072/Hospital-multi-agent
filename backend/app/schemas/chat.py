from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., description="User message or query")
    patient_id: int = Field(default=1, description="Active patient ID context")
    session_id: Optional[str] = Field(default="session-web-1", description="Conversation session ID")


class ChatResponse(BaseModel):
    route: str
    supervisor: str
    delegated_agent: str
    is_emergency: bool
    tools_called: List[Optional[str]]
    tool_results: Any
    response: str
