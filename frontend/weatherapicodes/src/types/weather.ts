// Weather API Response Types
export interface HourlyData {
  time: Date[];
  temperature2m: Float32Array | number[];
  weatherCode?: Float32Array | number[];
  humidity?: Float32Array | number[];
  windSpeed?: Float32Array | number[];
}

export interface DailyData {
  time: Date[];
  temperatureMax: number[];
  temperatureMin: number[];
  weatherCode: number[];
  precipitationSum?: number[];
}

export interface WeatherData {
  hourly: HourlyData;
  daily?: DailyData;
  current?: CurrentWeather;
}

export interface CurrentWeather {
  temperature: number;
  weatherCode: number;
  humidity?: number;
  windSpeed?: number;
  feelsLike?: number;
}

export interface Location {
  name: string;
  latitude: number;
  longitude: number;
}

export interface LocationData {
  enlem: number;
  boylam: number;
}

export interface FavoriteCity {
  id: string;
  name: string;
  latitude: number;
  longitude: number;
  namesByLanguage?: Record<string, string>;
}

export interface AiWeather {
  city: string | null;
  temperature: string | null;
  condition: string | null;
  humidity: string | null;
  wind: string | null;
   time: string | null;
  aiAnswer: string;
}

// Weather condition types
export type WeatherCondition = 'sunny' | 'cloudy' | 'rainy' | 'snowy' | 'storm' | 'night';

export interface WeatherTheme {
  background: string;
  accent: string;
  textColor: string;
}

// Chart data type for Recharts
export interface ChartDataPoint {
  time: string;
  temperature: number;
  hour: string;
}
