import whisper
m = whisper.load_model("small")      # try "base" if RAM is tight
res = m.transcribe("harvard.wav", fp16=False)
print(res["text"])