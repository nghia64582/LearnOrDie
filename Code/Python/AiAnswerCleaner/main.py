import tkinter as tk
from tkinter import font

def clean_ai_response(text):
    lines = text.split('\n')
    count_backticks = 0
    count_hyphens = 0
    count_triple_dashes = 0
    new_lines = []
    is_empty_available = False
    is_inside_brace = False
    is_add_tab_colon = (False, "")
    for i in range(len(lines)):
        line = lines[i]
        new_line = "".join([char for char in line if ord(char) < 256 or char.isalpha() or char == '–'])
        # replace ** to empty
        new_line = new_line.replace('**', '').replace('–', '-')
        # if line contains "|" then keep as is (used in markdown tables)
        if '|' in line:
            new_line = line
        if count_backticks % 2 == 1:
            # insert tab before the line and allow empty lines
            new_line = " " * 4 + new_line
            is_empty_available = True
        # insert tab before lines starting with hyphen if not in code block, and not contain "<digit>." format
        if count_hyphens % 2 == 1 and not line.startswith('-') and not any([f"{i}." in line for i in range(1, 10)]):
            new_line = " " * 4 + new_line
        elif count_triple_dashes % 2 == 1:
            new_line = " " * 4 + new_line
            is_empty_available = False
        elif is_add_tab_colon[0]:
            if new_line.strip() and new_line.strip()[0] == is_add_tab_colon[1]:
                new_line = " " * 4 + new_line
            else:
                is_add_tab_colon = (False, "")
        if line.startswith('```'):
            count_backticks += 1
        if line.startswith('---'):
            count_triple_dashes += 1
        if line.startswith('-'):
            count_hyphens += 1
        if line.endswith(':'):
            is_add_tab_colon = (True, lines[i + 1][0] if i + 1 < len(lines) and lines[i + 1].strip() else "")
        if "}" in line:
            is_inside_brace = False
        if is_inside_brace:
            new_line = " " * 4 + new_line
        if "{" in line:
            is_inside_brace = True
        if "---" in new_line:
            new_line = new_line.strip()
        if not '```' in new_line and not (new_line.strip() == '' and not is_empty_available):
            new_lines.append(new_line)
    new_lines = [line for line in new_lines if line.strip() != '']
    return "\n".join(new_lines)

# ================================
#  GUI
# ================================
def run_gui():
    root = tk.Tk()
    root.title("AI Response Cleaner")
    root.geometry("700x600")

    # Custom font
    APP_FONT = font.Font(family="Times New Roman", size=12)

    # ----- Input Label -----
    lbl_input = tk.Label(root, text="Input", font=APP_FONT)
    lbl_input.pack(pady=(10, 2))

    # ----- Input Text -----
    txt_input = tk.Text(root, height=10, font=APP_FONT, wrap="word")
    txt_input.pack(fill="both", expand=True, padx=10, pady=(0, 10))

    # ----- Output Label -----
    lbl_output = tk.Label(root, text="Output", font=APP_FONT)
    lbl_output.pack(pady=(10, 2))

    # ----- Output Text -----
    txt_output = tk.Text(root, height=10, font=APP_FONT, wrap="word")
    txt_output.pack(fill="both", expand=True, padx=10, pady=(0, 10))

    # ----- Convert Button -----
    def convert_text():
        raw = txt_input.get("1.0", tk.END)
        cleaned = clean_ai_response(raw)
        txt_output.delete("1.0", tk.END)
        txt_output.insert("1.0", cleaned)

    btn_convert = tk.Button(root, text="Convert", font=APP_FONT, command=convert_text)
    btn_convert.pack(pady=10)

    root.mainloop()


if __name__ == "__main__":
    run_gui()
