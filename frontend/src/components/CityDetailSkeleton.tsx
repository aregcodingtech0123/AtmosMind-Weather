import React from 'react';
import { motion } from 'framer-motion';
import { useTranslation } from 'react-i18next';
import { cn } from '../utils/cn';

interface CityDetailSkeletonProps {
  className?: string;
}

const pulse = 'animate-pulse rounded-2xl bg-white/10';

export const CityDetailSkeleton: React.FC<CityDetailSkeletonProps> = ({ className }) => {
  const { t } = useTranslation();

  return (
    <motion.div
      key="city-detail-skeleton"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.25 }}
      className={cn('grid grid-cols-12 gap-6', className)}
      data-testid="city-detail-skeleton"
      aria-busy="true"
      aria-label={String(t('cityDetail.loading'))}
    >
      <div className={cn('col-span-full lg:col-span-8 h-56 md:h-64', pulse)} />
      <div className="col-span-12 grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className={cn('h-40', pulse)} />
        ))}
      </div>
      <div className="col-span-12 flex justify-center gap-3">
        <div className={cn('h-11 w-40 rounded-full', pulse)} />
        <div className={cn('h-11 w-36 rounded-full', pulse)} />
      </div>
      <div className={cn('col-span-12 h-44', pulse)} />
      <div className={cn('col-span-full lg:col-span-6 h-72', pulse)} />
      <div className={cn('col-span-full lg:col-span-6 h-72', pulse)} />
      <p className="col-span-12 text-center text-sm text-white/55">{String(t('cityDetail.loading'))}</p>
    </motion.div>
  );
};
