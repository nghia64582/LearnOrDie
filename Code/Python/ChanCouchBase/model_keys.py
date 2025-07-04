def load_model_keys(filepath="model_key_name.txt") -> dict:
    keys = {}
    with open(filepath, "r") as f:
        for line in f:
            if "-" in line:
                prefix, name = line.strip().split("-", 1)
                keys[name.strip()] = prefix.strip()
    return keys
