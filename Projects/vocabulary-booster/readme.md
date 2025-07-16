📚 Vocabulary Booster App
An interactive vocabulary learning app that helps users build and retain new words through structured practice and spaced repetition.

🚀 Features Overview
 + Add new words to learn:
    + Input word, meaning, example or description, topic (will be current week if user does not specify)
    + 
 + Practice through multiple-choice quizzes
    + Show word and pick 6 random meanings
    + Show meaning and pick 6 random words
    + If user answers correctly, word is marked as learned and progress increased
    + If user answers incorrectly, word is reset to previous stage
 + Use spaced repetition to review at optimal times
 + Reset progress on wrong answers to reinforce learning

📖 Use Cases
1. Add New Word
 + Add words by topic
 + Users can input new words manually or from a suggestion list
 + Users can assign a topic or tag (e.g., “Business”, “Travel”)
 + Words are added to today’s learning list and the repetition system

2. Daily Word List
 + Users can view words added or due for practice today
 + Words are grouped by learning stage (New, Due Soon, Completed)
 + Includes word, pronunciation, meaning, and example sentence

3. Topic-Based Learning
 + Users can browse or filter vocabulary by topic
 + See progress per topic (e.g., “10/20 mastered”)

4. Multiple Choice Testing
 + Users are tested on meaning or word recognition
 + 6-option multiple choice, only one correct
 + Optional "I don't know" button to skip without guessing

5. Spaced Repetition
 + Default review schedule:
    + 1st: 1 hour after learning
    + 2nd: 1 day
    + 3rd: 2 days
    + 4th: 4 days
    + 5th: 7 days
    + 6th: 16 days
    + 7th: 30 days

 + If a user answers incorrectly, the word is reset to the previous stage

6. Progress Tracking
 + See overall vocabulary size
 + Daily review streak
 + Per-word history: last reviewed, next due, number of failures

🖥️ UI Layout

🏠 Home Screen
 + Button: "Add Word"
    + Word, Optional meaning (none means default in dictionary), Topic (default to current week, W25/7/14)
 + Sections: “Words to Review Today”, “Suggested Topics”, “Recent Activity”

➕ Add Word
 + Input: Word, Meaning, Example, Topic
 + Button: “Save to My List”

📅 Word List
 + Tabs: “Today”, “By Topic”, “All Words”
 + Word cards showing: word, short meaning, next review time, progress bar

🧠 Quiz Mode
 + Question: “What is the meaning of ‘X’?”
 + 4 buttons: Answer options
 + Feedback: “Correct!” / “Wrong - Try again later”
 + Progress bar and “Next” button

📊 Progress
 + Charts: Total learned, review schedule, streak
 + List of mastered vs. struggling words

📌 Tech Stack Suggestions (optional)
 + Frontend: Tkinter
 + Backend: Flask / Django REST API
 + Database: MySQL