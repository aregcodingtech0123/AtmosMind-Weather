import React from 'react';
import { render, screen } from '@testing-library/react';
import i18n from 'i18next';
import { I18nextProvider, initReactI18next } from 'react-i18next';
import { StaleBadge } from './StaleBadge';

const resources = {
  en: {
    translation: {
      'weather.stale_badge': 'Last updated {{time}}',
      'weather.stale_badge_unknown': 'Last updated',
    },
  },
  ar: {
    translation: {
      'weather.stale_badge': 'آخر تحديث {{time}}',
      'weather.stale_badge_unknown': 'آخر تحديث',
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

function renderBadge(ui: React.ReactElement, lang = 'en') {
  i18n.changeLanguage(lang);
  return render(<I18nextProvider i18n={i18n}>{ui}</I18nextProvider>);
}

describe('StaleBadge', () => {
  it('renders formatted time when fetchedAt is set', () => {
    renderBadge(<StaleBadge fetchedAt="2026-10-28T15:30:00.000Z" />);
    expect(screen.getByText(/Last updated/)).toBeInTheDocument();
  });

  it('uses dir auto for RTL locales', async () => {
    renderBadge(<StaleBadge fetchedAt="2026-10-28T15:30:00.000Z" />, 'ar');
    const el = screen.getByText(/آخر تحديث/);
    expect(el.getAttribute('dir')).toBe('auto');
  });
});
