import React, { useEffect, useMemo, useState } from 'react';
import { AnimatePresence, motion, useReducedMotion } from 'framer-motion';
import { resolveWmoBackgroundTheme, type WmoBackgroundTheme } from '../utils/weatherUtils';
import { cn } from '../utils/cn';

export interface DynamicWeatherBackgroundProps {
  /** Active Open-Meteo / WMO weather code from current conditions. */
  weatherCode: number;
  isNight?: boolean;
  className?: string;
}

const RAIN_DROPS = Array.from({ length: 16 }, (_, i) => ({
  id: i,
  left: `${((i * 17 + 7) % 97) + 1}%`,
  delay: (i % 6) * 0.28,
  duration: 1.6 + (i % 4) * 0.25,
  opacity: 0.2 + (i % 3) * 0.05,
  height: 14 + (i % 3) * 6,
}));

const SNOW_FLAKES = Array.from({ length: 20 }, (_, i) => ({
  id: i,
  left: `${((i * 13 + 5) % 95) + 2}%`,
  size: 2 + (i % 3),
  delay: (i % 8) * 0.45,
  duration: 6 + (i % 5) * 1.2,
  drift: i % 2 === 0 ? 12 : -10,
}));

const BASE_GRADIENTS: Record<WmoBackgroundTheme, string> = {
  clear: 'from-slate-950 via-[#0c1222] to-slate-950',
  rainy: 'from-[#0a1628] via-[#0f2744] to-[#0a1628]',
  stormy: 'from-[#05070d] via-[#0d1525] to-[#05070d]',
  snowy: 'from-[#101820] via-[#1a2836] to-[#0d1218]',
  cloudy: 'from-[#121820] via-[#1a242e] to-[#101418]',
};

function ClearLayer({ isNight }: { isNight: boolean }) {
  return (
    <>
      <motion.div
        aria-hidden
        className={cn(
          'absolute h-[55vmax] w-[55vmax] rounded-full blur-3xl',
          isNight ? 'bg-amber-400/12' : 'bg-amber-300/20'
        )}
        style={{ top: '-12%', left: '-8%', willChange: 'transform' }}
        animate={{ x: [0, 36, -18, 0], y: [0, 22, -12, 0] }}
        transition={{ duration: 28, repeat: Infinity, ease: 'easeInOut' }}
      />
      <motion.div
        aria-hidden
        className={cn(
          'absolute h-[48vmax] w-[48vmax] rounded-full blur-3xl',
          isNight ? 'bg-cyan-400/10' : 'bg-cyan-300/18'
        )}
        style={{ bottom: '-10%', right: '-6%', willChange: 'transform' }}
        animate={{ x: [0, -28, 14, 0], y: [0, -18, 10, 0] }}
        transition={{ duration: 32, repeat: Infinity, ease: 'easeInOut' }}
      />
      <motion.div
        aria-hidden
        className="absolute h-[32vmax] w-[32vmax] rounded-full bg-teal-400/10 blur-3xl"
        style={{ top: '35%', right: '18%', willChange: 'transform' }}
        animate={{ x: [0, 20, -12, 0], y: [0, -14, 8, 0] }}
        transition={{ duration: 24, repeat: Infinity, ease: 'easeInOut' }}
      />
    </>
  );
}

function RainLayer() {
  return (
    <div aria-hidden className="absolute inset-0 overflow-hidden">
      {RAIN_DROPS.map((drop) => (
        <motion.span
          key={drop.id}
          className="absolute w-px rounded-full bg-gradient-to-b from-white/0 via-white/40 to-white/0"
          style={{
            left: drop.left,
            height: drop.height,
            opacity: drop.opacity,
            willChange: 'transform',
          }}
          initial={{ y: '-12vh' }}
          animate={{ y: '112vh' }}
          transition={{
            duration: drop.duration,
            repeat: Infinity,
            delay: drop.delay,
            ease: 'linear',
          }}
        />
      ))}
    </div>
  );
}

function StormLayer({ reduceMotion }: { reduceMotion: boolean }) {
  const [flash, setFlash] = useState(false);

  useEffect(() => {
    if (reduceMotion) return undefined;

    let timeoutId: ReturnType<typeof setTimeout>;
    let cancelled = false;

    const scheduleFlash = () => {
      const wait = 4500 + Math.random() * 5000;
      timeoutId = setTimeout(() => {
        if (cancelled) return;
        setFlash(true);
        timeoutId = setTimeout(() => {
          setFlash(false);
          if (!cancelled) scheduleFlash();
        }, 180);
      }, wait);
    };

    scheduleFlash();
    return () => {
      cancelled = true;
      clearTimeout(timeoutId);
    };
  }, [reduceMotion]);

  return (
    <>
      <motion.div
        aria-hidden
        className="absolute inset-0 bg-gradient-to-br from-indigo-950/40 via-transparent to-violet-950/30"
        animate={flash ? { opacity: [0.15, 0.45, 0.12] } : { opacity: 0.15 }}
        transition={{ duration: 0.18, ease: 'easeOut' }}
      />
      <AnimatePresence>
        {flash && !reduceMotion && (
          <motion.div
            key="lightning"
            aria-hidden
            className="absolute inset-0 bg-gradient-to-tr from-cyan-200/10 via-violet-300/12 to-transparent"
            initial={{ opacity: 0 }}
            animate={{ opacity: [0, 0.35, 0] }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.22, ease: 'easeOut' }}
          />
        )}
      </AnimatePresence>
    </>
  );
}

