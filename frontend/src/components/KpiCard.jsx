import React from 'react';
import { motion } from 'framer-motion';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';

export default function KpiCard({ title, value, unit, trend, trendValue, icon: Icon, color = 'emerald', subtitle, loading }) {
  const colorMap = {
    emerald: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20',
    amber: 'text-amber-400 bg-amber-500/10 border-amber-500/20',
    blue: 'text-blue-400 bg-blue-500/10 border-blue-500/20',
    rose: 'text-rose-400 bg-rose-500/10 border-rose-500/20',
    violet: 'text-violet-400 bg-violet-500/10 border-violet-500/20',
    cyan: 'text-cyan-400 bg-cyan-500/10 border-cyan-500/20',
    orange: 'text-orange-400 bg-orange-500/10 border-orange-500/20',
  };

  const iconBg = colorMap[color] || colorMap.emerald;
  const trendIcon = trend === 'up' ? TrendingUp : trend === 'down' ? TrendingDown : Minus;
  const trendColor = trend === 'up' ? 'text-emerald-400' : trend === 'down' ? 'text-rose-400' : 'text-navy-600';
  const TrendIcon = trendIcon;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="bg-navy-800 border border-navy-600 rounded-xl p-5 hover:border-navy-500 transition-all duration-200"
    >
      <div className="flex items-start justify-between">
        <div className="flex-1 min-w-0">
          <p className="text-xs font-medium text-slate-400 uppercase tracking-wider truncate">{title}</p>
          <div className="mt-2 flex items-baseline gap-1">
            {loading ? (
              <div className="h-8 w-24 bg-navy-700 rounded animate-pulse" />
            ) : (
              <span className="text-2xl font-bold text-white font-mono">
                {value ?? '—'}
              </span>
            )}
            {unit && !loading && (
              <span className="text-sm text-slate-400 ml-1">{unit}</span>
            )}
          </div>
          {subtitle && (
            <p className="text-xs text-slate-500 mt-1">{subtitle}</p>
          )}
          {trendValue && !loading && (
            <div className={`flex items-center gap-1 mt-2 ${trendColor}`}>
              <TrendIcon size={12} />
              <span className="text-xs font-medium">{trendValue}</span>
            </div>
          )}
        </div>
        {Icon && (
          <div className={`ml-3 p-2.5 rounded-lg border ${iconBg} flex-shrink-0`}>
            <Icon size={18} className={iconBg.split(' ')[0]} />
          </div>
        )}
      </div>
    </motion.div>
  );
}
