import React, { createContext, useContext, useState } from 'react';

export const ThemeContext = createContext();

export const ThemeProvider = ({ children }) => {
  const [isDark, setIsDark] = useState(false);

  const toggleTheme = () => {
    setIsDark(!isDark);
    document.body.style.backgroundColor = !isDark ? '#333' : '#fff';
    document.body.style.color = !isDark ? '#fff' : '#333';
  };

  return (
    <ThemeContext.Provider value={{ isDark, toggleTheme }}>
      {children}
    </ThemeContext.Provider>
  );
};

const ThemeSwitcher = () => {
  const { isDark, toggleTheme } = useContext(ThemeContext);

  return (
    <button 
      onClick={toggleTheme}
      style={{
        padding: '8px 16px',
        borderRadius: '4px',
        border: 'none',
        backgroundColor: isDark ? '#fff' : '#333',
        color: isDark ? '#333' : '#fff',
        cursor: 'pointer'
      }}
    >
      Switch to {isDark ? 'Light' : 'Dark'} Mode
    </button>
  );
};

export default ThemeSwitcher;
