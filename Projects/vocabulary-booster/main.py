import random as rd

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

def is_long_word(word):
    return word.count(' ') > 2
# @aberrance /æ'berəns/ (aberrancy) /æ'berənsi/
lines = open("english-vietnamese.txt", "r", encoding="utf-8").readlines()
words = [line.strip().split("/")[0].strip() for line in lines if '@' in line]
to_learn_words = []
draft_file = open("draft.txt", "w", encoding="utf-8")
for word in words:
    word = word.strip()
    if is_plural(word) or is_past_tense(word) or is_present_tense(word) or is_adverb(word) or is_noun_ness(word) or \
        is_long_word(word) or is_noun_tion(word) or is_noun_ity(word) or is_adjective_al(word):
        continue
    to_learn_words.append(word)
    draft_file.write(word + '\n')
draft_file.close()
print(f"len(lines): {len(lines)}")
print(f"len(words): {len(words)}")
print(f"len(to_learn_words): {len(to_learn_words)}")
for i in range(100):
    print(rd.choice(to_learn_words))