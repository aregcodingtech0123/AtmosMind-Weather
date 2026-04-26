import React from 'react';
import { GlassCard } from './GlassCard';
import { WeatherIcon } from './WeatherIcon';
import { DailyData } from '../types/weather';
import { formatTemperature } from '../utils/weatherUtils';
import { cn } from '../utils/cn';
import { motion } from 'framer-motion';
import { useSettings } from '../context/SettingsContext';
import { useTranslation } from 'react-i18next';

interface DailyForecastProps {
  data: DailyData;
}

export const DailyForecast: React.FC<DailyForecastProps> = ({ data }) => {
  const { currentUnit, currentLanguage } = useSettings();
  const { t } = useTranslation();
  return (
    <GlassCard className="p-6 col-span-full lg:col-span-4" testId="daily-forecast">
      <h3 className="text-lg font-semibold text-white tracking-tight font-heading mb-4">
        {t('weather.sevenDayForecast')}
      </h3>

      <div className="space-y-3">
        {data.time.map((time, index) => {
          const isToday = index === 0;
          
          return (
            <motion.div
              key={time.toISOString()}
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.3, delay: index * 0.05 }}
              className={cn(
                'flex items-center justify-between p-3 rounded-xl',
                'bg-white/5 border border-white/10',
                'hover:bg-white/10 transition-all duration-200',
                isToday && 'bg-white/15 border-white/30'
              )}
              data-testid={`daily-item-${index}`}
            >
              <div className="flex items-center gap-3 min-w-[100px]">
                <span className={cn(
                  'text-sm font-medium w-12',
                  isToday ? 'text-white' : 'text-white/70'
                )}>
                  {isToday 
                    ? t('weather.today') 
                    : new Intl.DateTimeFormat(currentLanguage, { weekday: 'short' }).format(time)}
                </span>
              </div>

              <WeatherIcon 
                code={data.weatherCode[index]} 
                size="sm" 
              />

              <div className="flex items-center gap-2">
                <span className="text-white font-semibold">
                  {formatTemperature(data.temperatureMax[index], currentUnit)}
                </span>
                <span className="text-white/50">/</span>
                <span className="text-white/60">
                  {formatTemperature(data.temperatureMin[index], currentUnit)}
                </span>
              </div>
            </motion.div>
          );
        })}
      </div>
    </GlassCard>
  );
};
