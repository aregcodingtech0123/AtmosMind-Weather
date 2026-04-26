import i18n from 'i18next';
import HttpBackend from 'i18next-http-backend';
import { initReactI18next } from 'react-i18next';

const getInitialLanguage = (): string => {
  const params = new URLSearchParams(window.location.search);
  const lngParam = params.get('lng');
  if (lngParam) return lngParam;
  return localStorage.getItem('atmosmind.language') || 'en';
};

const savedLanguage = getInitialLanguage();

i18n
  .use(HttpBackend)
  .use(initReactI18next)
  .init({
    lng: savedLanguage,
    fallbackLng: 'en',
    supportedLngs: [
      'en', 'tr', 'fr', 'es', 'de', 'ja', 'zh', 'hi', 'ru', 'ar', 'it', 'pt',
      'bn', 'ur', 'tl', 'vi', 'uk', 'pl', 'nl', 'fi', 'da', 'no', 'sv', 'ha',
      'ta', 'ms', 'id', 'jv', 'su', 'hu', 'cs', 'el', 'ro', 'fa', 'th', 'sw',
      'az', 'kk', 'uz', 'ky', 'tk', 'ko'
    ],
    interpolation: {
      escapeValue: false,
    },
    backend: {
      loadPath: '/locales/{{lng}}/translation.json',
    },
  });

export default i18n;
