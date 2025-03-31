import React, { useState } from 'react';

const WordCard = ({ word, meaning, onDelete }) => {
  const [isFlipped, setIsFlipped] = useState(false);
  const [isFavorite, setIsFavorite] = useState(false);

  const handleSpell = () => {
    const utterance = new SpeechSynthesisUtterance(word);
    window.speechSynthesis.speak(utterance);
  };

  const handleFlip = () => {
    setIsFlipped(!isFlipped);
  };

  const toggleFavorite = () => {
    setIsFavorite(!isFavorite);
  };

  return (
    <div className={`word-card ${isFlipped ? 'flipped' : ''}`}>
      <div className="word-card-inner">
        <div className="word-card-front">
          <h3>{word}</h3>
          <div className="word-card-buttons">
            <button onClick={handleSpell} className="spell-btn">
              🔊 Spell
            </button>
            <button onClick={handleFlip} className="flip-btn">
              🔄 Show Meaning
            </button>
            <button onClick={toggleFavorite} className="favorite-btn">
              {isFavorite ? '❤️' : '🤍'} Favorite
            </button>
            <button onClick={onDelete} className="delete-btn">
              🗑️ Delete
            </button>
          </div>
        </div>
        <div className="word-card-back">
          <h3>Meaning:</h3>
          <p>{meaning}</p>
          <button onClick={handleFlip} className="flip-btn">
            🔄 Show Word
          </button>
        </div>
      </div>
    </div>
  );
};

export default WordCard;
