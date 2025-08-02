import random as rd
import stemming as stem
import re

def get_vocabulary():
    global words, to_learn_words
    def is_extension(word):
        def is_plural(word):
            return word.endswith('s') or word.endswith('es')

        def is_past_tense(word):
            return word.endswith('ed')

        def is_present_tense(word):
            return word.endswith('ing')

        def is_adverb(word):
            return word.endswith('ly')

        def is_noun_ness(word):
            return word.endswith('ness')

        def is_noun_tion(word):
            return word.endswith('tion')

        def is_noun_ity(word):
            return word.endswith('ity')

        def is_adjective_al(word):
            return word.endswith('al')

        def is_noun_ment(word):
            return word.endswith('ment')

        def is_long_word(word):
            return word.count(' ') > 2
        
        return is_plural(word) or is_past_tense(word) or is_present_tense(word) or is_adverb(word) or \
               is_noun_ness(word) or is_long_word(word) or is_noun_tion(word) or is_noun_ity(word) or \
               is_adjective_al(word) or is_noun_ment(word)
    
    # @aberrance /æ'berəns/ (aberrancy) /æ'berənsi/
    lines = open("english-vietnamese.txt", "r", encoding="utf-8").readlines()
    words = [line.strip().split("/")[0].strip().replace("@", "") for line in lines if '@' in line]
    to_learn_words = []
    draft_file = open("draft.txt", "w", encoding="utf-8")
    for word in words:
        word = word.strip()
        if not word or len(word) < 3 or is_extension(word):
            continue
        to_learn_words.append(word)
        draft_file.write(word + '\n')
    draft_file.close()
    print(f"len(lines): {len(lines)}")
    print(f"len(words): {len(words)}")
    print(f"len(to_learn_words): {len(to_learn_words)}")

def group_words():
    global words, to_learn_words
    group_words = stem.group_words_by_stem(to_learn_words)
    group_words.sort(key=lambda x: x[0], reverse=False)

    # Save the grouped words to a file
    to_learn_file = open("to_learn.txt", "w", encoding="utf-8")
    for group in group_words:
        if len(group) < 2:
            continue
        to_learn_file.write("-".join(group) + '\n')
    to_learn_file.close()

    print(f"len(group_words): {len(group_words)}")
    to_learn_words = []
    for group in group_words:
        if len(group) < 2:
            continue
        to_learn_words.append(group[0])
    print(f"len(to_learn_words): {len(to_learn_words)}")

def get_to_learn():
    group_words = open("to_learn.txt", "r", encoding="utf-8").readlines()
    print(len(group_words))

def parse_dictionary_file(file_path):
    global eng_dict
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    eng_dict = {}
    current_word = None
    pronunciation = ""
    word_type = ""
    meanings = []
    examples = []

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Detect new word entry
        if line.startswith('@'):
            # Save previous word
            if current_word:
                eng_dict[current_word] = {
                    "pronunciation": pronunciation,
                    "type": word_type,
                    "meaning": meanings,
                    "example": examples
                }

            # Reset all
            current_word = line[1:].split(' ')[0]
            pronunciation_match = re.search(r'/.*?/', line)
            pronunciation = pronunciation_match.group(0) if pronunciation_match else ""
            word_type = ""
            meanings = []
            examples = []
        elif line.startswith('*'):
            word_type = line.replace('*', '').strip()
        elif line.startswith('-'):
            meanings.append(line[1:].strip())
        elif line.startswith('='):
            examples.append(line[1:].strip())
        else:
            # Continuation of previous line (merge last meaning or example)
            if meanings:
                meanings[-1] += ' ' + line
            elif examples:
                examples[-1] += ' ' + line

    # Save last word
    if current_word and pronunciation:
        eng_dict[current_word] = {
            "pronunciation": pronunciation,
            "type": word_type,
            "meaning": meanings,
            "example": examples
        }

    return eng_dict

def process_dict():
    lines = open("english-vietnamese.txt", "r", encoding="utf-8").readlines()
    total_at = 0
    total_star = 0
    total_slash = 0
    for line in lines:
        if '@' in line:
            total_at += 1
        if '*' in line:
            total_star += 1
        if '/' in line:
            total_slash += 1
    print(f"Total @: {total_at}, Total *: {total_star}, Total /: {total_slash}")
    print(f"Total characters: {sum([len(line) for line in lines])}")

def process_dict_v2():
    parse_dictionary_file("english-vietnamese.txt")
    no_meaning_words = []
    no_example_words = []
    no_pronunciation_words = []
    no_type_words = []
    full_words = []
    for key in eng_dict:
        if not eng_dict[key]["meaning"]:
            no_meaning_words.append(key)
        if not eng_dict[key]["example"]:
            no_example_words.append(key)
        if not eng_dict[key]["pronunciation"]:
            no_pronunciation_words.append(key)
        if not eng_dict[key]["type"]:
            no_type_words.append(key)
        if eng_dict[key]["meaning"] and eng_dict[key]["example"] and eng_dict[key]["pronunciation"] and eng_dict[key]["type"]:
            full_words.append(key)
    for i in range(10):
        print(f"No meaning word {i}: {rd.choice(no_meaning_words)}")
    for i in range(10):
        print(f"No example word {i}: {rd.choice(no_example_words)}")
    for i in range(10):
        print(f"No pronunciation word {i}: {rd.choice(no_pronunciation_words)}")
    for i in range(10):
        print(f"No type word {i}: {rd.choice(no_type_words)}")
    for i in range(10):
        print(f"Full word {i}: {rd.choice(full_words)}")

    print(f"len(full_words): {len(full_words)}")
    print(f"len(no_meaning_words): {len(no_meaning_words)}")
    print(f"len(no_example_words): {len(no_example_words)}")
    print(f"len(no_pronunciation_words): {len(no_pronunciation_words)}")
    print(f"len(no_type_words): {len(no_type_words)}")

def process_dict_v3():
    # Count the line by first character
    # With each character, print first 5 lines
    lines = open("english-vietnamese.txt", "r", encoding="utf-8").readlines()
    char_count = {}
    for line in lines:
        if not line.strip():
            continue
        first_char = line[0]
        if first_char not in char_count:
            char_count[first_char] = []
        char_count[first_char].append(line.strip())

    for first_char in char_count:
        if first_char.isalpha():
            continue
        print(f"Lines starting with '{first_char}':")
        for i, line in enumerate(char_count[first_char][:5]):
            print(line)
        print()

if __name__ == "__main__":
    # get_vocabulary()
    # group_words()
    # get_to_learn()
    process_dict_v3()