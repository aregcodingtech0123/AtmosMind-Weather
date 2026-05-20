import React, { Suspense, lazy, useState, useCallback, useEffect, useMemo, useRef } from 'react';
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
import { MarkdownMessage } from './components/MarkdownMessage';
import { CookieConsent } from './components/CookieConsent';
import { useWeather } from './hooks/useWeather';
import { useGeolocation } from './hooks/useGeolocation';
import { useFavorites } from './hooks/useFavorites';

import { FavoriteCity, WeatherCondition, AiWeather } from './types/weather';
import type { WeatherData } from './types/weather';
import { formatTemperature, getWeatherCondition, weatherThemes, isNightTime } from './utils/weatherUtils';
import { cn } from './utils/cn';
import { Cloud, CloudRain, Snowflake, Zap, Lightbulb, Sun, Instagram, Facebook, RefreshCw } from 'lucide-react';
import { AnimatePresence, motion } from 'framer-motion';
import { useTranslation } from 'react-i18next';
import { SupportedLanguage, useSettings } from './context/SettingsContext';
import { fetchWeatherApi } from 'openmeteo';
import {
  fetchAiWeather as fetchAiWeatherApi,
  fetchCityAdvice,
  fetchForecastSummary,
  geocodeCity,
  reverseGeocode,
} from './services/api';
import './App.css';

import { POPULAR_CITIES, PopularCity } from './data/popularCities';
import { sanitizeDisplayText } from './utils/sanitize';

/** Dynamically resolves the image path for a given city based on its ID. */
export function getCityImagePath(cityId: string): string {
  return `/cities/${cityId}.avif`;
}

/** Type definition for weather data specific to a popular city card. */
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

const FloatingChatbot = lazy(() =>
  import('./components/FloatingChatbot').then((m) => ({ default: m.FloatingChatbot }))
);

