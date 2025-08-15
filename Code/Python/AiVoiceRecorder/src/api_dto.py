from pydantic import BaseModel

class SummaryResponse(BaseModel):
    transcript: str
    summary: str

class AnswerResponse(BaseModel):
    answer: str

class SummaryRequest(BaseModel):
    text: str
