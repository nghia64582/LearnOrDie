def load_model_keys(filepath="ModelKeyName.txt") -> dict:
    keys = {}
    with open(filepath, "r") as f:
        for line in f:
            if "-" in line:
                prefix, name = line.strip().split("-", 1)
                keys[name.strip()] = prefix.strip()
    return keys
