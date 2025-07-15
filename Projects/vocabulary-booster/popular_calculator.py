import re
from collections import Counter
import math
import os

def analyze_word_popularity(vocabulary_words, corpus_text, top_n=10000):
    """
    Analyzes word popularity from a corpus for a given vocabulary.

    Args:
        vocabulary_words (list): A list of English words (your 90,000 words).
        corpus_text (str): A large string of English text (your corpus).
        top_n (int): The number of most popular words to focus on.

    Returns:
        list: A list of tuples (word, popularity_score) for the top_n words.
    """
    print("Bước 1: Tiền xử lý corpus và đếm tần suất từ...")
    # Normalize corpus text: lowercase and remove non-alphabetic characters
    # This regex keeps only letters and spaces, then splits by whitespace
    words_in_corpus = re.findall(r'[a-z]+', corpus_text.lower())

    # Count word frequencies
    word_counts = Counter(words_in_corpus)
    print(f"   -> Tổng số từ duy nhất trong corpus: {len(word_counts)}")

    print("Bước 2: Lọc tần suất theo từ vựng của bạn...")
    # Filter word counts to include only words from your vocabulary
    filtered_word_counts = {
        word: count for word, count in word_counts.items()
        if word in vocabulary_words
    }
    print(f"   -> Số từ trong từ vựng của bạn được tìm thấy trong corpus: {len(filtered_word_counts)}")

    if not filtered_word_counts:
        print("Không tìm thấy từ nào trong từ vựng của bạn trong corpus. Vui lòng kiểm tra dữ liệu.")
        return []

    print("Bước 3: Xếp hạng từ theo tần suất...")
    # Sort words by frequency in descending order
    sorted_words = sorted(filtered_word_counts.items(), key=lambda item: item[1], reverse=True)
    print(f"   -> Tổng số từ đã lọc và sắp xếp: {len(sorted_words)}")

    print(f"Bước 4: Chọn {top_n} từ phổ biến nhất và gán điểm...")
    # Select the top_n most popular words
    top_words = sorted_words[:top_n]

    # Assign popularity scores (1-100 scale)
    # We'll use a rank-based scoring for simplicity and to fit the 1-100 range.
    # The highest ranked word gets 100, the lowest (within top_n) gets 1.
    # Words not in top_n get a score of 0 (or you can assign a base score like 1)
    popularity_scores = []
    if top_words:
        # Scale the rank from 1 to 100.
        # Rank 1 (most popular) -> 100
        # Rank top_n (least popular in top_n) -> 1
        # Using a linear scale for ranks: score = 100 - (rank / top_n) * 99
        # Or simply map rank to 1-100 range:
        # The first word (rank 0) gets 100, the last word (rank top_n-1) gets 1
        # score = 100 - (rank * 99 / (top_n - 1)) if top_n > 1 else 100
        # Let's simplify: top 10% get 100, then linearly decrease.

        # More robust scoring:
        # Assign 100 to the very top words (e.g., top 1% of top_n)
        # Then linearly scale down for the rest.
        # Or, a simple linear scale across the top_n words.

        # Let's define tiers for scoring:
        # Top 1% (100 words) -> 100
        # Next 9% (900 words) -> 90-99
        # Next 40% (4000 words) -> 50-89
        # Remaining 50% (5000 words) -> 1-49

        num_words = len(top_words)
        for i, (word, count) in enumerate(top_words):
            score = 0
            if i < num_words * 0.01: # Top 1%
                score = 100
            elif i < num_words * 0.10: # Next 9%
                score = 90 + int((num_words * 0.10 - i) / (num_words * 0.09) * 9) # 90-99
            elif i < num_words * 0.50: # Next 40%
                score = 50 + int((num_words * 0.50 - i) / (num_words * 0.40) * 39) # 50-89
            else: # Remaining 50%
                score = 1 + int((num_words - i) / (num_words * 0.50) * 48) # 1-49
            
            # Ensure score is within 1-100 range
            score = max(1, min(100, score))
            popularity_scores.append((word, score))
    
    print(f"   -> Đã gán điểm cho {len(popularity_scores)} từ.")
    return popularity_scores

