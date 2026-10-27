import React from 'react';
import { motion } from 'framer-motion';

interface WeatherValueSkeletonProps {
  className?: string;
}

export function WeatherValueSkeleton({ className }: WeatherValueSkeletonProps) {
  return (
    <motion.span
      className={className ?? 'inline-block h-4 w-10 rounded bg-white/25 animate-pulse'}
      aria-hidden
      initial={{ opacity: 0.6 }}
      animate={{ opacity: [0.6, 1, 0.6] }}
      transition={{ duration: 1.2, repeat: Infinity }}
    />
  );
}

interface UnavailableFadeProps {
  show: boolean;
  children: React.ReactNode;
  className?: string;
}

/** Fade from skeleton/loading into unavailable copy (~200ms). */
export function UnavailableFade({ show, children, className }: UnavailableFadeProps) {
  return (
    <motion.div
      className={className}
      initial={false}
      animate={{ opacity: show ? 1 : 0 }}
      transition={{ duration: 0.2 }}
    >
      {children}
    </motion.div>
  );
}
