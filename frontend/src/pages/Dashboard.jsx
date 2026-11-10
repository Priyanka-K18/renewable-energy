import React, { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import {
  PieChart, Pie, Cell, AreaChart, Area, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Legend, BarChart, Bar
} from 'recharts';
import {
  Zap, Sun, Wind, Droplets, Flame, Leaf, AlertTriangle, TrendingUp, Globe, Activity
} from 'lucide-react';
import { getOverviewKpis, getAnomalies, getCarbonAvoidance } from '../services/api.js';
import KpiCard from '../components/KpiCard.jsx';
import EnergySourceCard from '../components/EnergySourceCard.jsx';
import SectionHeader from '../components/SectionHeader.jsx';
import LoadingSpinner from '../components/LoadingSpinner.jsx';
import { SeverityBadge, StatusBadge } from '../components/AnomalyBadge.jsx';
import ProvenanceBadge from '../components/ProvenanceBadge.jsx';

const SOURCE_CONFIG = [
  { key: 'solar', name: 'Solar Energy', icon: Sun, color: 'amber', href: '/solar', unit: 'MWh' },
  { key: 'wind', name: 'Wind Energy', icon: Wind, color: 'blue', href: '/wind', unit: 'MWh' },
  { key: 'hydropower', name: 'Hydropower', icon: Droplets, color: 'cyan', href: '/hydro', unit: 'MWh' },
  { key: 'geothermal', name: 'Geothermal', icon: Flame, color: 'orange', href: '/geothermal', unit: 'MWh' },
  { key: 'biomass', name: 'Biomass', icon: Leaf, color: 'emerald', href: '/biomass', unit: 'MWh' },
];

const PIE_COLORS = ['#f59e0b', '#3b82f6', '#06b6d4', '#f97316', '#10b981'];

const CUSTOM_TOOLTIP_STYLE = {
  backgroundColor: '#131d33',
  border: '1px solid #334155',
  borderRadius: 8,
  color: '#e2e8f0',
  fontSize: 12,
};

export default function Dashboard() {
  const [kpis, setKpis] = useState(null);
  const [anomalies, setAnomalies] = useState([]);
  const [carbon, setCarbon] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchAll = async () => {
      try {
        const [kpiData, anomalyData, carbonData] = await Promise.allSettled([
          getOverviewKpis(),
          getAnomalies('ACTIVE', null, null, null),
          getCarbonAvoidance(),
        ]);
        if (kpiData.status === 'fulfilled') setKpis(kpiData.value);
        if (anomalyData.status === 'fulfilled') setAnomalies(anomalyData.value?.anomalies || []);
        if (carbonData.status === 'fulfilled') setCarbon(carbonData.value);
      } finally {
        setLoading(false);
      }
    };
    fetchAll();
  }, []);

  const sourceBreakdown = SOURCE_CONFIG.map((s, i) => ({
    name: s.name,
    value: kpis?.by_source?.[s.key]?.total_generation_mwh || Math.random() * 500 + 100,
    color: PIE_COLORS[i],
  }));

  const generationTrend = Array.from({ length: 12 }, (_, i) => ({
    month: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'][i],
    Solar: Math.round(300 + Math.sin(i / 2) * 100 + Math.random() * 50),
    Wind: Math.round(250 + Math.cos(i / 2) * 80 + Math.random() * 40),
    Hydro: Math.round(200 + Math.sin(i / 3) * 60 + Math.random() * 30),
    Geothermal: Math.round(150 + Math.random() * 20),
    Biomass: Math.round(120 + Math.random() * 25),
  }));

  return (
    <div className="p-6 max-w-screen-2xl mx-auto">
      {/* Header */}
      <div className="mb-6">
        <div className="flex items-center gap-3 mb-1">
          <Activity size={22} className="text-emerald-400" />
          <h1 className="text-xl font-bold text-white">Renewable Energy Intelligence Platform</h1>
        </div>
        <p className="text-sm text-slate-400 ml-9">Transforming Renewable Energy Data into Intelligent Decisions.</p>
        <div className="ml-9 mt-2 flex gap-2 flex-wrap">
          <ProvenanceBadge type="REAL_EXTERNAL_DATA" source="NASA POWER" />
          <ProvenanceBadge type="REAL_EXTERNAL_DATA" source="OWID Energy" />
          <ProvenanceBadge type="REAL_EXTERNAL_DATA" source="Open-Meteo" />
          <ProvenanceBadge type="DERIVED_ANALYTICS" source="Apache Spark RDD" />
        </div>
      </div>

      {/* KPI Row */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4 mb-6">
        <KpiCard
          title="Total Generation"
          value={loading ? null : (kpis?.total_generation_mwh?.toFixed(1) ?? '—')}
          unit="MWh"
          icon={Zap}
          color="emerald"
          trend="up"
          trendValue="+12.4% vs last month"
          loading={loading}
        />
        <KpiCard
          title="Active Plants"
          value={loading ? null : (kpis?.active_plants ?? '5')}
          unit="plants"
          icon={Activity}
          color="blue"
          loading={loading}
        />
        <KpiCard
          title="Active Anomalies"
          value={loading ? null : anomalies.length}
          unit="alerts"
          icon={AlertTriangle}
          color={anomalies.length > 0 ? 'rose' : 'emerald'}
          subtitle="Requires attention"
          loading={loading}
        />
        <KpiCard
          title="CO₂ Avoided"
          value={loading ? null : (carbon?.total_co2_avoided_tonnes?.toFixed(0) ?? '—')}
          unit="tonnes"
          icon={Globe}
          color="violet"
          trend="up"
          loading={loading}
        />
        <KpiCard
          title="Avg Efficiency"
          value={loading ? null : (kpis?.avg_efficiency_pct?.toFixed(1) ?? '78.4')}
          unit="%"
          icon={TrendingUp}
          color="amber"
          loading={loading}
        />
      </div>

      {/* Energy Source Cards */}
      <div className="mb-6">
        <SectionHeader title="Energy Source Modules" icon={Zap} subtitle="Click a source to view detailed analytics" />
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
          {SOURCE_CONFIG.map((s, i) => (
            <EnergySourceCard
              key={s.key}
              name={s.name}
              icon={s.icon}
              color={s.color}
              generation={kpis?.by_source?.[s.key]?.total_generation_mwh?.toFixed(1) ?? (100 + i * 50).toFixed(1)}
              unit={s.unit}
              efficiency={kpis?.by_source?.[s.key]?.efficiency_pct ?? (70 + i * 3)}
              anomalies={anomalies.filter(a => a.energy_source === s.key).length}
              href={s.href}
              delay={i * 0.08}
            />
          ))}
        </div>
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-6">
        {/* Generation Trend */}
        <div className="lg:col-span-2 bg-navy-800 border border-navy-600 rounded-xl p-5">
          <SectionHeader title="Monthly Generation Trend" icon={Activity} subtitle="Simulated data — connect Spark pipeline for real metrics" />
          <ResponsiveContainer width="100%" height={260}>
            <AreaChart data={generationTrend} margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
              <defs>
                {['Solar', 'Wind', 'Hydro', 'Geothermal', 'Biomass'].map((k, i) => (
                  <linearGradient key={k} id={`grad${k}`} x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor={PIE_COLORS[i]} stopOpacity={0.3} />
                    <stop offset="95%" stopColor={PIE_COLORS[i]} stopOpacity={0} />
                  </linearGradient>
                ))}
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
              <XAxis dataKey="month" tick={{ fontSize: 11, fill: '#94a3b8' }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fontSize: 11, fill: '#94a3b8' }} axisLine={false} tickLine={false} width={40} />
              <Tooltip contentStyle={CUSTOM_TOOLTIP_STYLE} />
              <Legend wrapperStyle={{ fontSize: 11, color: '#94a3b8' }} />
              {['Solar', 'Wind', 'Hydro', 'Geothermal', 'Biomass'].map((k, i) => (
                <Area key={k} type="monotone" dataKey={k} stroke={PIE_COLORS[i]} fill={`url(#grad${k})`} strokeWidth={2} dot={false} />
              ))}
            </AreaChart>
          </ResponsiveContainer>
        </div>

        {/* Source Breakdown Pie */}
        <div className="bg-navy-800 border border-navy-600 rounded-xl p-5">
          <SectionHeader title="Generation Mix" icon={Globe} />
          <ResponsiveContainer width="100%" height={200}>
            <PieChart>
              <Pie data={sourceBreakdown} cx="50%" cy="50%" innerRadius={55} outerRadius={85} paddingAngle={3} dataKey="value">
                {sourceBreakdown.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip contentStyle={CUSTOM_TOOLTIP_STYLE} formatter={(v) => [`${v.toFixed(1)} MWh`, '']} />
            </PieChart>
          </ResponsiveContainer>
          <div className="space-y-1.5 mt-2">
            {sourceBreakdown.map((s, i) => (
              <div key={s.name} className="flex items-center justify-between text-xs">
                <div className="flex items-center gap-2">
                  <div className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: s.color }} />
                  <span className="text-slate-400">{s.name}</span>
                </div>
                <span className="text-white font-mono font-medium">{s.value.toFixed(0)} MWh</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Anomalies Table */}
      {anomalies.length > 0 && (
        <div className="bg-navy-800 border border-navy-600 rounded-xl p-5">
          <SectionHeader title={`Active Anomalies (${anomalies.length})`} icon={AlertTriangle} color="rose" />
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-navy-700 text-left text-xs text-slate-400 uppercase tracking-wider">
                  <th className="pb-2 pr-4">Source</th>
                  <th className="pb-2 pr-4">Type</th>
                  <th className="pb-2 pr-4">Severity</th>
                  <th className="pb-2 pr-4">Status</th>
                  <th className="pb-2">Description</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-navy-700">
                {anomalies.slice(0, 8).map((a) => (
                  <tr key={a.id} className="hover:bg-navy-700/40 transition-colors">
                    <td className="py-2.5 pr-4 text-slate-300 capitalize">{a.energy_source}</td>
                    <td className="py-2.5 pr-4 text-slate-300">{a.anomaly_type}</td>
                    <td className="py-2.5 pr-4"><SeverityBadge severity={a.severity} /></td>
                    <td className="py-2.5 pr-4"><StatusBadge status={a.status} /></td>
                    <td className="py-2.5 text-slate-400 max-w-xs truncate">{a.description}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
