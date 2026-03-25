import React, { useCallback, useEffect, useId, useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { Menu, X } from 'lucide-react';
import { SearchBar } from './SearchBar';
import { useTranslation } from 'react-i18next';
import { SupportedLanguage, TemperatureUnit, useSettings } from '../context/SettingsContext';
import { useMediaQuery } from '../hooks/useMediaQuery';

interface NavbarProps {
  onSearch: (cityName: string, lat: number, lng: number) => void;
  onLocationRequest: () => void;
  locationLoading?: boolean;
  onBrandClick?: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  onSearch,
  onLocationRequest,
  locationLoading = false,
  onBrandClick,
}) => {
  const { t } = useTranslation();
  const location = useLocation();
  const reactId = useId();
  const isLg = useMediaQuery('(min-width: 1024px)');
  const isMd = useMediaQuery('(min-width: 768px)');
  const [menuOpen, setMenuOpen] = useState(false);

  const { currentLanguage, currentUnit, setLanguage, setUnit } = useSettings();

  const languageOptions: Array<{ code: SupportedLanguage; label: string }> = [
    { code: 'en', label: String(t('languages.en', { defaultValue: 'English' })) },
    { code: 'tr', label: String(t('languages.tr', { defaultValue: 'Türkçe' })) },
    { code: 'fr', label: String(t('languages.fr', { defaultValue: 'Français' })) },
    { code: 'es', label: String(t('languages.es', { defaultValue: 'Español' })) },
    { code: 'de', label: String(t('languages.de', { defaultValue: 'Deutsch' })) },
    { code: 'ja', label: String(t('languages.ja', { defaultValue: '日本語' })) },
    { code: 'zh', label: String(t('languages.zh', { defaultValue: '中文' })) },
    { code: 'ko', label: String(t('languages.ko', { defaultValue: '한국어' })) },
    { code: 'ru', label: String(t('languages.ru', { defaultValue: 'Русский' })) },
    { code: 'ar', label: String(t('languages.ar', { defaultValue: 'العربية' })) },
    { code: 'it', label: String(t('languages.it', { defaultValue: 'Italiano' })) },
    { code: 'pt', label: String(t('languages.pt', { defaultValue: 'Português' })) },
  ];

  const closeMenu = useCallback(() => setMenuOpen(false), []);

  useEffect(() => {
    setMenuOpen(false);
  }, [location.pathname]);

  useEffect(() => {
    if (isLg) setMenuOpen(false);
  }, [isLg]);

  useEffect(() => {
    if (!menuOpen || isLg) return;
    const prev = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      document.body.style.overflow = prev;
    };
  }, [menuOpen, isLg]);

  useEffect(() => {
    if (!menuOpen || isLg) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setMenuOpen(false);
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [menuOpen, isLg]);

  const brandInner = (
    <>
      <img
        src="/AtmosMindLogo.webp"
        alt="AtmosMind"
        width={160}
        height={40}
        className="h-9 w-auto shrink-0 object-contain sm:h-10"
      />
      <span className="font-heading text-lg font-bold tracking-tight whitespace-nowrap sm:text-xl md:text-2xl lg:text-3xl">
        AtmosMind
      </span>
    </>
  );

  const renderBrand = () =>
    onBrandClick ? (
      <button
        type="button"
        onClick={onBrandClick}
        className="flex max-w-full shrink-0 items-center gap-2 rounded-full text-left sm:gap-3"
        aria-label={String(t('navbar.goHome', { defaultValue: 'Go to home' }))}
      >
        {brandInner}
      </button>
    ) : (
      <Link to="/" className="flex max-w-full shrink-0 items-center gap-2 rounded-full sm:gap-3" onClick={closeMenu}>
        {brandInner}
      </Link>
    );

  const langSelect = (idSuffix: string) => (
    <>
      <label className="sr-only" htmlFor={`${reactId}-lang-${idSuffix}`}>
        {t('navbar.languageLabel')}
      </label>
      <select
        id={`${reactId}-lang-${idSuffix}`}
        value={currentLanguage}
        onChange={(e) => setLanguage(e.target.value as SupportedLanguage)}
        className="w-full shrink-0 rounded-xl border border-white/20 bg-black/20 px-3 py-2.5 text-sm text-white/90 focus:outline-none focus:ring-2 focus:ring-white/50 md:w-auto md:min-w-[8.5rem] md:max-w-[12rem] lg:max-w-none"
        aria-label={String(t('navbar.languageLabel'))}
      >
        {languageOptions.map((option) => (
          <option key={option.code} value={option.code}>
            {option.label}
          </option>
        ))}
      </select>
    </>
  );

  const unitSelect = (idSuffix: string) => (
    <>
      <label className="sr-only" htmlFor={`${reactId}-unit-${idSuffix}`}>
        {t('navbar.unitLabel')}
      </label>
      <select
        id={`${reactId}-unit-${idSuffix}`}
        value={currentUnit}
        onChange={(e) => setUnit(e.target.value as TemperatureUnit)}
        className="w-full shrink-0 rounded-xl border border-white/20 bg-black/20 px-3 py-2.5 text-sm text-white/90 focus:outline-none focus:ring-2 focus:ring-white/50 md:w-auto"
        aria-label={String(t('navbar.unitLabel'))}
      >
        <option value="metric">{t('navbar.celsius')}</option>
        <option value="imperial">{t('navbar.fahrenheit')}</option>
      </select>
    </>
  );

  const navLinks = (variant: 'row' | 'stack') => (
    <>
      <Link
        to="/about"
        onClick={closeMenu}
        className={
          variant === 'stack'
            ? 'min-h-12 shrink-0 rounded-xl px-4 py-3 text-base font-bold text-white/90 transition-colors hover:bg-white/10 hover:text-cyan-200'
            : 'shrink-0 text-base font-bold tracking-tight text-white/90 transition-colors hover:text-cyan-200 md:text-lg xl:text-xl'
        }
      >
        {t('navbar.about')}
      </Link>
      <Link
        to="/privacy"
        onClick={closeMenu}
        className={
          variant === 'stack'
            ? 'min-h-12 shrink-0 rounded-xl px-4 py-3 text-base text-white/80 transition-colors hover:bg-white/10 hover:text-cyan-200'
            : 'shrink-0 text-sm text-white/80 transition-colors hover:text-cyan-200 md:text-base'
        }
      >
        {t('navbar.privacy')}
      </Link>
    </>
  );

  const searchBar = (
    <SearchBar
      onSearch={onSearch}
      onLocationRequest={onLocationRequest}
      locationLoading={locationLoading}
      className={
        isLg
          ? 'mx-auto w-full max-w-[400px] shrink'
          : isMd
            ? 'w-full min-w-0 max-w-[400px] shrink md:max-w-[min(22rem,100%)]'
            : 'w-full max-w-none shrink'
      }
    />
  );

  const hamburger = (
    <button
      type="button"
      className="inline-flex h-11 w-11 shrink-0 items-center justify-center rounded-xl border border-white/20 bg-black/20 text-white/90 transition-colors hover:bg-white/10 focus:outline-none focus:ring-2 focus:ring-white/50"
      aria-expanded={menuOpen}
      aria-controls={`${reactId}-mobile-menu`}
      aria-label={menuOpen ? String(t('navbar.closeMenu', { defaultValue: 'Close menu' })) : String(t('navbar.openMenu', { defaultValue: 'Open menu' }))}
      onClick={() => setMenuOpen((o) => !o)}
    >
      {menuOpen ? <X className="h-6 w-6" strokeWidth={1.5} /> : <Menu className="h-6 w-6" strokeWidth={1.5} />}
    </button>
  );

  return (
    <motion.header
      initial={{ opacity: 0, y: -20 }}
      animate={{ opacity: 1, y: 0 }}
      className="relative z-20 mb-8 w-full min-w-0 overflow-visible md:mb-12"
    >
      <div className="w-full py-4">
        {/* Desktop ≥1024: three columns, space distributed via grid + gaps */}
        {isLg && (
          <div className="grid w-full min-w-0 grid-cols-[auto_minmax(0,1fr)_auto] items-center gap-x-6 gap-y-4 xl:gap-x-8 2xl:gap-x-10">
            <div className="flex min-w-0 shrink-0 items-center justify-start">{renderBrand()}</div>
            <div className="relative z-10 flex min-w-0 justify-center justify-self-stretch px-2">{searchBar}</div>
            <nav className="relative z-0 flex min-w-0 flex-wrap items-center justify-end justify-self-end gap-3 sm:gap-4">
              {langSelect('desktop')}
              {unitSelect('desktop')}
              {navLinks('row')}
            </nav>
          </div>
        )}

        {/* Tablet 768–1023: single row — brand, compact search, settings, hamburger (links in drawer) */}
        {!isLg && isMd && (
          <div className="flex min-w-0 flex-col gap-3">
            <div className="flex min-w-0 flex-wrap items-center gap-3 md:gap-4">
              <div className="shrink-0">{renderBrand()}</div>
              <div className="min-w-0 flex-1 basis-[min(100%,22rem)]">
                {searchBar}
              </div>
              <div className="flex shrink-0 flex-wrap items-center gap-2 md:gap-3">
                {langSelect('tablet')}
                {unitSelect('tablet')}
              </div>
              {hamburger}
            </div>
          </div>
        )}

        {/* Mobile <768: brand row + hamburger; search full width below */}
        {!isMd && (
          <div className="flex min-w-0 flex-col gap-4">
            <div className="flex min-w-0 items-center justify-between gap-4">
              {renderBrand()}
              {hamburger}
            </div>
            <div className="w-full min-w-0 px-0">{searchBar}</div>
          </div>
        )}

        {/* Slide-out: mobile = lang + unit + links; tablet = links only (settings stay in bar) */}
        <AnimatePresence>
          {!isLg && menuOpen && (
            <>
              <motion.button
                type="button"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.2 }}
                className="fixed inset-0 z-[90] bg-black/60 backdrop-blur-sm"
                aria-label={String(t('navbar.closeMenu', { defaultValue: 'Close menu' }))}
                onClick={closeMenu}
              />
              <motion.div
                id={`${reactId}-mobile-menu`}
                role="dialog"
                aria-modal="true"
                aria-label={String(t('navbar.menu', { defaultValue: 'Menu' }))}
                initial={{ x: '100%' }}
                animate={{ x: 0 }}
                exit={{ x: '100%' }}
                transition={{ type: 'tween', duration: 0.25, ease: [0.32, 0.72, 0, 1] }}
                className="fixed top-0 end-0 z-[100] flex h-full w-full max-w-sm flex-col border-s border-white/10 bg-slate-950/98 shadow-2xl backdrop-blur-xl"
              >
                <div className="flex items-center justify-between border-b border-white/10 px-5 py-4">
                  <span className="font-heading text-lg font-semibold text-white/95">
                    {t('navbar.menu', { defaultValue: 'Menu' })}
                  </span>
                  <button
                    type="button"
                    className="inline-flex h-10 w-10 items-center justify-center rounded-lg text-white/90 hover:bg-white/10"
                    aria-label={String(t('navbar.closeMenu', { defaultValue: 'Close menu' }))}
                    onClick={closeMenu}
                  >
                    <X className="h-6 w-6" strokeWidth={1.5} />
                  </button>
                </div>
                <div className="flex flex-1 flex-col gap-6 overflow-y-auto px-5 py-6">
                  {!isMd && (
                    <div className="flex flex-col gap-4">
                      {langSelect('menu-mobile')}
                      {unitSelect('menu-mobile')}
                    </div>
                  )}
                  {isMd && (
                    <p className="text-xs text-white/50 md:block lg:hidden">
                      {t('navbar.tabletMenuHint', { defaultValue: 'Language and unit are in the bar above.' })}
                    </p>
                  )}
                  <nav className="flex flex-col gap-2 border-t border-white/10 pt-4">{navLinks('stack')}</nav>
                </div>
              </motion.div>
            </>
          )}
        </AnimatePresence>
      </div>
    </motion.header>
  );
};
