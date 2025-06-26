import os

def to_base36(n: int) -> str:
    chars = "0123456789abcdefghijklmnopqrstuvwxyz"
    if n == 0: return "0"
    result = ""
    while n > 0:
        n, r = divmod(n, 36)
        result = chars[r] + result
    return result

def normalize_json(data: dict, model: str) -> dict:
    key_dict = min2full_dict.get(model, {})
    return expand_keys(data, key_dict=key_dict)

def minify_json(data: dict, model: str) -> dict:
    key_dict = full2min_dict.get(model, {})
    return minify_keys(data, key_dict=key_dict)

def parse_key_mapping_folder():
    global min2full_dict, full2min_dict
    min2full_dict = {}
    full2min_dict = {}
    folder_path = "minify/"

    for filename in os.listdir(folder_path):
        if filename.endswith(".txt"):
            key = filename[:-4]  # remove ".txt"
            min2full = {}
            full2min = {}

            file_path = os.path.join(folder_path, filename)
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line or '-' not in line:
                        continue
                    short, full = line.split('-', 1)
                    min2full[short] = full
                    full2min[full] = short

            min2full_dict[key] = min2full
            full2min_dict[key] = full2min

    return min2full_dict, full2min_dict

def expand_keys(data, key_dict):
    # do not call directly, since this is recursive, call normalize_json instead
    if isinstance(data, dict):
        result = {key_dict.get(k, k): expand_keys(v, key_dict) for k, v in data.items()}
    elif isinstance(data, list):
        result = [expand_keys(item, key_dict) for item in data]
    else:
        result = data
    return result
    
def minify_keys(data, key_dict):
    # do not call directly, since this is recursive, call minify_json instead
    if isinstance(data, dict):
        return {key_dict.get(k, k): minify_keys(v, key_dict) for k, v in data.items()}
    elif isinstance(data, list):
        return [minify_keys(item, key_dict) for item in data]
    else:
        return data
    
parse_key_mapping_folder()