import React, { useState, useEffect } from 'react';

const WeatherWidget = () => {
  const [weather, setWeather] = useState({
    temperature: 25,
    condition: 'Sunny',
    humidity: 60
  });

  useEffect(() => {
    // Simulate weather changes every 5 seconds
    const interval = setInterval(() => {
      const conditions = ['Sunny', 'Cloudy', 'Rainy', 'Windy'];
      const randomCondition = conditions[Math.floor(Math.random() * conditions.length)];
      const randomTemp = Math.floor(Math.random() * (35 - 15) + 15);
      const randomHumidity = Math.floor(Math.random() * (80 - 40) + 40);

      setWeather({
        temperature: randomTemp,
        condition: randomCondition,
        humidity: randomHumidity
      });
    }, 5000);

    return () => clearInterval(interval);
  }, []);

  return (
    <div className="weather-widget">
      <h3>Weather Info</h3>
      <div className="weather-info">
        <p>Temperature: {weather.temperature}°C</p>
        <p>Condition: {weather.condition}</p>
        <p>Humidity: {weather.humidity}%</p>
      </div>
    </div>
  );
};

export default WeatherWidget;
