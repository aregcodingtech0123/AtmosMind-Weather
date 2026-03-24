import React, { useState, useCallback, useEffect, useMemo, useRef } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { Navbar } from './components/Navbar';
import { Seo } from './components/Seo';
import { CurrentWeatherComponent } from './components/CurrentWeather';
import { HourlyForecast } from './components/HourlyForecast';
import { DailyForecast } from './components/DailyForecast';
import { WeatherChart } from './components/WeatherChart';
import { FavoriteCities } from './components/FavoriteCities';
import { LoadingSpinner } from './components/LoadingSpinner';
import { ErrorMessage } from './components/ErrorMessage';
import { FloatingChatbot } from './components/FloatingChatbot';
import { useWeather } from './hooks/useWeather';
import { useGeolocation } from './hooks/useGeolocation';
import { useFavorites } from './hooks/useFavorites';
import { FavoriteCity, WeatherCondition, AiWeather } from './types/weather';
import type { WeatherData } from './types/weather';
import { formatTemperature, getWeatherCondition, weatherThemes, isNightTime } from './utils/weatherUtils';
import { cn } from './utils/cn';
import { Cloud, CloudRain, Snowflake, Zap, Lightbulb, Sun, Instagram, Facebook } from 'lucide-react';
import { AnimatePresence, motion } from 'framer-motion';
import { useTranslation } from 'react-i18next';
import { useSettings } from './context/SettingsContext';
import {
  fetchAiWeather as fetchAiWeatherApi,
  fetchBatchWeather,
  fetchCityAdvice,
  fetchForecastSummary,
  geocodeCity,
  reverseGeocode,
} from './services/api';
import './App.css';

/** Single source of truth for popular city names and images; used for batch request and cards. */
const POPULAR_CITIES = [
  { name: 'London, United Kingdom', image: '/cities/london.jpg' },
  { name: 'New York, United States', image: '/cities/new-york-city.jpg' },
  { name: 'Tokyo, Japan', image: '/cities/tokyo.jpg' },
  { name: 'Istanbul, Turkiye', image: '/cities/istanbul.jpg' },
  { name: 'Sydney, Australia', image: '/cities/sydney.jpg' },
  { name: 'Paris, France', image: '/cities/paris.jpg' },
  { name: 'Dubai, United Arab Emirates', image: '/cities/dubai.jpg' },
  { name: 'Bangkok, Thailand', image: '/cities/bangkok.jpg' },
  { name: 'Rome, Italy', image: '/cities/rome.jpg' },
  { name: 'Berlin, Germany', image: '/cities/berlin.jpg' },
];

export interface PopularCityWeather {
  temperature: number | null;
  condition: string | null;
  weather_code: number | null;
}

function weatherCodeToIcon(code: number) {
  const condition = getWeatherCondition(code, false);
  switch (condition) {
    case 'rainy':
      return CloudRain;
    case 'snowy':
      return Snowflake;
    case 'storm':
      return Zap;
    case 'cloudy':
    case 'night':
      return Cloud;
    default:
      return Sun;
  }
}

