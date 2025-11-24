lines = open('input.txt', 'r', encoding='utf-8').read().splitlines()
file = open('output.txt', 'w', encoding='utf-8')
for line in lines:
    if len(line) == 0:
        continue
    new_line = [char for char in line if ord(char) < 256 or char.isalpha() or char == '–']
    # replace multiple spaces with single space
    new_line = ' '.join(''.join(new_line).split())
    # replace ** to empty
    new_line = new_line.replace('**', '').replace('–', '-')
    file.write(''.join(new_line) + '\n')
file.close()