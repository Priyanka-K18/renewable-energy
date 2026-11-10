import React from 'react';
import { Database, ShieldCheck, Cpu, LineChart } from 'lucide-react';

export default function ProvenanceBadge({ classification, className = '' }) {
  const configs = {
    REAL_EXTERNAL_DATA: {
      label: 'REAL EXTERNAL API',
      bg: 'bg-cyan-950/80 text-cyan-400 border-cyan-800/80',
      icon: Database,
      tooltip: 'Real-world verified observation retrieved from official external provider (NASA POWER / OWID / Open-Meteo)',
    },
    REAL_PLANT_DATA: {
      label: 'REAL PLANT TELEMETRY',
      bg: 'bg-emerald-950/80 text-emerald-400 border-emerald-800/80',
      icon: ShieldCheck,
      tooltip: 'Direct high-fidelity plant SCADA instrumentation data',
    },
    SIMULATED_DATA: {
      label: 'SIMULATED DATASET',
      bg: 'bg-amber-950/80 text-amber-400 border-amber-800/80',
      icon: Cpu,
      tooltip: 'Synthetic benchmark dataset generated with physical plant characteristics for evaluation',
    },
    DERIVED_ANALYTICS: {
      label: 'SPARK DERIVED RDD',
      bg: 'bg-purple-950/80 text-purple-400 border-purple-800/80',
      icon: LineChart,
      tooltip: 'Computed by Apache Spark RDD transformation and aggregation pipeline',
    },
  };

  const current = configs[classification] || configs.DERIVED_ANALYTICS;
  const Icon = current.icon;

  return (
    <span
      title={current.tooltip}
      className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[10px] font-mono font-semibold uppercase tracking-wider border shadow-sm ${current.bg} ${className}`}
    >
      <Icon className="w-3 h-3 shrink-0" />
      {current.label}
    </span>
  );
}
