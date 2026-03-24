import React, { createContext, useContext, useEffect, useMemo, useState } from 'react';
import i18n from '../i18n';

export type SupportedLanguage = 'en' | 'tr' | 'fr' | 'es' | 'de' | 'ja' | 'zh' | 'ko' | 'ru' | 'ar' | 'it' | 'pt';
export type TemperatureUnit = 'metric' | 'imperial';

interface SettingsContextValue {
  currentLanguage: SupportedLanguage;
  currentUnit: TemperatureUnit;
  setLanguage: (language: SupportedLanguage) => void;
  setUnit: (unit: TemperatureUnit) => void;
}

const SettingsContext = createContext<SettingsContextValue | undefined>(undefined);

const LANGUAGE_STORAGE_KEY = 'atmosmind.language';
const UNIT_STORAGE_KEY = 'atmosmind.unit';

const LANGUAGE_FALLBACK: SupportedLanguage = 'en';
const UNIT_FALLBACK: TemperatureUnit = 'metric';

const RTL_LANGUAGES = new Set<SupportedLanguage>(['ar']);

function isSupportedLanguage(value: string | null): value is SupportedLanguage {
  return !!value && ['en', 'tr', 'fr', 'es', 'de', 'ja', 'zh', 'ko', 'ru', 'ar', 'it', 'pt'].includes(value);
}

function isSupportedUnit(value: string | null): value is TemperatureUnit {
  return value === 'metric' || value === 'imperial';
}

export const SettingsProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [currentLanguage, setCurrentLanguage] = useState<SupportedLanguage>(() => {
    const saved = localStorage.getItem(LANGUAGE_STORAGE_KEY);
    return isSupportedLanguage(saved) ? saved : LANGUAGE_FALLBACK;
  });
  const [currentUnit, setCurrentUnit] = useState<TemperatureUnit>(() => {
    const saved = localStorage.getItem(UNIT_STORAGE_KEY);
    return isSupportedUnit(saved) ? saved : UNIT_FALLBACK;
  });

  useEffect(() => {
    localStorage.setItem(LANGUAGE_STORAGE_KEY, currentLanguage);
    document.documentElement.lang = currentLanguage;
    document.documentElement.dir = RTL_LANGUAGES.has(currentLanguage) ? 'rtl' : 'ltr';
    i18n.changeLanguage(currentLanguage);
  }, [currentLanguage]);

  useEffect(() => {
    localStorage.setItem(UNIT_STORAGE_KEY, currentUnit);
  }, [currentUnit]);

  const value = useMemo(
    () => ({
      currentLanguage,
      currentUnit,
      setLanguage: setCurrentLanguage,
      setUnit: setCurrentUnit,
    }),
    [currentLanguage, currentUnit]
  );

  return <SettingsContext.Provider value={value}>{children}</SettingsContext.Provider>;
};

export function useSettings(): SettingsContextValue {
  const context = useContext(SettingsContext);
  if (!context) {
    throw new Error('useSettings must be used within SettingsProvider');
  }
  return context;
}
