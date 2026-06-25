import React from 'react';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { HelmetProvider } from 'react-helmet-async';
import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import en from '../public/locales/en/translation.json';
import tr from '../public/locales/tr/translation.json';
import { SettingsProvider } from './context/SettingsContext';

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

import App from './App';

function renderApp() {
  localStorage.clear();
  localStorage.setItem('cookie-consent', 'accepted');
  localStorage.setItem(
    'atmosmind_popular_weather_cache_en_metric',
    JSON.stringify({ data: {}, timestamp: Date.now() })
  );
  return render(
    <HelmetProvider>
      <SettingsProvider>
        <App />
      </SettingsProvider>
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

beforeEach(() => {
  mockDesktopViewport();
  document.documentElement.lang = 'en';
  document.documentElement.dir = 'ltr';
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
});
