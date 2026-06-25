import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import en from '../../public/locales/en/translation.json';
import { SearchBar } from './SearchBar';
import { geocodeCity } from '../services/api';

jest.mock('react-i18next', () => {
  const mockEn = require('../../public/locales/en/translation.json');
  return {
  useTranslation: () => ({
    t: (key: string) => {
      const parts = key.split('.');
      let value: unknown = mockEn;
      for (const part of parts) {
        if (value && typeof value === 'object' && part in (value as object)) {
          value = (value as Record<string, unknown>)[part];
        } else {
          return key;
        }
      }
      return typeof value === 'string' ? value : key;
    },
    i18n: { language: 'en' },
  }),
  };
});

jest.mock('../context/SettingsContext', () => ({
  useSettings: () => ({
    currentLanguage: 'en',
    currentUnit: 'metric',
    setLanguage: jest.fn(),
    setUnit: jest.fn(),
  }),
}));

jest.mock('../services/api', () => ({
  geocodeCity: jest.fn(),
  apiUrl: (path: string) => `http://localhost:8000${path}`,
}));

const mockGeocodeCity = geocodeCity as jest.MockedFunction<typeof geocodeCity>;

const londonHit = {
  name: 'London',
  latitude: 51.5085,
  longitude: -0.1257,
  country: 'United Kingdom',
  country_code: 'GB',
  admin1: 'England',
  feature_code: 'PPLC',
  population: 9_000_000,
};

beforeEach(() => {
  jest.useFakeTimers();
  mockGeocodeCity.mockReset();
  mockGeocodeCity.mockResolvedValue([londonHit]);
  jest.spyOn(console, 'log').mockImplementation(() => undefined);
});

afterEach(() => {
  jest.runOnlyPendingTimers();
  jest.useRealTimers();
  jest.restoreAllMocks();
});

describe('SearchBar', () => {
  it('renders the search input and location button', () => {
    render(<SearchBar onSearch={jest.fn()} onLocationRequest={jest.fn()} />);

    expect(screen.getByTestId('search-input')).toBeInTheDocument();
    expect(screen.getByTestId('location-button')).toBeInTheDocument();
    expect(screen.getByPlaceholderText(en.search.placeholder)).toBeInTheDocument();
  });

  it('calls geocodeCity after debounce when the user types a query', async () => {
    render(<SearchBar onSearch={jest.fn()} onLocationRequest={jest.fn()} />);

    fireEvent.change(screen.getByTestId('search-input'), { target: { value: 'lon' } });
    fireEvent.focus(screen.getByTestId('search-input'));

    await act(async () => {
      jest.advanceTimersByTime(300);
    });

    await waitFor(() => {
      expect(mockGeocodeCity).toHaveBeenCalledWith('lon', 'en', 20);
    });
  });

  it('shows suggestions and calls onSearch when a suggestion is selected', async () => {
    const onSearch = jest.fn();
    render(<SearchBar onSearch={onSearch} onLocationRequest={jest.fn()} />);

    const input = screen.getByTestId('search-input');
    fireEvent.change(input, { target: { value: 'lon' } });
    fireEvent.focus(input);

    await act(async () => {
      jest.advanceTimersByTime(300);
    });

    const suggestion = await screen.findByText('London, England, United Kingdom');
    fireEvent.click(suggestion);

    expect(onSearch).toHaveBeenCalledWith('London', londonHit.latitude, londonHit.longitude);
  });

  it('invokes onLocationRequest when the location button is clicked', () => {
    const onLocationRequest = jest.fn();
    render(<SearchBar onSearch={jest.fn()} onLocationRequest={onLocationRequest} />);

    fireEvent.click(screen.getByTestId('location-button'));
    expect(onLocationRequest).toHaveBeenCalledTimes(1);
  });
});
