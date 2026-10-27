import React from 'react';
import { render, screen } from '@testing-library/react';
import i18n from 'i18next';
import { I18nextProvider, initReactI18next } from 'react-i18next';
import { SettingsProvider } from '../context/SettingsContext';
import { LifestyleIndicesGrid } from './LifestyleIndicesGrid';
import type { LifestyleIndices } from '../types/weather';

const resources = {
  en: {
    translation: {
      'weather.unavailable': 'Data temporarily unavailable',
      'lifestyleIndices.title': 'Lifestyle',
      'lifestyleIndices.subtitle': 'Subtitle',
      'lifestyleIndices.unavailable': 'Unavailable',
      'lifestyleIndices.km': 'km',
      'lifestyleIndices.miles': 'mi',
      'lifestyleIndices.aqi.title': 'AQI',
      'lifestyleIndices.aqi.helper.good': 'Good',
      'lifestyleIndices.uv.title': 'UV',
      'lifestyleIndices.uv.helper.low': 'Low',
      'lifestyleIndices.pollen.title': 'Pollen',
      'lifestyleIndices.pollen.level.low': 'Low',
      'lifestyleIndices.visibility.title': 'Visibility',
      'lifestyleIndices.visibility.dewPoint': 'Dew',
      'lifestyleIndices.visibility.helper.clear': 'Clear',
    },
  },
};

beforeAll(async () => {
  await i18n.use(initReactI18next).init({
    lng: 'en',
    resources,
    interpolation: { escapeValue: false },
  });
});

const baseData: LifestyleIndices = {
  latitude: 41,
  longitude: 29,
  timezone: 'Europe/Istanbul',
  observed_at: null,
  european_aqi: 25,
  us_aqi: null,
  aqi_value: 25,
  aqi_standard: 'european',
  aqi_category: 'good',
  uv_index: 3,
  uv_category: 'moderate',
  pollen: { birch: 0, grass: 0, ragweed: 0, level: 'low' },
  visibility_meters: null,
  dew_point_celsius: 12,
};

function renderGrid(data: LifestyleIndices) {
  return render(
    <I18nextProvider i18n={i18n}>
      <SettingsProvider>
        <LifestyleIndicesGrid data={data} />
      </SettingsProvider>
    </I18nextProvider>
  );
}

describe('LifestyleIndicesGrid', () => {
  it('shows AQI value and weather.unavailable for missing visibility', () => {
    renderGrid(baseData);
    expect(screen.getByText('25 EU')).toBeInTheDocument();
    expect(screen.getAllByText('Data temporarily unavailable').length).toBeGreaterThanOrEqual(1);
  });
});
