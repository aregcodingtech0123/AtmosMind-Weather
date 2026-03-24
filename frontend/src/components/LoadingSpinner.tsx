import React from 'react';
import { Loader2 } from 'lucide-react';
import { motion } from 'framer-motion';

export const LoadingSpinner: React.FC = () => {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="flex flex-col items-center justify-center py-20"
      data-testid="loading-spinner"
    >
      <Loader2 className="w-12 h-12 text-white animate-spin" strokeWidth={1.5} />
      <p className="text-white/60 mt-4 text-sm">Loading weather data...</p>
    </motion.div>
  );
};
