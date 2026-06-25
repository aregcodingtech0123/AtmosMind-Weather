import type { LifestyleIndices, WeatherData } from '../types/weather';

/** Raw weather slice from POST /api/weather/detail */
export interface WeatherDetailWeatherApi {
  current: {
    temperature: number;
    weather_code: number;
    humidity: number | null;
    wind_speed: number | null;
    feels_like: number | null;
  } | null;
  hourly: {
    time: string[];
    temperature_2m: number[];
    weather_code: number[];
    relative_humidity_2m: number[];
    wind_speed_10m: number[];
  };
  daily: {
    time: string[];
    weather_code: number[];
    temperature_2m_max: number[];
    temperature_2m_min: number[];
    precipitation_sum: number[];
  } | null;
}

export interface WeatherDetailApiResponse {
  latitude: number;
  longitude: number;
  weather: WeatherDetailWeatherApi;
  lifestyle_indices: LifestyleIndices;
}

export function mapWeatherDetailToWeatherData(weather: WeatherDetailWeatherApi): WeatherData {
  const hourlyTimes = weather.hourly.time.map((iso) => new Date(iso));

  const data: WeatherData = {
    hourly: {
      time: hourlyTimes,
      temperature2m: weather.hourly.temperature_2m,
      weatherCode: weather.hourly.weather_code,
      humidity: weather.hourly.relative_humidity_2m,
      windSpeed: weather.hourly.wind_speed_10m,
    },
  };

  if (weather.current) {
    data.current = {
      temperature: weather.current.temperature,
      weatherCode: weather.current.weather_code,
      humidity: weather.current.humidity ?? undefined,
      windSpeed: weather.current.wind_speed ?? undefined,
      feelsLike: weather.current.feels_like ?? undefined,
    };
  }

  if (weather.daily) {
    data.daily = {
      time: weather.daily.time.map((iso) => new Date(iso)),
      weatherCode: weather.daily.weather_code,
      temperatureMax: weather.daily.temperature_2m_max,
      temperatureMin: weather.daily.temperature_2m_min,
      precipitationSum: weather.daily.precipitation_sum,
    };
  }

  return data;
}
