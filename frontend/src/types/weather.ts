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

export type LifestylePollenLevel = 'low' | 'medium' | 'high' | 'unknown';
export type LifestyleAqiCategory =
  | 'good'
  | 'fair'
  | 'moderate'
  | 'poor'
  | 'very_poor'
  | 'hazardous'
  | 'unknown';
export type LifestyleUvCategory =
  | 'low'
  | 'moderate'
  | 'high'
  | 'very_high'
  | 'extreme'
  | 'unknown';

export interface LifestylePollenMetrics {
  birch: number | null;
  grass: number | null;
  ragweed: number | null;
  level: LifestylePollenLevel;
}

export interface LifestyleIndices {
  latitude: number;
  longitude: number;
  timezone: string | null;
  observed_at: string | null;
  european_aqi: number | null;
  us_aqi: number | null;
  aqi_value: number | null;
  aqi_standard: 'european' | 'us' | 'none';
  aqi_category: LifestyleAqiCategory;
  uv_index: number | null;
  uv_category: LifestyleUvCategory;
  pollen: LifestylePollenMetrics;
  visibility_meters: number | null;
  dew_point_celsius: number | null;
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
