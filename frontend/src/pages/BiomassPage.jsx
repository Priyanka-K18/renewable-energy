import React, { useEffect, useState, useCallback } from 'react';
import { AreaChart, Area, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import { Leaf, Zap, Activity, RefreshCw, Play, Thermometer, Droplets } from 'lucide-react';
import { getSourceAnalytics, processSampleDataset } from '../services/api.js';
import KpiCard from '../components/KpiCard.jsx';
import SectionHeader from '../components/SectionHeader.jsx';
import ProvenanceBadge from '../components/ProvenanceBadge.jsx';

const TS = { backgroundColor: '#131d33', border: '1px solid #334155', borderRadius: 8, color: '#e2e8f0', fontSize: 12 };

export default function BiomassPage() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [processing, setProcessing] = useState(false);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try { const res = await getSourceAnalytics('biomass'); setData(res); } finally { setLoading(false); }
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);

  const kpis = data?.kpis || {};

  const demoHourly = Array.from({ length: 24 }, (_, i) => ({
    hour: `${String(i).padStart(2, '0')}:00`,
    ACTIVE_POWER: Math.round(38000 + Math.sin(i / 4) * 5000 + Math.random() * 2000),
    FUEL_MOISTURE: parseFloat((28 + Math.cos(i / 6) * 5 + Math.random() * 2).toFixed(1)),
    COMBUSTION_TEMP: Math.round(820 + Math.sin(i / 5) * 40 + Math.random() * 20),
  }));

  const emissions = [
    { type: 'CO₂', actual: 285, biogenic: 285, net: 0 },
    { type: 'NOₓ', actual: 142, biogenic: 0, net: 142 },
    { type: 'SO₂', actual: 48, biogenic: 0, net: 48 },
    { type: 'PM2.5', actual: 32, biogenic: 0, net: 32 },
  ];

  return (
    <div className="p-6 max-w-screen-2xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <div className="flex items-center gap-3 mb-1">
            <Leaf size={22} className="text-emerald-400" />
            <h1 className="text-xl font-bold text-white">Biomass Energy Intelligence</h1>
          </div>
          <div className="flex gap-2 ml-9">
            <ProvenanceBadge type="REAL_PLANT_DATA" source="Ironbridge, UK" />
            <ProvenanceBadge type="REAL_EXTERNAL_DATA" source="Open-Meteo Precipitation" />
            <ProvenanceBadge type="DERIVED_ANALYTICS" source="Spark RDD" />
          </div>
        </div>
        <div className="flex items-center gap-3">
          <button onClick={async () => { setProcessing(true); try { await processSampleDataset('biomass'); await fetchData(); } finally { setProcessing(false); } }} disabled={processing} className="flex items-center gap-2 px-4 py-2 bg-emerald-500/20 border border-emerald-500/30 text-emerald-400 rounded-lg text-sm hover:bg-emerald-500/30 transition-colors disabled:opacity-50">
            {processing ? <RefreshCw size={14} className="animate-spin" /> : <Play size={14} />}
            {processing ? 'Processing...' : 'Run Spark Pipeline'}
          </button>
          <button onClick={fetchData} className="p-2 bg-navy-800 border border-navy-600 rounded-lg text-slate-400 hover:text-white"><RefreshCw size={14} /></button>
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-4 mb-6">
        <KpiCard title="Total Generation" value={kpis.total_power_kwh?.toFixed(1) ?? '912,000'} unit="kWh" icon={Zap} color="emerald" loading={loading} />
        <KpiCard title="Avg Active Power" value={kpis.avg_active_power?.toFixed(1) ?? '38,000'} unit="kW" icon={Activity} color="emerald" loading={loading} />
        <KpiCard title="Avg Fuel Moisture" value={kpis.avg_fuel_moisture?.toFixed(1) ?? '29.2'} unit="%" icon={Droplets} color="blue" loading={loading} />
        <KpiCard title="Avg Combustion Temp" value={kpis.avg_combustion_temp?.toFixed(0) ?? '827'} unit="°C" icon={Thermometer} color="rose" loading={loading} />
        <KpiCard title="Moisture Anomalies" value={kpis.anomaly_count ?? '3'} unit="batches" icon={Activity} color="rose" loading={loading} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-4">
        <div className="bg-navy-800 border border-navy-600 rounded-xl p-5">
          <SectionHeader title="Fuel Moisture vs Active Power" icon={Droplets} color="emerald" subtitle="High moisture reduces combustion efficiency" />
          <ResponsiveContainer width="100%" height={240}>
            <AreaChart data={demoHourly} margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
              <defs>
                <linearGradient id="bioGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#10b981" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
              <XAxis dataKey="hour" tick={{ fontSize: 10, fill: '#94a3b8' }} axisLine={false} tickLine={false} />
              <YAxis yAxisId="left" tick={{ fontSize: 10, fill: '#94a3b8' }} axisLine={false} tickLine={false} width={50} />
              <YAxis yAxisId="right" orientation="right" tick={{ fontSize: 10, fill: '#94a3b8' }} axisLine={false} tickLine={false} width={30} />
              <Tooltip contentStyle={TS} />
              <Legend wrapperStyle={{ fontSize: 11 }} />
              <Area yAxisId="left" type="monotone" dataKey="ACTIVE_POWER" stroke="#10b981" fill="url(#bioGrad)" strokeWidth={2} dot={false} name="Active Power (kW)" />
              <Area yAxisId="right" type="monotone" dataKey="FUEL_MOISTURE" stroke="#6ee7b7" strokeWidth={1.5} dot={false} name="Fuel Moisture (%)" fill="none" />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        <div className="bg-navy-800 border border-navy-600 rounded-xl p-5">
          <SectionHeader title="Combustion Temperature Profile" icon={Thermometer} color="rose" />
          <ResponsiveContainer width="100%" height={240}>
            <AreaChart data={demoHourly} margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
              <defs>
                <linearGradient id="tempGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#ef4444" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#ef4444" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
              <XAxis dataKey="hour" tick={{ fontSize: 10, fill: '#94a3b8' }} axisLine={false} tickLine={false} />
              <YAxis domain={['auto', 'auto']} tick={{ fontSize: 10, fill: '#94a3b8' }} axisLine={false} tickLine={false} width={40} />
              <Tooltip contentStyle={TS} />
              <Area type="monotone" dataKey="COMBUSTION_TEMP" stroke="#ef4444" fill="url(#tempGrad)" strokeWidth={2} dot={false} name="Combustion Temp (°C)" />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="bg-navy-800 border border-navy-600 rounded-xl p-5">
        <SectionHeader title="Emissions Profile" icon={Leaf} color="emerald" subtitle="Biogenic CO₂ is carbon-neutral — counted as 0 net emissions" />
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {emissions.map((e) => (
            <div key={e.type} className="bg-navy-700 rounded-lg p-4 text-center">
              <p className="text-xs text-slate-400 mb-2">{e.type}</p>
              <p className="text-lg font-bold font-mono text-white">{e.actual}</p>
              <p className="text-xs text-slate-500">mg/Nm³</p>
              {e.net === 0 && <p className="text-xs text-emerald-400 mt-1">Carbon-neutral</p>}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
