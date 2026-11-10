import React from 'react';

export default function SectionHeader({ title, subtitle, icon: Icon, action, color = 'emerald' }) {
  const colorMap = {
    emerald: 'text-emerald-400',
    amber: 'text-amber-400',
    blue: 'text-blue-400',
    rose: 'text-rose-400',
    violet: 'text-violet-400',
    cyan: 'text-cyan-400',
    orange: 'text-orange-400',
  };
  return (
    <div className="flex items-center justify-between mb-5">
      <div className="flex items-center gap-3">
        {Icon && (
          <div className={`p-2 rounded-lg bg-navy-700 border border-navy-600`}>
            <Icon size={18} className={colorMap[color] || 'text-emerald-400'} />
          </div>
        )}
        <div>
          <h2 className="text-base font-semibold text-white">{title}</h2>
          {subtitle && <p className="text-xs text-slate-400 mt-0.5">{subtitle}</p>}
        </div>
      </div>
      {action && <div>{action}</div>}
    </div>
  );
}
