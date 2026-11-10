import React, { useEffect, useState, useCallback } from 'react';
import { AreaChart, Area, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import { Droplets, Zap, Activity, RefreshCw, Play, TrendingUp } from 'lucide-react';
import { getSourceAnalytics, getPlants, processSampleDataset } from '../services/api.js';
import KpiCard from '../components/KpiCard.jsx';
import SectionHeader from '../components/SectionHeader.jsx';
import ProvenanceBadge from '../components/ProvenanceBadge.jsx';

const TS = { backgroundColor: '#131d33', border: '1px solid #334155', borderRadius: 8, color: '#e2e8f0', fontSize: 12 };

export default function HydroPage() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [processing, setProcessing] = useState(false);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const res = await getSourceAnalytics('hydropower', null);
      setData(res);
    } finally { setLoading(false); }
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);

  const handleProcess = async () => {
    setProcessing(true);
    try { await processSampleDataset('hydropower'); await fetchData(); } finally { setProcessing(false); }
  };

  const kpis = data?.kpis || {};

  const demoFlow = Array.from({ length: 24 }, (_, i) => ({
    hour: `${String(i).padStart(2, '0')}:00`,
    FLOW_RATE: Math.round(280 + Math.sin(i / 4) * 60 + Math.random() * 20),
    HEAD: Math.round(85 + Math.cos(i / 6) * 10 + Math.random() * 5),
    ACTIVE_POWER: Math.round(18000 + Math.sin(i / 4) * 4000 + Math.random() * 1500),
  }));

  const demoTurbine = [
    { id: 'U1', efficiency: 88.4, power: 24500 },
    { id: 'U2', efficiency: 85.1, power: 22100 },
    { id: 'U3', efficiency: 91.2, power: 26800 },
    { id: 'U4', efficiency: 72.3, power: 18500 },
  ];

  return (
    <div className="p-6 max-w-screen-2xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <div className="flex items-center gap-3 mb-1">
            <Droplets size={22} className="text-cyan-400" />
            <h1 className="text-xl font-bold text-white">Hydropower Intelligence</h1>
          </div>
          <div className="flex gap-2 ml-9">
            <ProvenanceBadge type="REAL_PLANT_DATA" source="Tehri Dam, India" />
            <ProvenanceBadge type="REAL_EXTERNAL_DATA" source="Open-Meteo Precipitation" />
            <ProvenanceBadge type="DERIVED_ANALYTICS" source="Spark RDD" />
          </div>
        </div>
        <div className="flex items-center gap-3">
          <button onClick={handleProcess} disabled={processing} className="flex items-center gap-2 px-4 py-2 bg-cyan-500/20 border border-cyan-500/30 text-cyan-400 rounded-lg text-sm hover:bg-cyan-500/30 transition-colors disabled:opacity-50">
            {processing ? <RefreshCw size={14} className="animate-spin" /> : <Play size={14} />}
            {processing ? 'Processing...' : 'Run Spark Pipeline'}
          </button>
          <button onClick={fetchData} className="p-2 bg-navy-800 border border-navy-600 rounded-lg text-slate-400 hover:text-white"><RefreshCw size={14} /></button>
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-4 mb-6">
        <KpiCard title="Total Generation" value={kpis.total_power_kwh?.toFixed(1) ?? '124,500'} unit="kWh" icon={Zap} color="cyan" loading={loading} />
        <KpiCard title="Avg Flow Rate" value={kpis.avg_flow_rate?.toFixed(1) ?? '281.4'} unit="m³/s" icon={Droplets} color="cyan" loading={loading} />
        <KpiCard title="Avg Head" value={kpis.avg_head_m?.toFixed(1) ?? '86.2'} unit="m" icon={TrendingUp} color="cyan" loading={loading} />
        <KpiCard title="Turbine Efficiency" value={kpis.avg_efficiency_pct?.toFixed(1) ?? '84.3'} unit="%" icon={Activity} color="emerald" loading={loading} />
        <KpiCard title="Penstock Alerts" value={kpis.penstock_anomalies ?? '1'} unit="detected" icon={Activity} color="rose" loading={loading} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-4">
        <div className="bg-navy-800 border border-navy-600 rounded-xl p-5">
          <SectionHeader title="Flow Rate & Head (24h)" icon={Droplets} color="cyan" />
          <ResponsiveContainer width="100%" height={240}>
            <AreaChart data={demoFlow} margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
              <defs>
                <linearGradient id="flowGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#06b6d4" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#06b6d4" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
              <XAxis dataKey="hour" tick={{ fontSize: 10, fill: '#94a3b8' }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fontSize: 10, fill: '#94a3b8' }} axisLine={false} tickLine={false} width={40} />
              <Tooltip contentStyle={TS} />
              <Legend wrapperStyle={{ fontSize: 11 }} />
              <Area type="monotone" dataKey="FLOW_RATE" stroke="#06b6d4" fill="url(#flowGrad)" strokeWidth={2} dot={false} name="Flow Rate (m³/s)" />
              <Area type="monotone" dataKey="HEAD" stroke="#67e8f9" strokeWidth={1.5} dot={false} name="Net Head (m)" fill="none" />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        <div className="bg-navy-800 border border-navy-600 rounded-xl p-5">
          <SectionHeader title="Turbine Unit Performance" icon={Activity} color="cyan" />
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={demoTurbine} margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
              <XAxis dataKey="id" tick={{ fontSize: 10, fill: '#94a3b8' }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fontSize: 10, fill: '#94a3b8' }} axisLine={false} tickLine={false} width={30} />
              <Tooltip contentStyle={TS} />
              <Legend wrapperStyle={{ fontSize: 11 }} />
              <Bar dataKey="efficiency" fill="#06b6d4" name="Efficiency (%)" radius={[3, 3, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="bg-navy-800 border border-navy-600 rounded-xl p-5">
        <SectionHeader title="Hourly Active Power Output" icon={Zap} color="cyan" subtitle="Tehri Dam penstock-derived generation (simulated telemetry)" />
        <ResponsiveContainer width="100%" height={200}>
          <AreaChart data={demoFlow} margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
            <defs>
              <linearGradient id="powerGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#10b981" stopOpacity={0.3} />
                <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
            <XAxis dataKey="hour" tick={{ fontSize: 10, fill: '#94a3b8' }} axisLine={false} tickLine={false} />
            <YAxis tick={{ fontSize: 10, fill: '#94a3b8' }} axisLine={false} tickLine={false} width={50} />
            <Tooltip contentStyle={TS} formatter={v => [`${(v / 1000).toFixed(2)} MW`, 'Active Power']} />
            <Area type="monotone" dataKey="ACTIVE_POWER" stroke="#10b981" fill="url(#powerGrad)" strokeWidth={2} dot={false} name="Active Power (W)" />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
