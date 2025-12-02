lines = open('input.txt', 'r', encoding='utf-8').read().splitlines()
file = open('output.txt', 'w', encoding='utf-8')
count_backticks = 0
count_hyphens = 0
new_lines = []
is_empty_available = False
is_inside_brace = False
for line in lines:
    new_line = "".join([char for char in line if ord(char) < 256 or char.isalpha() or char == '–'])
    # replace ** to empty
    new_line = new_line.replace('**', '').replace('–', '-')
    # if line contains "|" then keep as is (used in markdown tables)
    if '|' in line:
        new_line = line
    if count_backticks % 2 == 1:
        # insert tab before the line and allow empty lines
        new_line = "\t" + new_line
        is_empty_available = True
    # insert tab before lines starting with hyphen if not in code block, and not contain "<digit>." format
    if count_hyphens % 2 == 1 and not line.startswith('-') and not any([f"{i}." in line for i in range(1, 10)]):
        new_line = "\t" + new_line
    else:
        is_empty_available = False
    if line.startswith('```'):
        count_backticks += 1
    if line.startswith('-'):
        count_hyphens += 1
    if "}" in line:
        is_inside_brace = False
    if is_inside_brace:
        new_line = "\t" + new_line
    if "{" in line:
        is_inside_brace = True
    if not '```' in new_line and not (new_line.strip() == '' and not is_empty_available):
        new_lines.append(new_line)

file.write("\n".join(new_lines))
file.close()