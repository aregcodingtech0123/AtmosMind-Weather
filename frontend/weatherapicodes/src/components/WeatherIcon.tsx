import React from 'react';
import {
  Sun,
  Moon,
  Cloud,
  CloudRain,
  CloudSnow,
  CloudLightning,
  CloudDrizzle,
  CloudFog,
  CloudSun,
  CloudMoon,
} from 'lucide-react';
import { cn } from '../utils/cn';

interface WeatherIconProps {
  code: number;
  isNight?: boolean;
  size?: 'sm' | 'md' | 'lg' | 'xl';
  className?: string;
}

const sizeClasses = {
  sm: 'w-6 h-6',
  md: 'w-8 h-8',
  lg: 'w-12 h-12',
  xl: 'w-20 h-20',
};

export const WeatherIcon: React.FC<WeatherIconProps> = ({ 
  code, 
  isNight = false,
  size = 'md',
  className 
}) => {
  const iconClass = cn(sizeClasses[size], 'text-white', className);
  const strokeWidth = 1.5;

  // Map WMO weather codes to icons
  const getIcon = () => {
    // Clear sky
    if (code === 0 || code === 1) {
      return isNight ? 
        <Moon className={iconClass} strokeWidth={strokeWidth} /> : 
        <Sun className={iconClass} strokeWidth={strokeWidth} />;
    }
    // Partly cloudy
    if (code === 2) {
      return isNight ?
        <CloudMoon className={iconClass} strokeWidth={strokeWidth} /> :
        <CloudSun className={iconClass} strokeWidth={strokeWidth} />;
    }
    // Overcast
    if (code === 3) {
      return <Cloud className={iconClass} strokeWidth={strokeWidth} />;
    }
    // Fog
    if (code >= 45 && code <= 48) {
      return <CloudFog className={iconClass} strokeWidth={strokeWidth} />;
    }
    // Drizzle
    if (code >= 51 && code <= 57) {
      return <CloudDrizzle className={iconClass} strokeWidth={strokeWidth} />;
    }
    // Rain
    if (code >= 61 && code <= 67) {
      return <CloudRain className={iconClass} strokeWidth={strokeWidth} />;
    }
    // Snow
    if (code >= 71 && code <= 77) {
      return <CloudSnow className={iconClass} strokeWidth={strokeWidth} />;
    }
    // Rain showers
    if (code >= 80 && code <= 82) {
      return <CloudRain className={iconClass} strokeWidth={strokeWidth} />;
    }
    // Snow showers
    if (code >= 85 && code <= 86) {
      return <CloudSnow className={iconClass} strokeWidth={strokeWidth} />;
    }
    // Thunderstorm
    if (code >= 95 && code <= 99) {
      return <CloudLightning className={iconClass} strokeWidth={strokeWidth} />;
    }
    // Default
    return isNight ? 
      <Moon className={iconClass} strokeWidth={strokeWidth} /> : 
      <Sun className={iconClass} strokeWidth={strokeWidth} />;
  };

  return getIcon();
};
