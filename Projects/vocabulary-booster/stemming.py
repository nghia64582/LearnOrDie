import nltk
from nltk.stem import LancasterStemmer # Changed from PorterStemmer
from collections import defaultdict

# --- NLTK Data Download (Run this once if you haven't already) ---
# For the stemmers to work, you might need to download 'punkt' data.
# If you get a LookupError, uncomment the line below and run your script once.
# nltk.download('punkt')
# -----------------------------------------------------------------

def group_words_by_stem(word_list: list[str]) -> list[list[str]]:
    """
    Groups words by their stem (root form) to find words with nearly the same meaning,
    only differing in word type (e.g., learn, learned, learning, learner).
    This version uses LancasterStemmer, which is more aggressive than PorterStemmer
    and can group words like 'learn' and 'learner'.

    Args:
        word_list: A list of strings representing the dictionary words.

    Returns:
        A list of lists, where each inner list contains words that share the same stem.
    """
    # Using LancasterStemmer for more aggressive stemming
    stemmer = LancasterStemmer()
    # Use a defaultdict to automatically create a new list for a stem if it doesn't exist
    grouped_words = defaultdict(list)

    for word in word_list:
        # Convert the word to lowercase before stemming for consistent grouping
        lower_word = word.lower()
        stem = stemmer.stem(lower_word)
        # Add the original word to the list corresponding to its stem
        grouped_words[stem].append(word)

    # Convert the dictionary values (lists of words) into a list of lists
    return list(grouped_words.values())

# --- Example Usage ---
if __name__ == "__main__":
    # Your example dictionary (a small subset for demonstration)
    my_dictionary = [
        "learn", "learned", "learning", "learner", "teaches", "teacher",
        "running", "runs", "ran", "beautiful", "beauty", "beautify",
        "jump", "jumping", "jumps", "apple", "apples", "run", "dog", "dogs"
    ]

    grouped_results = group_words_by_stem(my_dictionary)

    print("Original Words:")
    print(my_dictionary)
    print("\nGrouped Words by Stem (using LancasterStemmer):")
    for group in grouped_results:
        print(group)

    # Example with a larger list (simulating 90k words)
    # This part is commented out but shows how you'd use it with a large list
    # large_word_list = ["word" + str(i) for i in range(90000)] + my_dictionary
    # large_grouped_results = group_words_by_stem(large_word_list)
    # print(f"\nGrouped {len(large_word_list)} words into {len(large_grouped_results)} groups.")
