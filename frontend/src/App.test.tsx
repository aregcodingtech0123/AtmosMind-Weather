import React from 'react';
import { render, screen, waitFor, fireEvent, within } from '@testing-library/react';
import { HelmetProvider } from 'react-helmet-async';
import { MemoryRouter } from 'react-router-dom';
import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import en from '../public/locales/en/translation.json';
import tr from '../public/locales/tr/translation.json';
import { SettingsProvider } from './context/SettingsContext';
import { POPULAR_CITIES } from './data/popularCities';
import { fetchPopularWeatherBatch } from './services/api';

// Sync i18n for tests (avoids HttpBackend network calls in Jest).
void i18n.use(initReactI18next).init({
  lng: 'en',
  fallbackLng: 'en',
  resources: {
    en: { translation: en },
    tr: { translation: tr },
  },
  interpolation: { escapeValue: false },
});

jest.mock('./hooks/useCityDetail', () => ({
  useCityDetail: () => ({
    weatherData: null,
    lifestyleIndices: null,
    detailMeta: null,
    loading: false,
    error: null,
    lifestyleError: null,
    refetch: jest.fn(),
  }),
}));

jest.mock('./hooks/useGeolocation', () => ({
  useGeolocation: () => ({
    getCurrentLocation: jest.fn(),
    loading: false,
    error: null,
    latitude: null,
    longitude: null,
  }),
}));

jest.mock('./components/FloatingChatbot', () => ({
  FloatingChatbot: () => null,
}));

jest.mock('./services/api', () => {
  const actual = jest.requireActual('./services/api');
  return {
    ...actual,
    fetchPopularWeatherBatch: jest.fn(),
    geocodeCity: jest.fn(),
    reverseGeocode: jest.fn(),
    fetchAiWeather: jest.fn(),
    fetchCityAdvice: jest.fn(),
    fetchForecastSummary: jest.fn(),
  };
});

const mockFetchPopularWeatherBatch = fetchPopularWeatherBatch as jest.MockedFunction<
  typeof fetchPopularWeatherBatch
>;

import App from './App';

function renderApp(initialPath = '/') {
  localStorage.clear();
  localStorage.setItem('cookie-consent', 'accepted');
  return render(
    <HelmetProvider>
      <MemoryRouter initialEntries={[initialPath]}>
        <SettingsProvider>
          <App />
        </SettingsProvider>
      </MemoryRouter>
    </HelmetProvider>
  );
}

function mockDesktopViewport() {
  Object.defineProperty(window, 'matchMedia', {
    writable: true,
    configurable: true,
    value: jest.fn().mockImplementation((query: string) => ({
      matches: query.includes('min-width'),
      media: query,
      onchange: null,
      addListener: jest.fn(),
      removeListener: jest.fn(),
      addEventListener: jest.fn(),
      removeEventListener: jest.fn(),
      dispatchEvent: jest.fn(),
    })),
  });
}

function mockBatchFiveStaleFifteenFresh() {
  const results = POPULAR_CITIES.map((city, index) => ({
    city: city.defaultName,
    temperature: 20 + (index % 10),
    condition: 'Clear',
    weather_code: 0,
    error: null,
    meta:
      index < 5
        ? { data_status: 'stale' as const, fetched_at: '2026-10-28T10:00:00.000Z' }
        : { data_status: 'fresh' as const, fetched_at: '2026-10-28T15:00:00.000Z' },
  }));
  const temperatures: Record<string, number> = {};
  for (const item of results) {
    if (item.temperature != null) {
      temperatures[item.city] = item.temperature;
    }
  }
  mockFetchPopularWeatherBatch.mockResolvedValue({ results, temperatures });
}

beforeEach(() => {
  mockDesktopViewport();
  document.documentElement.lang = 'en';
  document.documentElement.dir = 'ltr';
  delete process.env.REACT_APP_HOME_VISIBLE_CITIES;
  mockFetchPopularWeatherBatch.mockReset();
  mockBatchFiveStaleFifteenFresh();
});

describe('App', () => {
  it('renders the AtmosMind shell and home welcome content', async () => {
    renderApp();

    expect(screen.getByTestId('weather-app')).toBeInTheDocument();
    expect(await screen.findByText(en.home.welcome)).toBeInTheDocument();
    expect(screen.getByText(en.home.tagline)).toBeInTheDocument();
  });

  it('updates document language when the locale switcher changes', async () => {
    renderApp();

    const languageSelect = await screen.findByLabelText(en.navbar.languageLabel);
    fireEvent.change(languageSelect, { target: { value: 'tr' } });

    await waitFor(() => {
      expect(document.documentElement.lang).toBe('tr');
      expect(localStorage.getItem('atmosmind.language')).toBe('tr');
    });
  });

  it('home batch: 20 cards, 5 stale badges, no silent dashes on cards', async () => {
    process.env.REACT_APP_HOME_VISIBLE_CITIES = '20';
    renderApp();

    await waitFor(() => {
      expect(mockFetchPopularWeatherBatch).toHaveBeenCalled();
      expect(screen.getAllByTestId('weather-card').length).toBe(20);
    });

    expect(screen.getAllByTestId('stale-badge').length).toBe(5);

    screen.getAllByTestId('weather-card').forEach((card) => {
      expect(within(card).queryByText('—')).toBeNull();
    });
  });
});