function App() {
  const { t } = useTranslation();
  const { currentLanguage, currentUnit } = useSettings();
  const location = useLocation();
  const navigate = useNavigate();

  const [selectedCity, setSelectedCity] = useState<string>('');
  const [latitude, setLatitude] = useState<number | null>(null);
  const [longitude, setLongitude] = useState<number | null>(null);

  const [aiWeather, setAiWeather] = useState<AiWeather | null>(null);
  const [aiLoading, setAiLoading] = useState(false);
  const [aiError, setAiError] = useState<string | null>(null);

  const [adviceLoading, setAdviceLoading] = useState(false);
  const [adviceText, setAdviceText] = useState<string | null>(null);
  const [forecastSummaryLoading, setForecastSummaryLoading] = useState(false);
  const [forecastSummaryText, setForecastSummaryText] = useState<string | null>(null);
  const forecastSummarySectionRef = useRef<HTMLDivElement>(null);
  const adviceSectionRef = useRef<HTMLDivElement>(null);

  const [popularCitiesWeather, setPopularCitiesWeather] = useState<Record<string, PopularCityWeather>>({});
  const [popularCitiesWeatherLoading, setPopularCitiesWeatherLoading] = useState(true);
  const [popularCityLabels, setPopularCityLabels] = useState<Record<string, string>>({});

  const { weatherData, loading, error, refetch } = useWeather(latitude, longitude, currentLanguage, currentUnit);
  const geolocation = useGeolocation();
  const { favorites, addFavorite, removeFavorite, isFavorite } = useFavorites();

  // Get weather condition for dynamic background
  const isNight = useMemo(() => isNightTime(), []);
  
  const getCondition = useCallback((): WeatherCondition => {
    if (weatherData?.current) {
      return getWeatherCondition(weatherData.current.weatherCode, isNight);
    }
    return isNight ? 'night' : 'sunny';
  }, [weatherData, isNight]);

  const theme = weatherThemes[getCondition()];

  const handleHomeClick = useCallback(() => {
    navigate('/', { replace: false });
    setSelectedCity('');
    setLatitude(null);
    setLongitude(null);
    setAiWeather(null);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }, [navigate]);

  const fetchAiWeather = useCallback(async (cityName: string) => {
    try {
      setAiLoading(true);
      setAiError(null);

      const data = (await fetchAiWeatherApi(cityName, currentLanguage, currentUnit)) as AiWeather;
      setAiWeather(data);
    } catch (error: any) {
      setAiError(error.message || t('messages.failedToLoadAiWeather'));
      setAiWeather(null);
    } finally {
      setAiLoading(false);
    }
  }, [currentLanguage, currentUnit, t]);

  // Handle city search: push URL and sync state so Back/Forward work
  const handleSearch = useCallback(
    (cityName: string, lat: number, lng: number) => {
      const encoded = encodeURIComponent(cityName);
      navigate(`/weather/${encoded}`, { state: { cityName, latitude: lat, longitude: lng } });
      setSelectedCity(cityName);
      setLatitude(lat);
      setLongitude(lng);
      setAdviceText(null);
      setForecastSummaryText(null);
      fetchAiWeather(cityName);
    },
    [navigate, fetchAiWeather]
  );

  // Handle geolocation
  const handleLocationRequest = useCallback(() => {
    geolocation.getCurrentLocation();
  }, [geolocation]);

  // Sync app state from URL (Back/Forward and direct /weather/:cityEncoded)
  useEffect(() => {
    const pathname = location.pathname;
    if (pathname === '/' || pathname === '') {
      setSelectedCity('');
      setLatitude(null);
      setLongitude(null);
      return;
    }
    const match = pathname.match(/^\/weather\/(.+)$/);
    if (!match) return;
    const state = location.state as { cityName?: string; latitude?: number; longitude?: number } | null;
    if (state?.cityName != null && state?.latitude != null && state?.longitude != null) {
      setSelectedCity(state.cityName);
      setLatitude(state.latitude);
      setLongitude(state.longitude);
      fetchAiWeather(state.cityName);
      return;
    }
    const cityEncoded = match[1];
    const cityName = decodeURIComponent(cityEncoded);
    setSelectedCity(cityName);
    geocodeCity(cityName.split(',')[0].trim(), currentLanguage, 1)
      .then((results) => {
        const first = results[0];
        if (first) {
          setLatitude(first.latitude);
          setLongitude(first.longitude);
          fetchAiWeather(cityName);
        }
      })
      .catch(() => {});
  }, [location.pathname, location.state, fetchAiWeather, currentLanguage]);

  // Fetch batch weather on mount when on home: city names → temperatures for top-right bubbles
  useEffect(() => {
    if (location.pathname !== '/' && location.pathname !== '') return;
    const cityNames = POPULAR_CITIES.map((c) => c.name);
    setPopularCitiesWeatherLoading(true);
    fetchBatchWeather(cityNames, currentLanguage)
      .then((data) => {
        const map: Record<string, PopularCityWeather> = {};
        const norm = (s: string) => s.trim();
        if (Array.isArray(data.results)) {
          for (const r of data.results) {
            const key = norm(r.city);
            map[key] = {
              temperature: r.temperature ?? data.temperatures?.[r.city] ?? data.temperatures?.[key] ?? null,
              condition: r.condition ?? null,
              weather_code: r.weather_code ?? null,
            };
          }
        }
        if (data.temperatures) {
          for (const [city, temp] of Object.entries(data.temperatures)) {
            const key = norm(city);
            if (!(key in map)) map[key] = { temperature: temp, condition: null, weather_code: null };
            else if (map[key].temperature == null) map[key] = { ...map[key], temperature: temp };
          }
        }
        setPopularCitiesWeather(map);
      })
      .catch(() => setPopularCitiesWeather({}))
      .finally(() => setPopularCitiesWeatherLoading(false));
  }, [location.pathname, currentLanguage]);

  useEffect(() => {
    let disposed = false;
    const localizePopularCities = async () => {
      const entries = await Promise.all(
        POPULAR_CITIES.map(async (city) => {
          const baseName = city.name.split(',')[0].trim();
          try {
            const first = (await geocodeCity(baseName, currentLanguage, 1))[0];
            if (!first?.name) return [city.name, ''] as const;
            const label = first.name
              ? first.country || first.country_code
                ? `${first.name}, ${first.country ?? first.country_code}`
                : first.name
              : '';
            return [city.name, label] as const;
          } catch {
            return [city.name, ''] as const;
          }
        })
      );
      if (!disposed) setPopularCityLabels(Object.fromEntries(entries));
    };
    localizePopularCities();
    return () => {
      disposed = true;
    };
  }, [currentLanguage]);

  useEffect(() => {
    if (latitude == null || longitude == null) return;
    let disposed = false;
    const syncSelectedCityLabel = async () => {
      try {
        const first = await reverseGeocode(latitude, longitude, currentLanguage);
        if (!first?.name || disposed) return;
        const localizedLabel =
          first.country || first.country_code
            ? `${first.name}, ${first.country ?? first.country_code}`
            : first.name;
        setSelectedCity(localizedLabel);
      } catch {
        // Keep existing selected city label on localization failures.
      }
    };
    syncSelectedCityLabel();
    return () => {
      disposed = true;
    };
  }, [currentLanguage, latitude, longitude]);

  // Update coordinates when geolocation changes
  useEffect(() => {
    if (geolocation.latitude && geolocation.longitude) {
      setLatitude(geolocation.latitude);
      setLongitude(geolocation.longitude);
      setSelectedCity(String(t('weather.myLocation')));
    }
  }, [geolocation.latitude, geolocation.longitude, t]);

  // Handle favorite toggle
  const handleToggleFavorite = useCallback(() => {
    if (selectedCity && latitude && longitude) {
      if (isFavorite(latitude, longitude)) {
        removeFavorite(`${Number(latitude).toFixed(4)},${Number(longitude).toFixed(4)}`);
      } else {
        addFavorite({
          id: `${Number(latitude).toFixed(4)},${Number(longitude).toFixed(4)}`,
          name: selectedCity,
          latitude,
          longitude,
          namesByLanguage: { [currentLanguage]: selectedCity },
        });
      }
    }
  }, [selectedCity, latitude, longitude, isFavorite, addFavorite, removeFavorite, currentLanguage]);

  // Handle favorite city selection
  const handleFavoriteSelect = useCallback((city: FavoriteCity) => {
    setSelectedCity(city.name);
    setLatitude(city.latitude);
    setLongitude(city.longitude);
  }, []);

  const buildWeatherSummary = useCallback((data: WeatherData): string => {
    const parts: string[] = [];
    if (data.current) {
      const c = data.current;
      parts.push(
        `Current: ${formatTemperature(c.temperature, currentUnit)}, humidity ${c.humidity ?? '—'}%, wind ${c.windSpeed ?? '—'} km/h, weather code ${c.weatherCode}, feels like ${formatTemperature(c.feelsLike ?? c.temperature, currentUnit)}.`
      );
    }
    if (data.hourly?.time?.length) {
      const h = data.hourly;
      const humid = h.humidity?.[0];
      const wind = h.windSpeed?.[0];
      const temp = h.temperature2m?.[0];
      parts.push(
        `Next hours signal: around ${typeof temp === 'number' ? formatTemperature(temp, currentUnit) : '—'}, humidity ${humid ?? '—'}%, wind ${wind ?? '—'} km/h.`
      );
    }
    if (data.daily?.time?.length) {
      const days = data.daily;
      const maxArr = days.temperatureMax ?? [];
      const minArr = days.temperatureMin ?? [];
      const precip = days.precipitationSum ?? [];
      const slice = Math.min(3, days.time.length);
      for (let i = 0; i < slice; i++) {
        const day = days.time[i] instanceof Date ? (days.time[i] as Date).toLocaleDateString('en-GB', { weekday: 'short' }) : `Day ${i + 1}`;
        const min = typeof minArr[i] === 'number' ? formatTemperature(minArr[i], currentUnit) : '—';
        const max = typeof maxArr[i] === 'number' ? formatTemperature(maxArr[i], currentUnit) : '—';
        parts.push(` ${day}: ${min}–${max}, precipitation ${precip[i] ?? '—'} mm.`);
      }
    }
    return parts.join('');
  }, [currentUnit]);

  const handleGetForecastSummary = useCallback(async () => {
    if (!selectedCity || !weatherData) return;
    forecastSummarySectionRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    setForecastSummaryLoading(true);
    setForecastSummaryText(null);
    try {
      const weather_summary = buildWeatherSummary(weatherData);
      const data = await fetchForecastSummary(selectedCity, weather_summary, currentLanguage, currentUnit);
      setForecastSummaryText(data.summary);
    } catch {
      setForecastSummaryText(t('messages.couldNotLoadForecastSummary'));
    } finally {
      setForecastSummaryLoading(false);
    }
  }, [selectedCity, weatherData, buildWeatherSummary, currentLanguage, currentUnit, t]);

  const handleGetAdvice = useCallback(async () => {
    if (!selectedCity || !weatherData) return;
    adviceSectionRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    setAdviceLoading(true);
    setAdviceText(null);
    try {
      const weather_summary = buildWeatherSummary(weatherData);
      const data = await fetchCityAdvice(selectedCity, weather_summary, currentLanguage, currentUnit);
      setAdviceText(data.advice);
    } catch {
      setAdviceText(t('messages.couldNotLoadAdvice'));
    } finally {
      setAdviceLoading(false);
    }
  }, [selectedCity, weatherData, buildWeatherSummary, currentLanguage, currentUnit, t]);

  const handlePopularCityClick = useCallback(
    async (fullName: string) => {
      const baseName = fullName.split(',')[0].trim();
      if (!baseName) {
        return;
      }

      try {
        const firstResult = (await geocodeCity(baseName, currentLanguage, 1))[0];
        if (!firstResult) {
          return;
        }

        handleSearch(baseName, firstResult.latitude, firstResult.longitude);
      } catch {
        // Ignore geocoding errors for quick links
      }
    },
    [handleSearch, currentLanguage]
  );

  const buildCityHref = useCallback((fullName: string) => {
    const baseName = fullName.split(',')[0].trim();
    return `/weather/${encodeURIComponent(baseName)}`;
  }, []);

  const popularCities = POPULAR_CITIES;

  const hasData = weatherData && selectedCity;
  const isLoading = loading || geolocation.loading;
  const currentPath = location.pathname || '/';
  const decodedCityFromPath = useMemo(() => {
    const match = currentPath.match(/^\/weather\/(.+)$/);
    return match ? decodeURIComponent(match[1]) : '';
  }, [currentPath]);
  const cityForTitle = (selectedCity || decodedCityFromPath || '').trim();
  const seoTitle = cityForTitle
    ? `${cityForTitle} Weather Forecast & AI Advice - AtmosMind`
    : 'AtmosMind — AI-Powered Weather Dashboard | Real-Time Forecasts & Gemini AI Assistant';
  const seoDescription = cityForTitle
    ? `Get real-time weather forecast and AI-generated advice for ${cityForTitle}. Explore temperature, wind, humidity, and practical planning insights with AtmosMind.`
    : 'AtmosMind is an AI-powered weather dashboard with real-time forecasts, city insights, and an intelligent weather assistant for smarter daily and travel planning.';
  const lastUpdatedLabel = useMemo(
    () => new Date().toLocaleString('en-US', { dateStyle: 'medium', timeStyle: 'short' }),
    []
  );
  const breadcrumbSchema = useMemo(() => {
    const homeItem = {
      '@type': 'ListItem',
      position: 1,
      name: 'Home',
      item: 'https://atmosmind.app/',
    };
    if (!cityForTitle) {
      return {
        '@type': 'BreadcrumbList',
        itemListElement: [homeItem],
      };
    }
    return {
      '@type': 'BreadcrumbList',
      itemListElement: [
        homeItem,
        {
          '@type': 'ListItem',
          position: 2,
          name: cityForTitle,
          item: `https://atmosmind.app/weather/${encodeURIComponent(cityForTitle)}`,
        },
      ],
    };
  }, [cityForTitle]);

  return (
    <div 
      className={cn(
        'min-h-screen transition-all duration-700 ease-in-out',
        theme.background,
        theme.textColor
      )}
      data-testid="weather-app"
    >
      <Seo
        title={seoTitle}
        description={seoDescription}
        path={currentPath}
        structuredData={breadcrumbSchema}
      />
      <div className="w-full px-4 pt-8 sm:px-5 md:px-8 lg:px-12">
        <Navbar
          onSearch={handleSearch}
          onLocationRequest={handleLocationRequest}
          locationLoading={geolocation.loading}
          onBrandClick={handleHomeClick}
        />
      </div>

      <div className="max-w-7xl mx-auto px-4 pb-8 sm:px-5 md:px-8 lg:px-12">
        {/* Main Content */}
        <AnimatePresence mode="wait">
          {(location.pathname === '/' || location.pathname === '') && !hasData && !isLoading && !error && (
            <motion.div
              key="welcome"
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="flex flex-col items-center justify-center py-20"
            >
              <Cloud className="w-24 h-24 text-white/30 mb-6" strokeWidth={1} />
              <h2 className="text-2xl md:text-3xl font-semibold text-white/80 mb-3 text-center font-heading">
                {t('home.welcome')}
              </h2>
              <p className="text-white/60 text-center max-w-md">
                {t('home.tagline')}
              </p>
              <div className="mt-12 w-full max-w-6xl grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {popularCities.map((city) => {
                  const cityLabel = popularCityLabels[city.name] ?? '';
                  return (
                  <a
                    key={city.name}
                    href={buildCityHref(city.name)}
                    onClick={(e: React.MouseEvent<HTMLAnchorElement>) => {
                      // Preserve native browser behavior for middle-click, modifier-click,
                      // and context-menu/open-in-new-tab while keeping enhanced left-click flow.
                      if (
                        e.defaultPrevented ||
                        e.button !== 0 ||
                        e.metaKey ||
                        e.ctrlKey ||
                        e.shiftKey ||
                        e.altKey
                      ) {
                        return;
                      }
                      e.preventDefault();
                      handlePopularCityClick(city.name);
                    }}
                    className={cn(
                      'group relative flex flex-col rounded-3xl overflow-hidden',
                      'min-h-[220px] sm:min-h-[260px]',
                      'shadow-lg shadow-black/20 hover:shadow-xl hover:shadow-white/10',
                      'transition-all duration-500 ease-out',
                      'hover:scale-[1.03] focus:outline-none focus:ring-2 focus:ring-white/60 focus:ring-offset-2 focus:ring-offset-transparent',
                      'no-underline text-inherit'
                    )}
                    aria-label={String(t('home.openWeatherDetails', { city: cityLabel || city.name }))}
                  >
                    {/* Full-bleed background image with zoom on hover */}
                    <div className="absolute inset-0 overflow-hidden">
                      <img
                        src={city.image}
                        alt={cityLabel || city.name}
                        className="absolute inset-0 w-full h-full object-cover transition-transform duration-500 ease-out group-hover:scale-110"
                        loading="lazy"
                      />
                      {/* Dark gradient overlay for text readability */}
                      <div
                        className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/20 to-transparent"
                        aria-hidden
                      />
                    </div>

                    {/* Weather context: temp + icon (top right) — bound to cityData by city.name */}
                    <div
                      className={cn(
                        'absolute top-4 right-4 flex items-center gap-2 px-3 py-2 rounded-2xl min-w-[4.5rem] justify-center',
                        'bg-white/15 backdrop-blur-md border border-white/20',
                        'text-white font-semibold text-sm'
                      )}
                    >
                      {popularCitiesWeatherLoading ? (
                        <span className="animate-pulse text-white/80">...</span>
                      ) : (() => {
                          const cityData = popularCitiesWeather;
                          const key = city.name.trim();
                          const data = cityData[city.name] ?? cityData[key];
                          const temp = data?.temperature;
                          const code = data?.weather_code ?? 0;
                          const Icon = weatherCodeToIcon(code);
                          return (
                            <>
                              <Icon className="w-5 h-5 text-amber-200" strokeWidth={1.5} aria-hidden />
                              <span>{temp != null && Number.isFinite(temp) ? formatTemperature(temp, currentUnit) : '—'}</span>
                            </>
                          );
                        })()}
                    </div>

                    {/* Glassmorphism bottom overlay: city name */}
                    <div
                      className={cn(
                        'absolute bottom-0 left-0 right-0 p-5',
                        'bg-white/10 backdrop-blur-md border-t border-white/10'
                      )}
                    >
                      <p className="text-white font-semibold text-lg tracking-tight drop-shadow-sm">
                        {cityLabel || t('home.cityLoading')}
                      </p>
                    </div>
                  </a>
                );
                })}
              </div>
            </motion.div>
          )}

          {isLoading && (
            <motion.div
              key="loading"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
            >
              <LoadingSpinner />
            </motion.div>
          )}

          {error && (
            <motion.div
              key="error"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
            >
              <ErrorMessage message={error} onRetry={refetch} />
            </motion.div>
          )}

          {geolocation.error && (
            <motion.div
              key="geo-error"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
            >
              <ErrorMessage message={geolocation.error} />
            </motion.div>
          )}

          {hasData && !isLoading && (
            <motion.div
              key="content"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="grid grid-cols-12 gap-6"
            >
              {/* Current Weather */}
              {weatherData.current && (
                <CurrentWeatherComponent
                  data={weatherData.current}
                  cityName={selectedCity}
                  isFavorite={latitude != null && longitude != null ? isFavorite(latitude, longitude) : false}
                  onToggleFavorite={handleToggleFavorite}
                />
              )}

              {/* Get Advice button — scrolls to advice section and fetches AI advice */}
              <div className="col-span-12 flex justify-center gap-3 flex-wrap">
                <button
                  type="button"
                  onClick={handleGetForecastSummary}
                  className={cn(
                    'inline-flex items-center gap-2 px-5 py-2.5 rounded-full',
                    'bg-white/15 hover:bg-white/25 text-white font-medium',
                    'transition-colors focus:outline-none focus:ring-2 focus:ring-white/60'
                  )}
                >
                  <Sun className="w-5 h-5" strokeWidth={1.5} />
                  {t('actions.weatherForecast')}
                </button>
                <button
                  type="button"
                  onClick={handleGetAdvice}
                  className={cn(
                    'inline-flex items-center gap-2 px-5 py-2.5 rounded-full',
                    'bg-white/15 hover:bg-white/25 text-white font-medium',
                    'transition-colors focus:outline-none focus:ring-2 focus:ring-white/60'
                  )}
                >
                  <Lightbulb className="w-5 h-5" strokeWidth={1.5} />
                  {t('actions.getAdvice')}
                </button>
              </div>

              

              {/* Hourly Forecast */}
              {weatherData.hourly && (
                <HourlyForecast data={weatherData.hourly} limit={24} />
              )}

              {/* Weather Chart */}
              {weatherData.hourly && (
                <WeatherChart data={weatherData.hourly} limit={24} />
              )}

              {/* Daily Forecast */}
              {weatherData.daily && (
                <DailyForecast data={weatherData.daily} />
              )}

              {/* AI advice section (scroll target for "Get Advice" button) */}
              <div
                id="forecast-summary-section"
                ref={forecastSummarySectionRef}
                className="col-span-12"
              >
                <div className="bg-black/30 backdrop-blur-md rounded-3xl border border-white/10 p-6 text-white">
                  <h3 className="text-lg font-semibold mb-3">{t('sections.detailedForecastSummary')}</h3>
                  <p className="text-xs text-white/55 mb-3">
                    {t('sections.lastUpdated')}: {lastUpdatedLabel}
                  </p>
                  {forecastSummaryLoading && (
                    <p className="text-sm text-white/70">{t('sections.generatingForecastSummary')}</p>
                  )}
                  {!forecastSummaryLoading && forecastSummaryText && (
                    <p className="text-white/90 whitespace-pre-line text-sm leading-relaxed">
                      {forecastSummaryText}
                    </p>
                  )}
                  {!forecastSummaryLoading && !forecastSummaryText && (
                    <p className="text-sm text-white/60">
                      {t('sections.clickWeatherForecastHint')}
                    </p>
                  )}
                </div>
              </div>

              {/* AI advice section (scroll target for "Get Advice" button) */}
              <div
                id="city-advice-section"
                ref={adviceSectionRef}
                className="col-span-12"
              >
                <div className="bg-black/30 backdrop-blur-md rounded-3xl border border-white/10 p-6 text-white">
                  <h3 className="text-lg font-semibold mb-3">{t('sections.personalizedAdviceFor', { city: selectedCity })}</h3>
                  <p className="text-xs text-white/55 mb-3">
                    {t('sections.lastUpdated')}: {lastUpdatedLabel}
                  </p>
                  {adviceLoading && (
                    <p className="text-sm text-white/70">{t('sections.gettingAdvice')}</p>
                  )}
                  {!adviceLoading && adviceText && (
                    <p className="text-white/90 whitespace-pre-line text-sm leading-relaxed">
                      {adviceText}
                    </p>
                  )}
                  {!adviceLoading && !adviceText && (
                    <p className="text-sm text-white/60">
                      {t('sections.clickGetAdviceHint')}
                    </p>
                  )}
                </div>
              </div>

              {/* Favorite Cities */}
              <FavoriteCities
                favorites={favorites}
                onSelect={handleFavoriteSelect}
                onRemove={removeFavorite}
                currentCity={selectedCity}
              />

              
            </motion.div>
          )}
        </AnimatePresence>

        {/* Footer */}
        <motion.footer
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.5 }}
          className={cn(
            'mt-14 overflow-hidden rounded-3xl',
            'bg-black/35 backdrop-blur-md border border-white/10'
          )}
        >
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-8 px-6 py-8 md:px-8 md:py-10">
            <div className="space-y-4">
              <div className="flex items-center gap-3">
                <img
                  src="/AtmosMindLogo.png"
                  alt="AtmosMind"
                  className="h-8 w-auto object-contain"
                />
                <h3 className="text-lg font-semibold text-white">AtmosMind</h3>
              </div>
              <p className="text-sm leading-relaxed text-white/65">
                {t('footer.brandTagline')}
              </p>
            </div>

            <div className="space-y-3">
              <h4 className="text-sm font-semibold uppercase tracking-wide text-white/80">{t('footer.quickLinks')}</h4>
              <div className="flex flex-col gap-2 text-sm">
                <Link to="/" className="text-white/65 hover:text-cyan-300 transition-colors duration-200">{t('footer.home')}</Link>
                <Link to="/about" className="text-white/65 hover:text-cyan-300 transition-colors duration-200">{t('footer.aboutUs')}</Link>
              </div>
            </div>

            <div className="space-y-3">
              <h4 className="text-sm font-semibold uppercase tracking-wide text-white/80">{t('footer.resources')}</h4>
              <div className="flex flex-col gap-2 text-sm">
                <Link to="/privacy" className="text-white/65 hover:text-cyan-300 transition-colors duration-200">{t('footer.privacyPolicy')}</Link>
              </div>
            </div>

            <div className="space-y-4">
              <h4 className="text-sm font-semibold uppercase tracking-wide text-white/80">{t('footer.connect')}</h4>
              <div className="flex items-center gap-3">
                <a
                  href="https://instagram.com"
                  target="_blank"
                  rel="noreferrer"
                  className={cn(
                    'inline-flex h-9 w-9 items-center justify-center rounded-full',
                    'bg-white/10 text-white/75 hover:text-cyan-300 hover:bg-white/15',
                    'transition-colors duration-200'
                  )}
                  aria-label={String(t('footer.instagram'))}
                >
                  <Instagram className="h-4 w-4" />
                </a>
                <a
                  href="https://facebook.com"
                  target="_blank"
                  rel="noreferrer"
                  className={cn(
                    'inline-flex h-9 w-9 items-center justify-center rounded-full',
                    'bg-white/10 text-white/75 hover:text-cyan-300 hover:bg-white/15',
                    'transition-colors duration-200'
                  )}
                  aria-label={String(t('footer.facebook'))}
                >
                  <Facebook className="h-4 w-4" />
                </a>
              </div>
              
            </div>
          </div>

          <div className="border-t border-white/10 px-6 py-4 text-center text-xs text-white/50 md:px-8">
            {t('footer.copyright')}
          </div>
        </motion.footer>
      </div>

      <FloatingChatbot />
    </div>
  );
}

export default App;
