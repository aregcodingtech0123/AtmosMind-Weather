import React, { useRef } from 'react';
import { GlassCard } from './GlassCard';
import { WeatherIcon } from './WeatherIcon';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import { HourlyData } from '../types/weather';
import { formatTemperature, isNightTime } from '../utils/weatherUtils';
import { cn } from '../utils/cn';
import { useSettings } from '../context/SettingsContext';
import { useTranslation } from 'react-i18next';

interface HourlyForecastProps {
  data: HourlyData;
  limit?: number;
}

export const HourlyForecast: React.FC<HourlyForecastProps> = ({ data, limit = 24 }) => {
  const { currentUnit, currentLanguage } = useSettings();
  const { t } = useTranslation();
  const scrollRef = useRef<HTMLDivElement>(null);

  const scroll = (direction: 'left' | 'right') => {
    if (scrollRef.current) {
      const scrollAmount = 200;
      scrollRef.current.scrollBy({
        left: direction === 'left' ? -scrollAmount : scrollAmount,
        behavior: 'smooth',
      });
    }
  };

  const hourlyItems = data.time.slice(0, limit).map((time, index) => ({
    time,
    temperature: data.temperature2m[index],
    weatherCode: data.weatherCode ? data.weatherCode[index] : 0,
  }));

  return (
    <GlassCard
      animate={false}
      className={cn(
        'p-6 col-span-full min-w-0 w-full',
        /* backdrop-filter + horizontal scroll = texture corruption on many mobile GPUs — use solid surface */
        'max-md:!backdrop-blur-none max-md:bg-white/[0.14] max-md:shadow-[0_4px_24px_rgba(0,0,0,0.2)]'
      )}
      testId="hourly-forecast"
    >
      <div className="flex items-center justify-between mb-4 gap-3 min-w-0">
        <h3 className="text-lg font-semibold text-white tracking-tight font-heading truncate">
          {t('weather.hourlyForecast')}
        </h3>
        <div className="flex gap-2 shrink-0">
          <button
            type="button"
            onClick={() => scroll('left')}
            className="p-2 rounded-full bg-white/10 hover:bg-white/20 transition-colors"
            data-testid="hourly-scroll-left"
            aria-label={String(t('weather.scrollLeft'))}
          >
            <ChevronLeft className="w-4 h-4 text-white" strokeWidth={1.5} />
          </button>
          <button
            type="button"
            onClick={() => scroll('right')}
            className="p-2 rounded-full bg-white/10 hover:bg-white/20 transition-colors"
            data-testid="hourly-scroll-right"
            aria-label={String(t('weather.scrollRight'))}
          >
            <ChevronRight className="w-4 h-4 text-white" strokeWidth={1.5} />
          </button>
        </div>
      </div>

      <div
        ref={scrollRef}
        className={cn(
          'hourly-scroll scrollbar-hide flex gap-3 pb-2',
          'snap-x snap-mandatory',
          '[scrollbar-width:none]'
        )}
        style={{ scrollbarWidth: 'none', msOverflowStyle: 'none' }}
        role="list"
        aria-label={String(t('weather.hourlyForecast'))}
      >
        {hourlyItems.map((item, index) => {
          const isNight = isNightTime(item.time);
          const isNow = index === 0;

          return (
            <div
              key={item.time.toISOString()}
              role="listitem"
              className={cn(
                'flex shrink-0 snap-start flex-col items-center gap-2 rounded-xl border p-4',
                /* Opaque-enough fills avoid alpha stacking artifacts next to scroll/compositor edges */
                'min-w-[5.5rem] basis-[5.5rem] max-w-[6rem]',
                'bg-black/25 border-white/15',
                'md:bg-white/5 md:border-white/10',
                'transition-colors duration-200',
                'hover:bg-white/10 md:hover:bg-white/10',
                isNow && 'border-white/35 bg-white/15 md:bg-white/15 md:border-white/30'
              )}
              data-testid={`hourly-item-${index}`}
            >
              <span
                className={cn(
                  'text-xs font-medium',
                  isNow ? 'text-white' : 'text-white/60'
                )}
              >
                {isNow ? t('weather.now') : new Intl.DateTimeFormat(currentLanguage, { 
                  hour: '2-digit', 
                  minute: '2-digit', 
                  hour12: false 
                }).format(item.time)}
              </span>
              <span className="flex shrink-0 [&_svg]:block">
                <WeatherIcon code={Number(item.weatherCode)} isNight={isNight} size="md" />
              </span>
              <span className="text-lg font-semibold text-white tabular-nums">
                {formatTemperature(Number(item.temperature), currentUnit)}
              </span>
            </div>
          );
        })}
      </div>
    </GlassCard>
  );
};