def export_to_file(data, filename="word_popularity.txt"):
    """Exports the word popularity data to a text file."""
    print(f"Bước 5: Xuất dữ liệu ra file '{filename}'...")
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            for word, score in data:
                f.write(f"{word},{score}\n")
        print(f"   -> Xuất file thành công: {filename}")
    except IOError as e:
        print(f"Lỗi khi ghi file: {e}")

if __name__ == "__main__":
    # --- SIMULATED DATA (REPLACE WITH REAL DATA) ---
    # Simulate your 90,000-word vocabulary
    # In a real scenario, you'd load this from a file:
    # with open('your_vocabulary.txt', 'r', encoding='utf-8') as f:
    #     vocabulary_words = [line.strip().lower() for line in f if line.strip()]
    sample_vocabulary = [
        "is", "have", "name", "the", "a", "an", "and", "but", "or", "in", "on", "at",
        "apple", "banana", "orange", "hello", "world", "python", "javascript",
        "react", "scala", "java", "database", "server", "client", "network",
        "computer", "software", "hardware", "program", "code", "function",
        "variable", "data", "file", "system", "user", "application", "project",
        "development", "learning", "english", "vietnamese", "word", "popularity",
        "styx", "lobulose", "quincunx", "zeugma", "cacography", "ephemeral", "ubiquitous",
        "serendipity", "mellifluous", "luminous", "benevolent", "eloquence",
        # Add more words to reach ~90,000 in a real scenario
    ]
    # Add some more words to make the example more realistic for sorting
    for i in range(1, 80000):
        sample_vocabulary.append(f"word{i}")
    
    # Simulate a large English text corpus
    # In a real scenario, you'd load this from a massive text file or multiple files:
    # with open('your_corpus.txt', 'r', encoding='utf-8') as f:
    #     corpus_text = f.read()
    sample_corpus_text = """
    The quick brown fox jumps over the lazy dog. This is a sample text to demonstrate
    word frequency counting. Python is a versatile language. React and Scala are used
    for web development. This project involves a database server and client applications.
    Hello world, this is a test. The popularity of words like "is" and "the" will be high.
    We have a name for this. The computer program runs on the network.
    Data files are important for the system user. An application project requires development and learning.
    English and Vietnamese words are being analyzed for popularity.
    Some rare words like styx and lobulose might appear, but very infrequently.
    This is a very long string to simulate a large corpus.
    """ * 5000 # Repeat to make it "large" for demonstration

    print(f"Kích thước từ vựng mẫu: {len(sample_vocabulary)} từ.")
    print(f"Kích thước corpus mẫu: {len(sample_corpus_text)} ký tự.")

    # Run the analysis
    popular_words_with_scores = analyze_word_popularity(sample_vocabulary, sample_corpus_text, top_n=10000)

    # Export the results
    output_filename = "word_popularity_scores.csv" # Using .csv for clarity
    export_to_file(popular_words_with_scores, output_filename)

    print("\n--- Hoàn thành phân tích ---")
    print(f"Kiểm tra file '{output_filename}' để xem kết quả.")
    print(f"Tổng số từ được xuất: {len(popular_words_with_scores)}")

    # Optional: Print a few examples
    print("\nMột vài ví dụ từ phổ biến nhất:")
    for i, (word, score) in enumerate(popular_words_with_scores[:10]):
        print(f"   {i+1}. {word}: {score}")

    print("\nMột vài ví dụ từ ít phổ biến nhất (trong top 10000):")
    for i, (word, score) in enumerate(popular_words_with_scores[max(0, len(popular_words_with_scores) - 10):]):
        print(f"   {len(popular_words_with_scores) - 9 + i}. {word}: {score}")
