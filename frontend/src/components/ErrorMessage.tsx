import React from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';
import { GlassCard } from './GlassCard';
import { motion } from 'framer-motion';

interface ErrorMessageProps {
  message: string;
  onRetry?: () => void;
}

export const ErrorMessage: React.FC<ErrorMessageProps> = ({ message, onRetry }) => {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="col-span-full"
    >
      <GlassCard className="p-8" testId="error-message">
        <div className="flex flex-col items-center justify-center text-center">
          <AlertTriangle className="w-12 h-12 text-amber-400 mb-4" strokeWidth={1.5} />
          <h3 className="text-xl font-semibold text-white mb-2">Oops!</h3>
          <p className="text-white/70 mb-6 max-w-md">{message}</p>
          {onRetry && (
            <button
              onClick={onRetry}
              className="flex items-center gap-2 px-5 py-2.5 bg-white/20 hover:bg-white/30 rounded-full text-white transition-colors"
              data-testid="retry-button"
            >
              <RefreshCw className="w-4 h-4" strokeWidth={1.5} />
              Try Again
            </button>
          )}
        </div>
      </GlassCard>
    </motion.div>
  );
};
