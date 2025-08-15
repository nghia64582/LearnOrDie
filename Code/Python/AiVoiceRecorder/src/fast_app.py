from fastapi import FastAPI
from api_dto import *
from pydantic import BaseModel
from voice_model import *
from ai_model import *

ai_model = AiModel(model_id="Qwen/Qwen2-1.5B-Instruct", device="cpu")
app = FastAPI()

@app.get("/")
def root():
    return {"message": "Upload an MP3 file to /summarize to get transcript and summary."}

@app.post("/summarize-text", response_model=SummaryResponse)
async def summarize_text(req: SummaryRequest):
    text = req.text.strip()
    answer = ai_model.generate_response(f"Summary this conversation : {text}")
    return SummaryResponse(transcript=text, summary=answer)

@app.post("/question", response_model=AnswerResponse)
async def answer_questions(req: SummaryRequest):
    answer = ai_model.generate_response(req.text)
    return AnswerResponse(answer=answer)