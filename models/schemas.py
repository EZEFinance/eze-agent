from typing import Optional
from pydantic import BaseModel

class QueryRequest(BaseModel):
    query: str
    thread_id: Optional[str] = None

class QueryResponse(BaseModel):
    response: str
    thread_id: str
    processing_time: float