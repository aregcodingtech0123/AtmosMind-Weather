import React, { useEffect, useId, useRef, useState } from 'react';
import { GlassCard } from './GlassCard';
import { HourlyData } from '../types/weather';
import { prepareChartData } from '../utils/weatherUtils';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
} from 'recharts';
import { useSettings } from '../context/SettingsContext';
import { useTranslation } from 'react-i18next';
import { convertTemperature } from '../utils/weatherUtils';

interface WeatherChartProps {
  data: HourlyData;
  limit?: number;
}

const CHART_HEIGHT = 250;

const CustomTooltip = ({ active, payload, unit }: any) => {
  if (active && payload && payload.length) {
    const temp = convertTemperature(Number(payload[0].value), unit);
    return (
      <div className="bg-black/60 backdrop-blur-md border border-white/10 rounded-lg px-3 py-2 shadow-xl">
        <p className="text-white font-semibold">{Math.round(temp)}{unit === 'imperial' ? '°F' : '°C'}</p>
        <p className="text-white/60 text-sm">{payload[0].payload.hour}</p>
      </div>
    );
  }
  return null;
};

export const WeatherChart: React.FC<WeatherChartProps> = ({ data, limit = 24 }) => {
  const { currentUnit, currentLanguage } = useSettings();
  const { t } = useTranslation();
  const chartData = prepareChartData(data.time, data.temperature2m, limit, currentLanguage);
  const reactId = useId();
  const gradientId = `temperatureGradient-${reactId.replace(/:/g, '')}`;
  const containerRef = useRef<HTMLDivElement>(null);
  const [chartWidth, setChartWidth] = useState(0);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return undefined;

    const measure = () => {
      requestAnimationFrame(() => {
        const w = el.clientWidth;
        if (w <= 0) return;
        setChartWidth((prev) => (Math.abs(prev - w) < 0.5 ? prev : w));
      });
    };

    measure();
    const ro = new ResizeObserver(measure);
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  return (
    <GlassCard className="p-6 col-span-full lg:col-span-8" testId="weather-chart">
      <h3 className="text-lg font-semibold text-white tracking-tight font-heading mb-4">
        {t('weather.temperatureTrend')}
      </h3>

      <div ref={containerRef} className="h-[250px] w-full min-w-0">
        {chartWidth > 0 && (
          <AreaChart
            width={chartWidth}
            height={CHART_HEIGHT}
            data={chartData}
            margin={{ top: 10, right: 10, left: -20, bottom: 0 }}
          >
            <defs>
              <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#ffffff" stopOpacity={0.3} />
                <stop offset="95%" stopColor="#ffffff" stopOpacity={0} />
              </linearGradient>
            </defs>
            <XAxis
              dataKey="hour"
              axisLine={false}
              tickLine={false}
              tick={{ fill: 'rgba(255,255,255,0.5)', fontSize: 12 }}
              interval="preserveStartEnd"
            />
            <YAxis
              axisLine={false}
              tickLine={false}
              tick={{ fill: 'rgba(255,255,255,0.5)', fontSize: 12 }}
              domain={['dataMin - 2', 'dataMax + 2']}
              tickFormatter={(value) => {
                const converted = convertTemperature(Number(value), currentUnit);
                return `${Math.round(converted)}°`;
              }}
            />
            <Tooltip content={<CustomTooltip unit={currentUnit} />} />
            <Area
              type="monotone"
              dataKey="temperature"
              stroke="#ffffff"
              strokeWidth={2}
              fill={`url(#${gradientId})`}
              dot={false}
              activeDot={{ r: 6, fill: '#ffffff', stroke: 'rgba(255,255,255,0.3)', strokeWidth: 3 }}
            />
          </AreaChart>
        )}
      </div>
    </GlassCard>
  );
};
