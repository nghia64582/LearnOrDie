import logo from './logo.svg';
import './App.css';
import { useState } from "react";
import TodoList from './components/TodoList';
import WeatherWidget from './components/WeatherWidget';
import ThemeSwitcher, { ThemeProvider } from './components/ThemeSwitcher';
import WordCard from './components/WordCard';

function App() {
  const [words, setWords] = useState([]);
  const [newWord, setNewWord] = useState({ word: '', meaning: '' });

  const addWord = (e) => {
    e.preventDefault();
    if (!newWord.word.trim() || !newWord.meaning.trim()) return;
    setWords([...words, { ...newWord, id: Date.now() }]);
    setNewWord({ word: '', meaning: '' });
  };

  const deleteWord = (id) => {
    setWords(words.filter(word => word.id !== id));
  };

  const showLog1 = () => {
    console.log("showLog1 called");
  };

  const showLog2 = () => {
    console.log("showLog2 called");
  };

  const showLog3 = () => {
    console.log("showLog3 called");
  };

  return (
    <ThemeProvider>
      <div className="App">
        <header className="App-header">
          <ThemeSwitcher />
          <img src={logo} className="App-logo" alt="logo" />
          <WeatherWidget />
          
          <div className="word-form">
            <h2>Add New Word</h2>
            <form onSubmit={addWord}>
              <input
                type="text"
                placeholder="Enter word"
                value={newWord.word}
                onChange={(e) => setNewWord({ ...newWord, word: e.target.value })}
              />
              <input
                type="text"
                placeholder="Enter meaning"
                value={newWord.meaning}
                onChange={(e) => setNewWord({ ...newWord, meaning: e.target.value })}
              />
              <button type="submit">Add Word</button>
            </form>
          </div>

          <div className="word-cards">
            {words.map(word => (
              <WordCard
                key={word.id}
                word={word.word}
                meaning={word.meaning}
                onDelete={() => deleteWord(word.id)}
              />
            ))}
          </div>

          <TodoList />
          <p onClick={showLog2}>
            Edit <code>src/App.js</code> and save to reload.
          </p>
          <a
            className="App-link"
            href="https://reactjs.org"
            target="_blank"
            rel="noopener noreferrer"
          >
            Learn React
          </a>
          <input type="button" value="Add tag" onClick={showLog1} onMouseMove={showLog3}/>
        </header>
      </div>
    </ThemeProvider>
  );
}

export default App;
