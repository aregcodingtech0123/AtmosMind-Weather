import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import en from '../../public/locales/en/translation.json';
import { Navbar } from './Navbar';
import type { SupportedLanguage } from '../context/SettingsContext';

const mockSetLanguage = jest.fn();
const mockSetUnit = jest.fn();

let mockCurrentLanguage: SupportedLanguage = 'en';
let mockCurrentUnit: 'metric' | 'imperial' = 'metric';

jest.mock('react-i18next', () => {
  const mockEn = require('../../public/locales/en/translation.json');
  return {
  useTranslation: () => ({
    t: (key: string, options?: { defaultValue?: string }) => {
      const parts = key.split('.');
      let value: unknown = mockEn;
      for (const part of parts) {
        if (value && typeof value === 'object' && part in (value as object)) {
          value = (value as Record<string, unknown>)[part];
        } else {
          return options?.defaultValue ?? key;
        }
      }
      return typeof value === 'string' ? value : options?.defaultValue ?? key;
    },
    i18n: { language: 'en', changeLanguage: jest.fn() },
  }),
  };
});

jest.mock('../context/SettingsContext', () => ({
  useSettings: () => ({
    currentLanguage: mockCurrentLanguage,
    currentUnit: mockCurrentUnit,
    setLanguage: mockSetLanguage,
    setUnit: mockSetUnit,
  }),
}));

jest.mock('../hooks/useMediaQuery', () => ({
  useMediaQuery: (query: string) => {
    if (query.includes('1024')) return true;
    if (query.includes('768')) return true;
    return false;
  },
}));

jest.mock('./SearchBar', () => ({
  SearchBar: () => <div data-testid="search-bar-stub" />,
}));

function renderNavbar() {
  return render(
    <Navbar
      onSearch={jest.fn()}
      onLocationRequest={jest.fn()}
    />
  );
}

beforeEach(() => {
  mockCurrentLanguage = 'en';
  mockCurrentUnit = 'metric';
  mockSetLanguage.mockReset();
  mockSetUnit.mockReset();
  mockSetLanguage.mockImplementation((lang: SupportedLanguage) => {
    mockCurrentLanguage = lang;
    document.documentElement.lang = lang;
    document.documentElement.dir = ['ar', 'ur', 'fa'].includes(lang) ? 'rtl' : 'ltr';
  });
  document.documentElement.lang = 'en';
  document.documentElement.dir = 'ltr';
});

describe('Navbar i18n locale switcher', () => {
  it('renders the brand and language selector', () => {
    renderNavbar();
    expect(screen.getByText('AtmosMind')).toBeInTheDocument();
    expect(screen.getByLabelText(en.navbar.languageLabel)).toBeInTheDocument();
  });

  it('calls setLanguage with tr when Turkish is selected', async () => {
    renderNavbar();
    fireEvent.change(screen.getByLabelText(en.navbar.languageLabel), {
      target: { value: 'tr' },
    });

    await waitFor(() => {
      expect(mockSetLanguage).toHaveBeenCalledWith('tr');
      expect(document.documentElement.lang).toBe('tr');
    });
  });

  it('sets document direction to rtl when Arabic is selected', async () => {
    renderNavbar();
    fireEvent.change(screen.getByLabelText(en.navbar.languageLabel), {
      target: { value: 'ar' },
    });

    await waitFor(() => {
      expect(mockSetLanguage).toHaveBeenCalledWith('ar');
      expect(document.documentElement.dir).toBe('rtl');
      expect(document.documentElement.lang).toBe('ar');
    });
  });

  it('restores ltr when switching from Arabic to English', async () => {
    renderNavbar();
    const select = screen.getByLabelText(en.navbar.languageLabel);

    fireEvent.change(select, { target: { value: 'ar' } });
    await waitFor(() => expect(document.documentElement.dir).toBe('rtl'));

    fireEvent.change(select, { target: { value: 'en' } });
    await waitFor(() => {
      expect(mockSetLanguage).toHaveBeenLastCalledWith('en');
      expect(document.documentElement.dir).toBe('ltr');
    });
  });
});