function App() {
  const { t, i18n } = useTranslation();
  const { currentLanguage, currentUnit } = useSettings();
  const location = useLocation();
  const navigate = useNavigate();
  // Safe helper to sanitize the locale key exactly as requested
  const langKey = (i18n.language || currentLanguage).split('-')[0] as SupportedLanguage;


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
  const [popularCitiesWeatherError, setPopularCitiesWeatherError] = useState(false);
  const [visibleCount, setVisibleCount] = useState(6);

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
    const cityName = sanitizeDisplayText(decodeURIComponent(cityEncoded), 120);
    if (!cityName) return;
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
      .catch(() => { });
  }, [location.pathname, location.state, fetchAiWeather, currentLanguage]);

  // Fetch batch weather on mount when on home: city names → temperatures for top-right bubbles
  const fetchPopularBatch = useCallback(async () => {
    setPopularCitiesWeatherLoading(true);
    setPopularCitiesWeatherError(false);

    try {
      const cacheKey = `atmosmind_popular_weather_cache_${currentLanguage}_${currentUnit}`;
      const cached = localStorage.getItem(cacheKey);
      if (cached) {
        try {
          const parsed = JSON.parse(cached);
          if (Date.now() - parsed.timestamp < 15 * 60 * 1000) {
            setPopularCitiesWeather(parsed.data);
            setPopularCitiesWeatherLoading(false);
            return;
          }
        } catch {
          // ignore cache parse error
        }
      }

      const lats = POPULAR_CITIES.map((c) => c.latitude);
      const lons = POPULAR_CITIES.map((c) => c.longitude);

      const url = 'https://api.open-meteo.com/v1/forecast';
      const params = {
        latitude: lats,
        longitude: lons,
        temperature_unit: currentUnit === 'imperial' ? 'fahrenheit' : 'celsius',
        current: ['temperature_2m', 'weather_code'],
        timezone: 'auto'
      };

      const responses = await fetchWeatherApi(url, params);
      const map: Record<string, PopularCityWeather> = {};

      responses.forEach((response, i) => {
        const current = response.current()!;
        const temp = current.variables(0)!.value();
        const code = current.variables(1)!.value();
        map[POPULAR_CITIES[i].id] = {
          temperature: temp,
          condition: null,
          weather_code: code
        };
      });

      setPopularCitiesWeather(map);
      localStorage.setItem(cacheKey, JSON.stringify({
        data: map,
        timestamp: Date.now()
      }));
    } catch (err) {
      console.error('Batch weather fetch error:', err);
      setPopularCitiesWeatherError(true);
      setPopularCitiesWeather({});
    } finally {
      setPopularCitiesWeatherLoading(false);
    }
  }, [currentLanguage, currentUnit]);

  useEffect(() => {
    if (location.pathname !== '/' && location.pathname !== '') return;
    fetchPopularBatch();
  }, [location.pathname, fetchPopularBatch]);

  // Update coordinates when geolocation changes and reverse-geocode to get actual city name.
  // Performs reverse geocoding directly here instead of via a separate hook to avoid
  // timing / re-render issues with refs.
  useEffect(() => {
    if (!geolocation.latitude || !geolocation.longitude) return;

    const lat = geolocation.latitude;
    const lng = geolocation.longitude;

    // Set coordinates immediately so weather data starts loading
    setLatitude(lat);
    setLongitude(lng);
    // Show placeholder while reverse geocoding runs
    setSelectedCity(String(t('weather.myLocation') || 'Current Location'));

    // Perform reverse geocoding to resolve the actual city name
    let cancelled = false;
    reverseGeocode(lat, lng, currentLanguage)
      .then((result) => {
        if (cancelled) return;

        if (result?.name) {
          const parts = [result.name];
          if (result.admin1 && result.admin1 !== result.name) {
            parts.push(result.admin1);
          }
          if (result.country) {
            parts.push(result.country);
          } else if (result.country_code) {
            parts.push(result.country_code);
          }
          const resolvedName = parts.join(', ');
          setSelectedCity(resolvedName);
          fetchAiWeather(resolvedName);
        } else {
          // Fallback: keep the placeholder and fetch AI weather with it
          const fallback = String(t('weather.myLocation') || 'Current Location');
          setSelectedCity(fallback);
        }
      })
      .catch(() => {
        if (cancelled) return;
        // On error, keep the placeholder
        console.warn('Reverse geocoding failed, keeping placeholder name');
      });

    return () => { cancelled = true; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [geolocation.latitude, geolocation.longitude, currentLanguage]);

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
    if (!match) return '';
    try {
      return sanitizeDisplayText(decodeURIComponent(match[1]), 120);
    } catch {
      return '';
    }
  }, [currentPath]);
  const cityForTitle = sanitizeDisplayText(selectedCity || decodedCityFromPath, 120);
  const seoTitle = cityForTitle
    ? `${cityForTitle} Weather Forecast & AI Advice - AtmosMind`
    : 'AtmosMind';
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
      <CookieConsent />
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

              {/* Daily Weather Insight (static, visible by default for content richness) */}

              <div className="mt-12 w-full max-w-[1600px] grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 p-4">
                <AnimatePresence>
                  {popularCities.slice(0, visibleCount).map((city, index) => {
                    const cityLabel = city.names[langKey] || city.names['en'] || city.defaultName;
                    // Performance: First row of cities (top 3 on desktop) are optimized as LCP items.
                    const isLcp = index < 3;

                    return (
                      <motion.a
                        layout
                        initial={{ opacity: 0, scale: 0.9 }}
                        animate={{ opacity: 1, scale: 1 }}
                        exit={{ opacity: 0, scale: 0.9 }}
                        transition={{ duration: 0.3 }}
                        key={city.id}
                        href={buildCityHref(city.defaultName)}
                        onClick={(e: React.MouseEvent<HTMLAnchorElement>) => {
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
                          handlePopularCityClick(cityLabel);
                        }}
                        className={cn(
                          'group relative flex flex-col rounded-2xl overflow-hidden',
                          'aspect-[4/3] w-full',
                          'shadow-lg shadow-black/20 hover:shadow-2xl hover:shadow-black/40',
                          'transition-all duration-300 ease-out',
                          'hover:scale-[1.03] focus:outline-none focus:ring-2 focus:ring-white/60 focus:ring-offset-2 focus:ring-offset-transparent',
                          'no-underline text-inherit'
                        )}
                        aria-label={String(t('home.openWeatherDetails', { city: cityLabel }))}
                      >
                        {/* City Background Image */}
                        <div className="absolute inset-0 overflow-hidden bg-slate-800">
                          <img
                            src={getCityImagePath(city.id)}
                            alt={cityLabel}
                            width={1280}
                            height={1000}
                            className="absolute inset-0 w-full h-full object-cover transition-transform duration-500 ease-out group-hover:scale-110"

                            loading={isLcp ? 'eager' : 'lazy'}
                            // @ts-ignore - fetchPriority is supported in modern browsers but missing from some React types
                            fetchpriority={isLcp ? 'high' : 'auto'}
                            onError={(e) => {
                              e.currentTarget.style.display = 'none';
                            }}
                          />
                          {/* Readable Overlay: Subtle gradient for text contrast */}
                          <div className="absolute inset-x-0 bottom-0 h-1/2 bg-gradient-to-t from-black/80 via-black/30 to-transparent pointer-events-none" />
                        </div>

                        {/* Weather context: temp + icon (top right) */}
                        <div
                          className={cn(
                            'absolute top-4 right-4 flex items-center gap-2 px-3 py-2 rounded-xl min-w-[4.5rem] justify-center h-[40px]',
                            'bg-white/20 backdrop-blur-md border border-white/30 shadow-[0_0_15px_rgba(255,255,255,0.2)]',
                            'text-white font-bold text-base z-10'
                          )}
                        >
                          {popularCitiesWeatherLoading ? (
                            <span className="animate-pulse text-white/80">...</span>
                          ) : popularCitiesWeatherError ? (
                            <button
                              onClick={(e) => { e.preventDefault(); e.stopPropagation(); fetchPopularBatch(); }}
                              className="flex items-center justify-center p-1 rounded-full hover:bg-white/25 hover:rotate-180 transition-all duration-300"
                              aria-label="Retry weather fetch"
                            >
                              <RefreshCw className="w-4 h-4 text-white/90" />
                            </button>
                          ) : (() => {
                            const cityData = popularCitiesWeather;
                            const data = cityData[city.id];
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

                        {/* City name */}
                        <div className="absolute bottom-0 left-0 right-0 p-5 sm:p-6 z-10 transition-opacity duration-300">
                          <p className="text-white font-bold text-lg sm:text-xl md:text-2xl tracking-tight drop-shadow-md">
                            {cityLabel}
                          </p>
                        </div>
                      </motion.a>
                    );
                  })}
                </AnimatePresence>
              </div>

              <div className="mt-8 flex flex-col md:flex-row justify-center gap-4">
                {visibleCount < popularCities.length && (
                  <button
                    onClick={() => setVisibleCount((prev) => Math.min(prev + 6, popularCities.length))}
                    className="px-6 py-3 rounded-full bg-white/10 hover:bg-white/20 border border-white/20 text-white font-medium transition-all duration-300 w-full md:w-auto"
                  >
                    {String(t('common.showMore', 'Show More'))}
                  </button>
                )}
                {visibleCount > 6 && (
                  <button
                    onClick={() => setVisibleCount(6)}
                    className="px-6 py-3 rounded-full bg-black/20 hover:bg-black/30 backdrop-blur-md border border-white/10 text-white font-medium transition-all duration-300 w-full md:w-auto"
                  >
                    {String(t('common.showLess', 'Show Less'))}
                  </button>
                )}
              </div>

              <div className="mt-16 w-full max-w-3xl">
                <div className="rounded-3xl border border-white/10 bg-black/30 backdrop-blur-md p-6">
                  <h3 className="text-lg md:text-xl font-semibold text-white/90 mb-3">
                    {t('home.insights.title')}
                  </h3>
                  <p className="text-sm md:text-base text-white/70 leading-7">
                    {t('home.insights.mainText')}
                  </p>
                  <ul className="mt-4 list-disc pl-6 space-y-2 text-sm md:text-base text-white/70 leading-7">
                    <li>
                      <span className="text-white/85 font-medium">{t('home.insights.windTitle')}</span> {t('home.insights.windText')}
                    </li>
                    <li>
                      <span className="text-white/85 font-medium">{t('home.insights.humidityTitle')}</span> {t('home.insights.humidityText')}
                    </li>
                    <li>
                      <span className="text-white/85 font-medium">{t('home.insights.rainTitle')}</span> {t('home.insights.rainText')}
                    </li>
                    <li>
                      <span className="text-white/85 font-medium">{t('home.insights.dressTitle')}</span> {t('home.insights.dressText')}
                    </li>
                  </ul>
                  <p className="mt-4 text-xs text-white/50 leading-6">
                    {t('home.insights.tip')}
                  </p>
                </div>
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
                  <Sun className="w-5 h-5 shrink-0" strokeWidth={1.5} aria-hidden />
                  <span>{t('actions.weatherForecast')}</span>
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
                  <Lightbulb className="w-5 h-5 shrink-0" strokeWidth={1.5} aria-hidden />
                  <span>{t('actions.getAdvice')}</span>
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
                    <MarkdownMessage content={forecastSummaryText} />
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
                  <p className="text-xs text-white/55 mb-3">
                    {String(t('disclaimer.aiGenerated', { defaultValue: 'AI-generated content. May be inaccurate—verify for critical decisions.' }))}
                  </p>
                  {adviceLoading && (
                    <p className="text-sm text-white/70">{t('sections.gettingAdvice')}</p>
                  )}
                  {!adviceLoading && adviceText && (
                    <MarkdownMessage content={adviceText} />
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
          <div className="px-6 py-8 md:px-8 md:py-10">
            <div className="flex flex-col gap-6 sm:flex-row sm:items-start sm:justify-between">
              <div className="space-y-4">
                <div className="flex items-center gap-3">
                  <img
                    src="/AtmosMindLogo.webp"
                    alt="AtmosMind"
                    className="h-8 w-auto object-contain"
                  />
                  <h3 className="text-lg font-semibold text-white">AtmosMind</h3>
                </div>
                <p className="text-sm leading-relaxed text-white/65">
                  {t('footer.brandTagline')}
                </p>
              </div>

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
                  <Instagram className="h-4 w-4" aria-hidden />
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
                  <Facebook className="h-4 w-4" aria-hidden />
                </a>
              </div>
            </div>

            <div className="mt-8 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-8">
              {/* Column 1: Legal */}
              <div className="space-y-3">
                <h4 className="text-sm font-semibold uppercase tracking-wide text-white/80">
                  {t('footer.sections.legal')}
                </h4>
                <div className="flex flex-col gap-2 text-sm">
                  <Link to="/privacy" className="text-white/65 hover:text-cyan-300 transition-colors duration-200">
                    {t('footer.privacyPolicy')}
                  </Link>
                  <Link to="/terms" className="text-white/65 hover:text-cyan-300 transition-colors duration-200">
                    {t('footer.terms')}
                  </Link>
                  <Link to="/cookies" className="text-white/65 hover:text-cyan-300 transition-colors duration-200">
                    {t('footer.cookiePolicy')}
                  </Link>
                </div>
              </div>

              {/* Column 2: Weather Guides */}
              <div className="space-y-3">
                <h4 className="text-sm font-semibold uppercase tracking-wide text-white/80">
                  {t('footer.sections.guides')}
                </h4>
                <div className="flex flex-col gap-2 text-sm">
                  <Link to="/guides/humidity" className="text-white/65 hover:text-cyan-300 transition-colors duration-200">
                    {t('footer.guides.humidity')}
                  </Link>
                  <Link to="/guides/wind-chill" className="text-white/65 hover:text-cyan-300 transition-colors duration-200">
                    {t('footer.guides.windChill')}
                  </Link>
                  <Link to="/guides/what-to-wear" className="text-white/65 hover:text-cyan-300 transition-colors duration-200">
                    {t('footer.guides.whatToWear')}
                  </Link>
                  <Link to="/guides/thunderstorm-safety" className="text-white/65 hover:text-cyan-300 transition-colors duration-200">
                    {t('footer.guides.thunderstorm')}
                  </Link>
                  <Link to="/guides/uv-index" className="text-white/65 hover:text-cyan-300 transition-colors duration-200">
                    {t('footer.guides.uvIndex')}
                  </Link>
                </div>
              </div>

              {/* Column 3: Support */}
              <div className="space-y-3">
                <h4 className="text-sm font-semibold uppercase tracking-wide text-white/80">
                  {t('footer.sections.support')}
                </h4>
                <div className="flex flex-col gap-2 text-sm">
                  <Link to="/about" className="text-white/65 hover:text-cyan-300 transition-colors duration-200">
                    {t('footer.aboutUs')}
                  </Link>
                  <Link to="/contact" className="text-white/65 hover:text-cyan-300 transition-colors duration-200">
                    {t('footer.contact')}
                  </Link>
                </div>
              </div>
            </div>
          </div>

          <div className="border-t border-white/10 px-6 py-6 md:px-8">
            <div className="max-w-6xl mx-auto">
              <h4 className="text-sm font-semibold uppercase tracking-wide text-white/80 mb-3">
                {t('footer.sections.popularCities')}
              </h4>
              <div className="flex flex-wrap gap-x-4 gap-y-2 text-sm">
                {popularCities.map((city) => {
                  const label = city.names[langKey] || city.names['en'] || city.defaultName;
                  return (
                    <Link
                      key={city.id}
                      to={buildCityHref(city.defaultName)}
                      className="text-white/65 hover:text-cyan-300 transition-colors duration-200"
                    >
                      {label}
                    </Link>
                  );
                })}
              </div>
            </div>
          </div>

          <div className="border-t border-white/10 px-6 py-4 text-center text-xs text-white/50 md:px-8">
            {t('footer.copyright')}
          </div>
        </motion.footer>
      </div>

      <Suspense fallback={null}>
        <FloatingChatbot />
      </Suspense>
    </div>
  );
}

export default App;
