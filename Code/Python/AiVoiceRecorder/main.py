from transformers import AutoModelForCausalLM, AutoTokenizer
import torch

tokenizer = AutoTokenizer.from_pretrained("Qwen/Qwen2-7B-Instruct", trust_remote_code=True)
model = AutoModelForCausalLM.from_pretrained("Qwen/Qwen2-7B-Instruct", device_map="auto", trust_remote_code=True)

# Inference
prompt = "Hello, what is your name?"
inputs = tokenizer(prompt, return_tensors='pt').to(model.device)

# --- Correct way to generate text ---
# The 'generate' method handles past_key_values internally.
# Ensure 'use_cache=True' is either default or explicitly set.
outputs = model.generate(
    inputs.input_ids,
    max_new_tokens=100,
    do_sample=True,
    temperature=0.7,
    top_p=0.9,
    use_cache=True, # Ensure this is True
    pad_token_id=tokenizer.eos_token_id # Good practice for text generation
)

response = tokenizer.decode(outputs[0], skip_special_tokens=True)
print(response)