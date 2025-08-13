from fastapi import FastAPI, File, UploadFile, HTTPException
from pydantic import BaseModel
import whisper
import torch
import tempfile
import os
from transformers import AutoModelForCausalLM, AutoTokenizer
import logging

app = FastAPI()

# Load Whisper model for speech-to-text
try:
    whisper_model = whisper.load_model("base")  # or 'small', 'medium', etc.
except Exception as e:
    logging.error("Failed to load Whisper model: %s", e)
    raise

# Load Qwen model
try:
    tokenizer = AutoTokenizer.from_pretrained("Qwen/Qwen1.5-0.5B-Chat", trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained("Qwen/Qwen1.5-0.5B-Chat", trust_remote_code=True).eval()
except Exception as e:
    logging.error("Failed to load Qwen model: %s", e)
    raise

class SummaryResponse(BaseModel):
    transcript: str
    summary: str

@app.post("/summarize", response_model=SummaryResponse)
async def summarize_audio(file: UploadFile = File(...)):
    if not file.filename.endswith(".mp3"):
        raise HTTPException(status_code=400, detail="Only MP3 files are supported.")

    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name

    try:
        # Transcribe
        transcription_result = whisper_model.transcribe(tmp_path)
        transcript = transcription_result["text"]

        # Proper Qwen Chat prompt
        messages = [
            {"role": "system", "content": "You are a helpful assistant who summarizes transcripts."},
            {"role": "user", "content": f"Tóm tắt nội dung sau: {transcript.strip()}"}
        ]
        input_ids = tokenizer.apply_chat_template(messages, return_tensors="pt", padding=True, truncation=True)
        attention_mask = (input_ids != tokenizer.pad_token_id).long()

        with torch.no_grad():
            output_ids = model.generate(
                input_ids=input_ids,
                attention_mask=attention_mask,
                max_new_tokens=200,
                do_sample=True
            )

        new_tokens = output_ids[0][input_ids.shape[-1]:]
        summary = tokenizer.decode(new_tokens, skip_special_tokens=True).strip()

    finally:
        os.unlink(tmp_path)

    return SummaryResponse(transcript=transcript, summary=summary)

@app.get("/")
def root():
    return {"message": "Upload an MP3 file to /summarize to get transcript and summary."}