import React from 'react';
import { motion } from 'framer-motion';
import { Link } from 'react-router-dom';
import { ArrowRight, AlertTriangle } from 'lucide-react';

export default function EnergySourceCard({ name, icon: Icon, color, generation, unit, efficiency, anomalies = 0, href, delay = 0 }) {
  const colorMap = {
    amber: { text: 'text-amber-400', bg: 'bg-amber-400/10', border: 'border-amber-400/20', bar: 'bg-amber-400' },
    blue: { text: 'text-blue-400', bg: 'bg-blue-400/10', border: 'border-blue-400/20', bar: 'bg-blue-400' },
    cyan: { text: 'text-cyan-400', bg: 'bg-cyan-400/10', border: 'border-cyan-400/20', bar: 'bg-cyan-400' },
    orange: { text: 'text-orange-400', bg: 'bg-orange-400/10', border: 'border-orange-400/20', bar: 'bg-orange-400' },
    emerald: { text: 'text-emerald-400', bg: 'bg-emerald-400/10', border: 'border-emerald-400/20', bar: 'bg-emerald-400' },
    violet: { text: 'text-violet-400', bg: 'bg-violet-400/10', border: 'border-violet-400/20', bar: 'bg-violet-400' },
  };
  const c = colorMap[color] || colorMap.emerald;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay }}
    >
      <Link to={href} className="block bg-navy-800 border border-navy-600 rounded-xl p-5 hover:border-navy-500 transition-all duration-200 group">
        <div className="flex items-center justify-between mb-4">
          <div className={`p-2.5 rounded-lg border ${c.bg} ${c.border}`}>
            <Icon size={20} className={c.text} />
          </div>
          {anomalies > 0 && (
            <span className="flex items-center gap-1 text-xs text-orange-400 bg-orange-400/10 border border-orange-400/20 px-2 py-0.5 rounded-full">
              <AlertTriangle size={10} />
              {anomalies} alert{anomalies > 1 ? 's' : ''}
            </span>
          )}
        </div>
        <h3 className="text-sm font-semibold text-white mb-1">{name}</h3>
        <div className="flex items-baseline gap-1 mb-3">
          <span className={`text-xl font-bold font-mono ${c.text}`}>{generation ?? '—'}</span>
          <span className="text-xs text-slate-400">{unit}</span>
        </div>
        {efficiency !== undefined && (
          <>
            <div className="flex justify-between text-xs text-slate-400 mb-1.5">
              <span>Efficiency</span>
              <span className="text-white font-medium">{efficiency}%</span>
            </div>
            <div className="h-1.5 bg-navy-700 rounded-full overflow-hidden">
              <motion.div
                initial={{ width: 0 }}
                animate={{ width: `${efficiency}%` }}
                transition={{ duration: 0.8, delay: delay + 0.2 }}
                className={`h-full rounded-full ${c.bar}`}
              />
            </div>
          </>
        )}
        <div className={`flex items-center gap-1 mt-3 text-xs ${c.text} opacity-0 group-hover:opacity-100 transition-opacity`}>
          <span>View analytics</span>
          <ArrowRight size={12} />
        </div>
      </Link>
    </motion.div>
  );
}
