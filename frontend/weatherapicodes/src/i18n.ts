import i18n from 'i18next';
import HttpBackend from 'i18next-http-backend';
import { initReactI18next } from 'react-i18next';

const savedLanguage = localStorage.getItem('atmosmind.language') || 'en';

i18n
  .use(HttpBackend)
  .use(initReactI18next)
  .init({
    lng: savedLanguage,
    fallbackLng: 'en',
    supportedLngs: ['en', 'tr', 'fr', 'es', 'de', 'ja', 'zh', 'ko', 'ru', 'ar', 'it', 'pt'],
    interpolation: {
      escapeValue: false,
    },
    backend: {
      loadPath: '/locales/{{lng}}/translation.json',
    },
  });

export default i18n;
