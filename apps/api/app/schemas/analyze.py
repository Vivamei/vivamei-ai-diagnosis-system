from pydantic import BaseModel


class AnalyzeCreateRequest(BaseModel):
    photoId: int


class AnalyzeCreateResponse(BaseModel):
    taskId: str
    status: str
