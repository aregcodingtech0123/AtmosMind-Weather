import { useState, useEffect, useCallback } from 'react';
import { fetchWeatherApi } from 'openmeteo';
import { WeatherData, CurrentWeather } from '../types/weather';
import { range } from '../utils/weatherUtils';

interface UseWeatherReturn {
  weatherData: WeatherData | null;
  loading: boolean;
  error: string | null;
  refetch: () => void;
}

export const useWeather = (
  latitude: number | null, 
  longitude: number | null,
  language: string,
  unit: 'metric' | 'imperial'
): UseWeatherReturn => {
  const [weatherData, setWeatherData] = useState<WeatherData | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    if (latitude === null || longitude === null) {
      setWeatherData(null);
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const url = 'https://api.open-meteo.com/v1/forecast';
      const params = {
        latitude,
        longitude,
        temperature_unit: unit === 'imperial' ? 'fahrenheit' : 'celsius',
        current: ['temperature_2m', 'weather_code', 'relative_humidity_2m', 'wind_speed_10m', 'apparent_temperature'],
        hourly: ['temperature_2m', 'weather_code', 'relative_humidity_2m', 'wind_speed_10m'],
        daily: ['weather_code', 'temperature_2m_max', 'temperature_2m_min', 'precipitation_sum'],
        timezone: 'auto',
        language,
        forecast_days: 7,
      };

      const responses = await fetchWeatherApi(url, params);
      const response = responses[0];

      const utcOffsetSeconds = response.utcOffsetSeconds();
      const current = response.current()!;
      const hourly = response.hourly()!;
      const daily = response.daily()!;

      // Parse current weather
      const currentWeather: CurrentWeather = {
        temperature: current.variables(0)!.value(),
        weatherCode: current.variables(1)!.value(),
        humidity: current.variables(2)!.value(),
        windSpeed: current.variables(3)!.value(),
        feelsLike: current.variables(4)!.value(),
      };

      // Parse hourly data
      const hourlyTimes = range(
        Number(hourly.time()), 
        Number(hourly.timeEnd()), 
        hourly.interval()
      ).map((t) => new Date((t + utcOffsetSeconds) * 1000));

      // Parse daily data
      const dailyTimes = range(
        Number(daily.time()), 
        Number(daily.timeEnd()), 
        daily.interval()
      ).map((t) => new Date((t + utcOffsetSeconds) * 1000));

      const data: WeatherData = {
        current: currentWeather,
        hourly: {
          time: hourlyTimes,
          temperature2m: hourly.variables(0)!.valuesArray()!,
          weatherCode: hourly.variables(1)!.valuesArray()!,
          humidity: hourly.variables(2)!.valuesArray()!,
          windSpeed: hourly.variables(3)!.valuesArray()!,
        },
        daily: {
          time: dailyTimes,
          weatherCode: Array.from(daily.variables(0)!.valuesArray()!),
          temperatureMax: Array.from(daily.variables(1)!.valuesArray()!),
          temperatureMin: Array.from(daily.variables(2)!.valuesArray()!),
          precipitationSum: Array.from(daily.variables(3)!.valuesArray()!),
        },
      };

      setWeatherData(data);
    } catch (err) {
      console.error('Weather fetch error:', err);
      setError('Failed to fetch weather data. Please try again.');
      setWeatherData(null);
    } finally {
      setLoading(false);
    }
  }, [latitude, longitude, language, unit]);

  useEffect(() => {
    fetchData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [latitude, longitude, language, unit]);

  return { weatherData, loading, error, refetch: fetchData };
};
