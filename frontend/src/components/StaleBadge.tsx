import React, { useMemo } from 'react';
import { useTranslation } from 'react-i18next';

interface StaleBadgeProps {
  fetchedAt?: string | null;
  className?: string;
}

function formatLocalTime(iso: string, locale: string): string {
  try {
    const d = new Date(iso.replace('Z', '+00:00'));
    return d.toLocaleTimeString(locale, { hour: '2-digit', minute: '2-digit' });
  } catch {
    return '';
  }
}

export function StaleBadge({ fetchedAt, className }: StaleBadgeProps) {
  const { t, i18n } = useTranslation();
  const timeLabel = useMemo(() => {
    if (!fetchedAt) return null;
    const formatted = formatLocalTime(fetchedAt, i18n.language);
    return formatted || null;
  }, [fetchedAt, i18n.language]);

  return (
    <span
      data-testid="stale-badge"
      dir="auto"
      className={className ?? 'text-[10px] sm:text-xs text-amber-200/90 ms-1 whitespace-nowrap'}
    >
      {timeLabel
        ? t('weather.stale_badge', { time: timeLabel })
        : t('weather.stale_badge_unknown')}
    </span>
  );
}
