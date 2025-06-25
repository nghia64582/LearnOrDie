def to_base36(n: int) -> str:
    chars = "0123456789abcdefghijklmnopqrstuvwxyz"
    if n == 0: return "0"
    result = ""
    while n > 0:
        n, r = divmod(n, 36)
        result = chars[r] + result
    return result

def normalize_json(data: dict, mapping: dict) -> dict:
    return {mapping.get(k, k): v for k, v in data.items()}
