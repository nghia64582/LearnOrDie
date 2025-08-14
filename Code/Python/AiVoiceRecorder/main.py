from transformers import AutoModelForCausalLM, AutoTokenizer
import torch

model_id = "Qwen/Qwen2-7B-Instruct"

tokenizer = AutoTokenizer.from_pretrained(model_id, trust_remote_code=True)
if tokenizer.pad_token is None:
    tokenizer.pad_token = tokenizer.eos_token
tokenizer.padding_side = "left"

# Load on CPU only (no Accelerate sharding/offload)
model = AutoModelForCausalLM.from_pretrained(
    model_id,
    torch_dtype=torch.float32,   # CPU-safe dtype
    trust_remote_code=True
).to("cpu")                      # ensure CPU

# 3) Build inputs WITH attention_mask and padding
prompt = "Hello, what is your name?"
inputs = tokenizer(
    prompt,
    return_tensors="pt",
    padding=True,                 # ensures attention_mask is created
    truncation=True,
    max_length=2048
).to(model.device)

# 4) Generate (pass attention_mask explicitly; set pad_token_id)
outputs = model.generate(
    input_ids=inputs.input_ids,
    attention_mask=inputs.attention_mask,   # <-- fixes the warning
    max_new_tokens=300,
    do_sample=True,
    temperature=0.7,
    top_p=0.9,
    use_cache=True,
    pad_token_id=tokenizer.pad_token_id
)

print(tokenizer.decode(outputs[0], skip_special_tokens=True))
