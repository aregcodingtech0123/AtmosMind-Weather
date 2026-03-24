import React, { useRef } from 'react';
import { GlassCard } from './GlassCard';
import { WeatherIcon } from './WeatherIcon';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import { HourlyData } from '../types/weather';
import { formatTemperature, formatHourlyTime, isNightTime } from '../utils/weatherUtils';
import { cn } from '../utils/cn';
import { motion } from 'framer-motion';
import { useSettings } from '../context/SettingsContext';
import { useTranslation } from 'react-i18next';

interface HourlyForecastProps {
  data: HourlyData;
  limit?: number;
}

export const HourlyForecast: React.FC<HourlyForecastProps> = ({ data, limit = 24 }) => {
  const { currentUnit } = useSettings();
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
    <GlassCard className="p-6 col-span-full" testId="hourly-forecast">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-white tracking-tight font-heading">
          {t('weather.hourlyForecast')}
        </h3>
        <div className="flex gap-2">
          <button
            onClick={() => scroll('left')}
            className="p-2 rounded-full bg-white/10 hover:bg-white/20 transition-colors"
            data-testid="hourly-scroll-left"
            aria-label={String(t('weather.scrollLeft'))}
          >
            <ChevronLeft className="w-4 h-4 text-white" strokeWidth={1.5} />
          </button>
          <button
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
        className="flex gap-3 overflow-x-auto scrollbar-hide pb-2"
        style={{ scrollbarWidth: 'none', msOverflowStyle: 'none' }}
      >
        {hourlyItems.map((item, index) => {
          const isNight = isNightTime(item.time);
          const isNow = index === 0;
          
          return (
            <motion.div
              key={item.time.toISOString()}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3, delay: index * 0.03 }}
              className={cn(
                'flex-shrink-0 flex flex-col items-center gap-2 p-4 rounded-xl',
                'bg-white/5 border border-white/10',
                'min-w-[80px] transition-all duration-200',
                'hover:bg-white/10',
                isNow && 'bg-white/15 border-white/30'
              )}
              data-testid={`hourly-item-${index}`}
            >
              <span className={cn(
                'text-xs font-medium',
                isNow ? 'text-white' : 'text-white/60'
              )}>
                {isNow ? t('weather.now') : formatHourlyTime(item.time)}
              </span>
              <WeatherIcon 
                code={Number(item.weatherCode)} 
                isNight={isNight} 
                size="md" 
              />
              <span className="text-lg font-semibold text-white">
                {formatTemperature(Number(item.temperature), currentUnit)}
              </span>
            </motion.div>
          );
        })}
      </div>
    </GlassCard>
  );
};
