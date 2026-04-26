import React, { createContext, useContext, useEffect, useMemo, useState } from 'react';
import i18n from '../i18n';

export type SupportedLanguage =
  | 'en' | 'tr' | 'fr' | 'es' | 'de' | 'ja' | 'zh' | 'hi' | 'ru' | 'ar' | 'it' | 'pt'
  | 'bn' | 'ur' | 'tl' | 'vi' | 'uk' | 'pl' | 'nl' | 'fi' | 'da' | 'no' | 'sv' | 'ha'
  | 'ta' | 'ms' | 'id' | 'jv' | 'su' | 'hu' | 'cs' | 'el' | 'ro' | 'fa' | 'th' | 'sw'
  | 'az' | 'kk' | 'uz' | 'ky' | 'tk' | 'ko';
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

const RTL_LANGUAGES = new Set<SupportedLanguage>(['ar', 'ur', 'fa']);

function isSupportedLanguage(value: string | null): value is SupportedLanguage {
  const supported: string[] = [
    'en', 'tr', 'fr', 'es', 'de', 'ja', 'zh', 'hi', 'ru', 'ar', 'it', 'pt',
    'bn', 'ur', 'tl', 'vi', 'uk', 'pl', 'nl', 'fi', 'da', 'no', 'sv', 'ha',
    'ta', 'ms', 'id', 'jv', 'su', 'hu', 'cs', 'el', 'ro', 'fa', 'th', 'sw',
    'az', 'kk', 'uz', 'ky', 'tk', 'ko'
  ];
  return !!value && supported.includes(value);
}

function isSupportedUnit(value: string | null): value is TemperatureUnit {
  return value === 'metric' || value === 'imperial';
}

export const SettingsProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [currentLanguage, setCurrentLanguage] = useState<SupportedLanguage>(() => {
    const params = new URLSearchParams(window.location.search);
    const lngParam = params.get('lng');
    if (isSupportedLanguage(lngParam)) return lngParam;

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
