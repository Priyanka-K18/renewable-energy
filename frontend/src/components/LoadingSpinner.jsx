import React from 'react';
import { motion } from 'framer-motion';
import { Zap } from 'lucide-react';

export default function LoadingSpinner({ size = 'md', message = 'Loading...' }) {
  const sizes = { sm: 'h-4 w-4', md: 'h-8 w-8', lg: 'h-12 w-12' };
  const textSizes = { sm: 'text-xs', md: 'text-sm', lg: 'text-base' };
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-12">
      <motion.div
        animate={{ rotate: 360 }}
        transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
        className={`${sizes[size]} text-emerald-400`}
      >
        <Zap className="w-full h-full" />
      </motion.div>
      {message && (
        <p className={`${textSizes[size]} text-slate-400`}>{message}</p>
      )}
    </div>
  );
}
