from fastapi import FastAPI, File, UploadFile, HTTPException
from pydantic import BaseModel
import whisper
import torch
import tempfile
import os
from transformers import AutoModelForCausalLM, AutoTokenizer
import logging
import time

try:
    whisper_model = whisper.load_model("base")  # or 'small', 'medium', etc.
except Exception as e:
    logging.error("Failed to load Whisper model: %s", e)
    raise

model_id = "Qwen/Qwen-7B-Chat"  # Qwen-1 chat
model_id = "Qwen/Qwen2-1.5B-Instruct"

tokenizer = AutoTokenizer.from_pretrained(model_id, trust_remote_code=True)
#    We'll use the ChatML end token "<|im_end|>" (Qwen uses ChatML-style prompts).
need_resize = False
if tokenizer.eos_token is None and tokenizer.pad_token is None:
    # Add a single special token and point both EOS and PAD to it
    special = {"additional_special_tokens": ["<|im_end|>"]}
    tokenizer.add_special_tokens(special)
    # Now assign both to the same string so they resolve to the SAME id
    tokenizer.eos_token = "<|im_end|>"
    tokenizer.pad_token = "<|im_end|>"
    need_resize = True
elif tokenizer.eos_token is None:
    # Reuse PAD as EOS if PAD exists; otherwise add one
    if tokenizer.pad_token is not None:
        tokenizer.eos_token = tokenizer.pad_token
    else:
        tokenizer.add_special_tokens({"additional_special_tokens": ["<|im_end|>"]})
        tokenizer.eos_token = "<|im_end|>"
        tokenizer.pad_token = "<|im_end|>"
        need_resize = True
elif tokenizer.pad_token is None:
    # If EOS exists, reuse it for PAD
    tokenizer.pad_token = tokenizer.eos_token
tokenizer.padding_side = "left"   # safer for generation on causal LMs

model = AutoModelForCausalLM.from_pretrained(
    model_id,
    torch_dtype=torch.float32,
    trust_remote_code=True,
).to("cpu")
model.config.use_cache = False
model.eval()

# Supply a minimal ChatML template if missing
if not getattr(tokenizer, "chat_template", None):
    tokenizer.chat_template = (
        "{% for m in messages %}"
        "{% if m['role'] == 'system' %}<|im_start|>system\n{{ m['content'] }}<|im_end|>\n"
        "{% elif m['role'] == 'user' %}<|im_start|>user\n{{ m['content'] }}<|im_end|>\n"
        "{% elif m['role'] == 'assistant' %}<|im_start|>assistant\n{{ m['content'] }}<|im_end|>\n"
        "{% endif %}"
        "{% endfor %}<|im_start|>assistant\n"
    )

print("pad_token_id:", tokenizer.pad_token, "eos_token_id:", tokenizer.eos_token)
print("has_template:", bool(getattr(tokenizer, "chat_template", None)))

app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "Hello, FastAPI!"}

class SummaryResponse(BaseModel):
    transcript: str
    summary: str

class AnswerResponse(BaseModel):
    answer: str

class SummaryRequest(BaseModel):
    text: str

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
                do_sample=True,
                pad_token_id=tokenizer.pad_token_id
            )

        new_tokens = output_ids[0][input_ids.shape[-1]:]
        summary = tokenizer.decode(new_tokens, skip_special_tokens=True).strip()

    finally:
        os.unlink(tmp_path)

    return SummaryResponse(transcript=transcript, summary=summary)

@app.post("/summarize-text", response_model=SummaryResponse)
async def summarize_text(req: SummaryRequest):
    # Proper Qwen Chat prompt
    text = req.text
    messages = [
        {"role": "system", "content": "You are a helpful assistant who summarizes text."},
        {"role": "user", "content": f"Tóm tắt nội dung sau: {text.strip()}"}
    ]
    print(f"S1 {time.time()}")
    input_ids = tokenizer.apply_chat_template(
        messages,
        add_generation_prompt=True,
        return_tensors="pt",
        padding=True,
        truncation=True,
        max_length=2048,
    )
    print(f"S2 {time.time()}")
    if not torch.is_tensor(input_ids):
        raise RuntimeError(f"apply_chat_template did not return a tensor, got: {type(input_ids)}")

    print(f"S3 {time.time()}")
    pad_id = tokenizer.pad_token_id
    if pad_id is None:
        raise RuntimeError("tokenizer.pad_token_id is None; make sure you set tokenizer.pad_token and/or eos_token, then resize embeddings if you added tokens.")
    attention_mask = (input_ids != pad_id).long()

    print(f"S4 {time.time()}")
    input_ids = input_ids.to(model.device)
    attention_mask = attention_mask.to(model.device)

    print(f"S5 {time.time()}")
    with torch.no_grad():
        output_ids = model.generate(
            input_ids=input_ids,
            attention_mask=attention_mask,
            max_new_tokens=100,
            do_sample=True,
            use_cache=False,
            pad_token_id=tokenizer.pad_token_id
        )
    print(f"S6 {time.time()}")

    new_tokens = output_ids[0][input_ids.shape[-1]:]
    answer = tokenizer.decode(new_tokens, skip_special_tokens=True).strip()

    return SummaryResponse(transcript=text, summary=answer)

@app.get("/")
def root():
    return {"message": "Upload an MP3 file to /summarize to get transcript and summary."}

@app.post("/question", response_model=AnswerResponse)
async def answer_questions(req: SummaryRequest):
    text = req.text
    messages = [
        {"role": "user", "content": f"{text.strip()}"}
    ]
    print(f"S1 {time.time()}")
    input_ids = tokenizer.apply_chat_template(
        messages,
        add_generation_prompt=True,
        return_tensors="pt",
        padding=True,
        truncation=True,
        max_length=2048,
    )
    print(f"S2 {time.time()}")
    if not torch.is_tensor(input_ids):
        raise RuntimeError(f"apply_chat_template did not return a tensor, got: {type(input_ids)}")

    print(f"S3 {time.time()}")
    pad_id = tokenizer.pad_token_id
    if pad_id is None:
        raise RuntimeError("tokenizer.pad_token_id is None; make sure you set tokenizer.pad_token and/or eos_token, then resize embeddings if you added tokens.")
    attention_mask = (input_ids != pad_id).long()

    print(f"S4 {time.time()}")
    input_ids = input_ids.to(model.device)
    attention_mask = attention_mask.to(model.device)

    print(f"S5 {time.time()}")
    with torch.no_grad():
        output_ids = model.generate(
            input_ids=input_ids,
            attention_mask=attention_mask,
            max_new_tokens=100,
            do_sample=True,
            use_cache=False,
            pad_token_id=tokenizer.pad_token_id
        )
    print(f"S6 {time.time()}")

    new_tokens = output_ids[0][input_ids.shape[-1]:]
    answer = tokenizer.decode(new_tokens, skip_special_tokens=True).strip()

    print(f"S7 {time.time()}")
    return AnswerResponse(answer=answer)