import React from 'react';
import { GlassCard } from './GlassCard';
import { WeatherIcon } from './WeatherIcon';
import { Droplets, Wind, Thermometer, Heart } from 'lucide-react';
import { CurrentWeather as CurrentWeatherType } from '../types/weather';
import { 
  formatTemperature, 
  getWeatherDescription,
  formatFullDate,
  isNightTime
} from '../utils/weatherUtils';
import { cn } from '../utils/cn';
import { useSettings } from '../context/SettingsContext';
import { useTranslation } from 'react-i18next';

interface CurrentWeatherProps {
  data: CurrentWeatherType;
  cityName: string;
  isFavorite: boolean;
  onToggleFavorite: () => void;
}

export const CurrentWeatherComponent: React.FC<CurrentWeatherProps> = ({ 
  data, 
  cityName,
  isFavorite,
  onToggleFavorite
}) => {
    const { currentUnit, currentLanguage } = useSettings();
  const { t } = useTranslation();
  const isNight = isNightTime();

  return (
    <GlassCard className="p-6 md:p-8 col-span-full lg:col-span-8" testId="current-weather">
      <div className="flex flex-col md:flex-row justify-between gap-6">
        {/* Left side - Main info */}
        <div className="flex-1">
          <div className="flex items-center gap-3 mb-2">
            <h2 className="text-2xl md:text-3xl font-semibold capitalize tracking-tight text-white font-heading">
              {cityName}
            </h2>
            <button
              onClick={onToggleFavorite}
              className={cn(
                'p-2 rounded-full transition-all duration-200',
                'hover:bg-white/20 active:scale-95'
              )}
              data-testid="favorite-toggle"
              aria-label={String(isFavorite ? t('weather.removeFromFavorites') : t('weather.addToFavorites'))}
            >
              <Heart 
                className={cn(
                  'w-5 h-5 transition-colors',
                  isFavorite ? 'fill-red-400 text-red-400' : 'text-white/60'
                )} 
                strokeWidth={1.5} 
              />
            </button>
          </div>
          <p className="text-white/70 text-sm mb-6">{formatFullDate(new Date(), currentLanguage)}</p>
          
          <div className="flex items-start gap-4">
            <WeatherIcon code={data.weatherCode} isNight={isNight} size="xl" />
            <div>
              <p className="text-8xl md:text-9xl font-bold tracking-tighter text-white font-heading leading-none">
                {formatTemperature(data.temperature, currentUnit)}
              </p>
              <p className="text-lg text-white/80 mt-2">
                {getWeatherDescription(data.weatherCode)}
              </p>
            </div>
          </div>
        </div>

        {/* Right side - Details */}
        <div className="flex flex-col justify-end gap-4">
          <div className="flex items-center gap-3 text-white/80">
            <Thermometer className="w-5 h-5" strokeWidth={1.5} />
            <span className="text-sm">{t('weather.feelsLike')}</span>
            <span className="font-semibold">
              {formatTemperature(data.feelsLike || data.temperature, currentUnit)}
            </span>
          </div>
          <div className="flex items-center gap-3 text-white/80">
            <Droplets className="w-5 h-5" strokeWidth={1.5} />
            <span className="text-sm">{t('weather.humidity')}</span>
            <span className="font-semibold">{Math.round(data.humidity || 0)}%</span>
          </div>
          <div className="flex items-center gap-3 text-white/80">
            <Wind className="w-5 h-5" strokeWidth={1.5} />
            <span className="text-sm">{t('weather.wind')}</span>
            <span className="font-semibold">{Math.round(data.windSpeed || 0)} {t('weather.kmh')}</span>
          </div>
        </div>
      </div>
    </GlassCard>
  );
};
