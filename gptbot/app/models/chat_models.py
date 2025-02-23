from pydantic import BaseModel

class ChatRequest(BaseModel):
    message: str
    session_id: str = None  # Optional: If omitted, we create a new session.

class ChatResponse(BaseModel):
    response: str
    session_id: str