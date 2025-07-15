import random as rd
import stemming as stem

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
    for i in range(100):
        words = rd.choice(group_words).strip().split("-")
        print(words[0])

if __name__ == "__main__":
    # get_vocabulary()
    # group_words()
    get_to_learn()