function SnowLayer() {
  return (
    <div aria-hidden className="absolute inset-0 overflow-hidden">
      {SNOW_FLAKES.map((flake) => (
        <motion.span
          key={flake.id}
          className="absolute rounded-full bg-white/70 blur-[0.5px]"
          style={{
            left: flake.left,
            width: flake.size,
            height: flake.size,
            willChange: 'transform',
          }}
          initial={{ y: '-8vh', x: 0, opacity: 0.35 }}
          animate={{
            y: '108vh',
            x: [0, flake.drift, -flake.drift * 0.5, 0],
            opacity: [0.25, 0.55, 0.4, 0.2],
          }}
          transition={{
            duration: flake.duration,
            repeat: Infinity,
            delay: flake.delay,
            ease: 'linear',
          }}
        />
      ))}
    </div>
  );
}

function CloudyLayer() {
  return (
    <>
      <motion.div
        aria-hidden
        className="absolute h-[60vmax] w-[70vmax] rounded-full bg-slate-400/12 blur-3xl"
        style={{ top: '-18%', left: '-15%', willChange: 'transform' }}
        animate={{ x: [0, 40, -20, 0], y: [0, 16, -8, 0] }}
        transition={{ duration: 36, repeat: Infinity, ease: 'easeInOut' }}
      />
      <motion.div
        aria-hidden
        className="absolute h-[50vmax] w-[55vmax] rounded-full bg-teal-500/8 blur-3xl"
        style={{ bottom: '-12%', right: '-10%', willChange: 'transform' }}
        animate={{ x: [0, -32, 18, 0], y: [0, -12, 6, 0] }}
        transition={{ duration: 30, repeat: Infinity, ease: 'easeInOut' }}
      />
      <motion.div
        aria-hidden
        className="absolute h-[38vmax] w-[42vmax] rounded-full bg-slate-300/10 blur-3xl"
        style={{ top: '28%', left: '30%', willChange: 'transform' }}
        animate={{ x: [0, 24, -16, 0], y: [0, 10, -6, 0] }}
        transition={{ duration: 26, repeat: Infinity, ease: 'easeInOut' }}
      />
    </>
  );
}

function ThemeLayers({
  theme,
  isNight,
  reduceMotion,
}: {
  theme: WmoBackgroundTheme;
  isNight: boolean;
  reduceMotion: boolean;
}) {
  if (reduceMotion) {
    return null;
  }

  switch (theme) {
    case 'clear':
      return <ClearLayer isNight={isNight} />;
    case 'rainy':
      return <RainLayer />;
    case 'stormy':
      return <StormLayer reduceMotion={reduceMotion} />;
    case 'snowy':
      return <SnowLayer />;
    case 'cloudy':
      return <CloudyLayer />;
    default:
      return null;
  }
}

/**
 * Fixed, lightweight WMO-driven ambient background for city detail pages.
 * Sits behind all content (`z-0`); pair with `relative z-10` on the page shell.
 */
export const DynamicWeatherBackground: React.FC<DynamicWeatherBackgroundProps> = ({
  weatherCode,
  isNight = false,
  className,
}) => {
  const reduceMotion = useReducedMotion();
  const theme = useMemo(
    () => resolveWmoBackgroundTheme(weatherCode, isNight),
    [weatherCode, isNight]
  );

  return (
    <div
      aria-hidden
      className={cn(
        'pointer-events-none fixed inset-0 z-0 overflow-hidden',
        className
      )}
      data-testid="dynamic-weather-background"
      data-weather-theme={theme}
    >
      <AnimatePresence mode="wait">
        <motion.div
          key={theme}
          className={cn('absolute inset-0 bg-gradient-to-br', BASE_GRADIENTS[theme])}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.9, ease: 'easeInOut' }}
        />
      </AnimatePresence>

      <ThemeLayers theme={theme} isNight={isNight} reduceMotion={!!reduceMotion} />

      {/* Readability scrim — keeps glass panels and text contrast stable */}
      <div className="absolute inset-0 bg-gradient-to-b from-slate-950/35 via-slate-950/10 to-slate-950/55" />
    </div>
  );
};
