import React from 'react';
import { AlertTriangle, AlertCircle, Info, CheckCircle } from 'lucide-react';

const severityConfig = {
  CRITICAL: { color: 'bg-rose-500/15 text-rose-400 border-rose-500/30', icon: AlertCircle },
  HIGH: { color: 'bg-orange-500/15 text-orange-400 border-orange-500/30', icon: AlertTriangle },
  MEDIUM: { color: 'bg-amber-500/15 text-amber-400 border-amber-500/30', icon: AlertTriangle },
  LOW: { color: 'bg-blue-500/15 text-blue-400 border-blue-500/30', icon: Info },
};
const statusConfig = {
  ACTIVE: { color: 'bg-rose-500/15 text-rose-400 border-rose-500/30' },
  INVESTIGATING: { color: 'bg-amber-500/15 text-amber-400 border-amber-500/30' },
  RESOLVED: { color: 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30' },
  IGNORED: { color: 'bg-slate-500/15 text-slate-400 border-slate-500/30' },
};

export function SeverityBadge({ severity }) {
  const cfg = severityConfig[severity?.toUpperCase()] || severityConfig.LOW;
  const Icon = cfg.icon;
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium border ${cfg.color}`}>
      <Icon size={10} />
      {severity}
    </span>
  );
}

export function StatusBadge({ status }) {
  const cfg = statusConfig[status?.toUpperCase()] || statusConfig.ACTIVE;
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium border ${cfg.color}`}>
      <CheckCircle size={10} />
      {status}
    </span>
  );
}

export default function AnomalyBadge({ severity }) {
  return <SeverityBadge severity={severity} />;
}
