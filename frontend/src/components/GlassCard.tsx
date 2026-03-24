import React from 'react';
import { cn } from '../utils/cn';
import { motion } from 'framer-motion';

interface GlassCardProps {
  children: React.ReactNode;
  className?: string;
  hover?: boolean;
  onClick?: () => void;
  testId?: string;
}

export const GlassCard: React.FC<GlassCardProps> = ({ 
  children, 
  className, 
  hover = false,
  onClick,
  testId 
}) => {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: 'easeOut' }}
      className={cn(
        'bg-white/10 backdrop-blur-xl border border-white/20',
        'shadow-[0_8px_32px_0_rgba(31,38,135,0.37)]',
        'rounded-2xl',
        hover && 'hover:bg-white/20 transition-all duration-300 ease-out hover:scale-[1.02] cursor-pointer',
        className
      )}
      onClick={onClick}
      data-testid={testId}
    >
      {children}
    </motion.div>
  );
};
