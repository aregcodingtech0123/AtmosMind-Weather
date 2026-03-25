import React, { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { cn } from '../utils/cn';
import { useTranslation } from 'react-i18next';

type CookieConsentChoice = 'accepted' | 'rejected';

const STORAGE_KEY = 'cookie-consent';

export const CookieConsent: React.FC = () => {
  const { t } = useTranslation();
  const [choice, setChoice] = useState<CookieConsentChoice | null>(null);

  useEffect(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY) as CookieConsentChoice | null;
      if (stored === 'accepted' || stored === 'rejected') setChoice(stored);
    } catch {
      // If storage is blocked, show banner (no persistence).
      setChoice(null);
    }
  }, []);

  const isVisible = useMemo(() => choice == null, [choice]);

  const save = (next: CookieConsentChoice) => {
    setChoice(next);
    try {
      localStorage.setItem(STORAGE_KEY, next);
    } catch {
      // ignore
    }
  };

  if (!isVisible) return null;

  return (
    <div className="fixed inset-x-0 bottom-0 z-[80] p-3 sm:p-4 pointer-events-none">
      <div
        className={cn(
          'mx-auto w-full max-w-4xl',
          'rounded-2xl border border-white/10 bg-black/50 backdrop-blur-xl',
          'px-4 py-4 sm:px-5',
          'shadow-2xl shadow-black/30',
          // Only the banner itself should capture clicks; everything else should be click-through.
          'pointer-events-auto'
        )}
        role="dialog"
        aria-live="polite"
        aria-label={String(t('consent.title', { defaultValue: 'Cookie consent' }))}
      >
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div className="min-w-0">
            <p className="text-sm font-semibold text-white/90">
              {String(t('consent.title', { defaultValue: 'Cookies & Ads' }))}
            </p>
            <p className="mt-1 text-sm text-white/70 leading-6">
              {String(
                t('consent.body', {
                  defaultValue:
                    'We use cookies and similar technologies to remember settings and to support advertising (including Google AdSense). You can accept or reject non-essential cookies.',
                })
              )}{' '}
              <Link to="/cookies" className="text-cyan-200 hover:text-cyan-100 transition-colors">
                {String(t('consent.learnMore', { defaultValue: 'Learn more' }))}
              </Link>
              .
            </p>
          </div>

          <div className="flex shrink-0 flex-col gap-2 sm:flex-row sm:items-center sm:gap-3">
            <button
              type="button"
              onClick={() => save('rejected')}
              className={cn(
                'inline-flex items-center justify-center rounded-xl px-4 py-2.5 text-sm font-medium',
                'bg-white/10 hover:bg-white/15 text-white/85',
                'transition-colors focus:outline-none focus:ring-2 focus:ring-white/50'
              )}
            >
              {String(t('consent.reject', { defaultValue: 'Reject' }))}
            </button>
            <button
              type="button"
              onClick={() => save('accepted')}
              className={cn(
                'inline-flex items-center justify-center rounded-xl px-4 py-2.5 text-sm font-semibold',
                'bg-cyan-500/25 hover:bg-cyan-500/35 text-white',
                'border border-cyan-300/30',
                'transition-colors focus:outline-none focus:ring-2 focus:ring-cyan-200/60'
              )}
            >
              {String(t('consent.accept', { defaultValue: 'Accept' }))}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

