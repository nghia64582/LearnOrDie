import ast

def python_list_to_java_format(file_path):
    with open(file_path, "r") as f:
        content = f.read().strip()

    try:
        data = ast.literal_eval(content)  # Safely evaluate the Python list
        if not isinstance(data, list):
            raise ValueError("Expected a list of lists")

        # Convert to Java-style string
        java_formatted = "{" + ", ".join(
            "{" + ", ".join(str(x) for x in sublist) + "}" for sublist in data
        ) + "};"

        return java_formatted

    except Exception as e:
        print("Error parsing input:", e)
        return ""

# Usage
input_file = "input.txt"
java_output = python_list_to_java_format(input_file)
print("Java format:")
print(java_output)
