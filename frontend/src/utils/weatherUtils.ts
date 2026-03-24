import { WeatherCondition, WeatherTheme, ChartDataPoint } from '../types/weather';
import { TemperatureUnit } from '../context/SettingsContext';

// Weather code to condition mapping based on Open-Meteo WMO codes
export const getWeatherCondition = (code: number, isNight: boolean = false): WeatherCondition => {
  if (isNight && code < 3) return 'night';
  
  // Clear
  if (code === 0 || code === 1) return 'sunny';
  // Partly cloudy, Cloudy
  if (code >= 2 && code <= 3) return 'cloudy';
  // Fog, depositing rime fog
  if (code >= 45 && code <= 48) return 'cloudy';
  // Drizzle
  if (code >= 51 && code <= 57) return 'rainy';
  // Rain
  if (code >= 61 && code <= 67) return 'rainy';
  // Snow
  if (code >= 71 && code <= 77) return 'snowy';
  // Rain showers
  if (code >= 80 && code <= 82) return 'rainy';
  // Snow showers
  if (code >= 85 && code <= 86) return 'snowy';
  // Thunderstorm
  if (code >= 95 && code <= 99) return 'storm';
  
  return 'sunny';
};

// Get weather description from code
export const getWeatherDescription = (code: number): string => {
  const descriptions: Record<number, string> = {
    0: 'Clear sky',
    1: 'Mainly clear',
    2: 'Partly cloudy',
    3: 'Overcast',
    45: 'Foggy',
    48: 'Depositing rime fog',
    51: 'Light drizzle',
    53: 'Moderate drizzle',
    55: 'Dense drizzle',
    56: 'Light freezing drizzle',
    57: 'Dense freezing drizzle',
    61: 'Slight rain',
    63: 'Moderate rain',
    65: 'Heavy rain',
    66: 'Light freezing rain',
    67: 'Heavy freezing rain',
    71: 'Slight snow fall',
    73: 'Moderate snow fall',
    75: 'Heavy snow fall',
    77: 'Snow grains',
    80: 'Slight rain showers',
    81: 'Moderate rain showers',
    82: 'Violent rain showers',
    85: 'Slight snow showers',
    86: 'Heavy snow showers',
    95: 'Thunderstorm',
    96: 'Thunderstorm with slight hail',
    99: 'Thunderstorm with heavy hail',
  };
  return descriptions[code] || 'Unknown';
};

// Theme configurations
export const weatherThemes: Record<WeatherCondition, WeatherTheme> = {
  sunny: {
    background: 'bg-gradient-to-br from-[#4facfe] to-[#00f2fe]',
    accent: '#FFD700',
    textColor: 'text-white',
  },
  cloudy: {
    background: 'bg-gradient-to-br from-[#bdc3c7] to-[#2c3e50]',
    accent: '#ecf0f1',
    textColor: 'text-white',
  },
  rainy: {
    background: 'bg-gradient-to-br from-[#3a7bd5] to-[#3a6073]',
    accent: '#89CFF0',
    textColor: 'text-white',
  },
  snowy: {
    background: 'bg-gradient-to-br from-[#E6DADA] to-[#274046]',
    accent: '#FFFFFF',
    textColor: 'text-white',
  },
  night: {
    background: 'bg-[radial-gradient(ellipse_at_center,_var(--tw-gradient-stops))] from-[#1B2735] via-[#090a0f] to-[#000000]',
    accent: '#F0F8FF',
    textColor: 'text-white',
  },
  storm: {
    background: 'bg-gradient-to-br from-[#141E30] to-[#243B55]',
    accent: '#9D50BB',
    textColor: 'text-white',
  },
};

// Check if it's night time
export const isNightTime = (date: Date = new Date()): boolean => {
  const hours = date.getHours();
  return hours < 6 || hours >= 20;
};

// Format temperature
export const convertTemperature = (tempCelsius: number, unit: TemperatureUnit): number => {
  if (unit === 'imperial') {
    return (tempCelsius * 9) / 5 + 32;
  }
  return tempCelsius;
};

export const formatTemperature = (tempCelsius: number, unit: TemperatureUnit = 'metric'): string => {
  const converted = convertTemperature(tempCelsius, unit);
  const suffix = unit === 'imperial' ? '°F' : '°C';
  return `${Math.round(converted)}${suffix}`;
};

// Format time for hourly display
export const formatHourlyTime = (date: Date): string => {
  return date.toLocaleTimeString('en-US', { hour: 'numeric', hour12: true });
};

// Format date for daily display
export const formatDailyDate = (date: Date): string => {
  return date.toLocaleDateString('en-US', { weekday: 'short' });
};

// Format full date
export const formatFullDate = (date: Date): string => {
  return date.toLocaleDateString('en-US', { 
    weekday: 'long', 
    month: 'long', 
    day: 'numeric' 
  });
};

// Prepare chart data from hourly data
export const prepareChartData = (
  times: Date[], 
  temperatures: Float32Array | number[],
  limit: number = 24
): ChartDataPoint[] => {
  return times.slice(0, limit).map((time, index) => ({
    time: time.toISOString(),
    temperature: Math.round(temperatures[index]),
    hour: formatHourlyTime(time),
  }));
};

// Generate range array (used for API parsing)
export const range = (start: number, stop: number, step: number): number[] =>
  Array.from({ length: Math.ceil((stop - start) / step) }, (_, i) => start + i * step);
