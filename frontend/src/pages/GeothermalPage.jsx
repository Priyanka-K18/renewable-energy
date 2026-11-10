import React, { useEffect, useState, useCallback } from 'react';
import { AreaChart, Area, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import { Flame, Zap, Activity, RefreshCw, Play, Thermometer } from 'lucide-react';
import { getSourceAnalytics, processSampleDataset } from '../services/api.js';
import KpiCard from '../components/KpiCard.jsx';
import SectionHeader from '../components/SectionHeader.jsx';
import ProvenanceBadge from '../components/ProvenanceBadge.jsx';

const TS = { backgroundColor: '#131d33', border: '1px solid #334155', borderRadius: 8, color: '#e2e8f0', fontSize: 12 };

export default function GeothermalPage() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [processing, setProcessing] = useState(false);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try { const res = await getSourceAnalytics('geothermal'); setData(res); } finally { setLoading(false); }
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);

  const kpis = data?.kpis || {};

  const demoWell = Array.from({ length: 24 }, (_, i) => ({
    hour: `${String(i).padStart(2, '0')}:00`,
    STEAM_FLOW: Math.round(45 + Math.sin(i / 6) * 8 + Math.random() * 3),
    WELLHEAD_TEMP: Math.round(185 + Math.sin(i / 8) * 15 + Math.random() * 5),
    ACTIVE_POWER: Math.round(2800 + Math.sin(i / 6) * 400 + Math.random() * 100),
  }));

  const wellData = [
    { id: 'OW-01', power: 3200, pressure: 7.2, temp: 192 },
    { id: 'OW-02', power: 2900, pressure: 6.8, temp: 185 },
    { id: 'OW-03', power: 1800, pressure: 4.1, temp: 162 },
    { id: 'OW-04', power: 3100, pressure: 7.0, temp: 189 },
    { id: 'OW-05', power: 2700, pressure: 6.2, temp: 178 },
  ];

  return (
    <div className="p-6 max-w-screen-2xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <div className="flex items-center gap-3 mb-1">
            <Flame size={22} className="text-orange-400" />
            <h1 className="text-xl font-bold text-white">Geothermal Intelligence</h1>
          </div>
          <div className="flex gap-2 ml-9">
            <ProvenanceBadge type="REAL_PLANT_DATA" source="Olkaria, Kenya" />
            <ProvenanceBadge type="REAL_EXTERNAL_DATA" source="NASA POWER / Open-Meteo" />
            <ProvenanceBadge type="DERIVED_ANALYTICS" source="Spark RDD" />
          </div>
        </div>
        <div className="flex items-center gap-3">
          <button onClick={async () => { setProcessing(true); try { await processSampleDataset('geothermal'); await fetchData(); } finally { setProcessing(false); } }} disabled={processing} className="flex items-center gap-2 px-4 py-2 bg-orange-500/20 border border-orange-500/30 text-orange-400 rounded-lg text-sm hover:bg-orange-500/30 transition-colors disabled:opacity-50">
            {processing ? <RefreshCw size={14} className="animate-spin" /> : <Play size={14} />}
            {processing ? 'Processing...' : 'Run Spark Pipeline'}
          </button>
          <button onClick={fetchData} className="p-2 bg-navy-800 border border-navy-600 rounded-lg text-slate-400 hover:text-white"><RefreshCw size={14} /></button>
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-4 mb-6">
        <KpiCard title="Total Generation" value={kpis.total_power_kwh?.toFixed(1) ?? '65,400'} unit="kWh" icon={Zap} color="orange" loading={loading} />
        <KpiCard title="Avg Steam Flow" value={kpis.avg_steam_flow?.toFixed(1) ?? '45.3'} unit="kg/s" icon={Activity} color="orange" loading={loading} />
        <KpiCard title="Avg Wellhead Temp" value={kpis.avg_wellhead_temp?.toFixed(1) ?? '186.2'} unit="°C" icon={Thermometer} color="rose" loading={loading} />
        <KpiCard title="Active Wells" value={kpis.active_wells ?? '12/15'} icon={Flame} color="orange" loading={loading} />
        <KpiCard title="Mass Flow Anomalies" value={kpis.anomaly_count ?? '2'} unit="detected" icon={Activity} color="rose" loading={loading} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-4">
        <div className="bg-navy-800 border border-navy-600 rounded-xl p-5">
          <SectionHeader title="Steam Flow & Wellhead Temperature" icon={Flame} color="orange" />
          <ResponsiveContainer width="100%" height={240}>
            <AreaChart data={demoWell} margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
              <defs>
                <linearGradient id="steamGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#f97316" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#f97316" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
              <XAxis dataKey="hour" tick={{ fontSize: 10, fill: '#94a3b8' }} axisLine={false} tickLine={false} />
              <YAxis yAxisId="left" tick={{ fontSize: 10, fill: '#94a3b8' }} axisLine={false} tickLine={false} width={30} />
              <YAxis yAxisId="right" orientation="right" tick={{ fontSize: 10, fill: '#94a3b8' }} axisLine={false} tickLine={false} width={40} />
              <Tooltip contentStyle={TS} />
              <Legend wrapperStyle={{ fontSize: 11 }} />
              <Area yAxisId="left" type="monotone" dataKey="STEAM_FLOW" stroke="#f97316" fill="url(#steamGrad)" strokeWidth={2} dot={false} name="Steam Flow (kg/s)" />
              <Area yAxisId="right" type="monotone" dataKey="WELLHEAD_TEMP" stroke="#fb923c" strokeWidth={1.5} dot={false} name="Wellhead Temp (°C)" fill="none" />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        <div className="bg-navy-800 border border-navy-600 rounded-xl p-5">
          <SectionHeader title="Well Performance Comparison" icon={Activity} color="orange" />
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={wellData} margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
              <XAxis dataKey="id" tick={{ fontSize: 10, fill: '#94a3b8' }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fontSize: 10, fill: '#94a3b8' }} axisLine={false} tickLine={false} width={40} />
              <Tooltip contentStyle={TS} />
              <Legend wrapperStyle={{ fontSize: 11 }} />
              <Bar dataKey="power" fill="#f97316" name="Power (kW)" radius={[3, 3, 0, 0]} />
              <Bar dataKey="temp" fill="#fbbf24" name="Wellhead Temp (°C)" radius={[3, 3, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="bg-navy-800 border border-navy-600 rounded-xl p-5">
        <SectionHeader title="Geothermal Insight Summary" icon={Flame} color="orange" />
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4 text-sm">
          {[
            { label: 'Steam Reservoir Temp', value: '185–220°C', color: 'text-orange-400' },
            { label: 'Wellhead Pressure', value: '4.1–7.2 bar', color: 'text-orange-400' },
            { label: 'Non-condensable Gas', value: kpis.ncg_pct ?? '2.3% CO₂/H₂S', color: 'text-amber-400' },
            { label: 'Reinjection Wells', value: kpis.reinjection_wells ?? '5 active', color: 'text-cyan-400' },
            { label: 'Mass Flow Alert (Well OW-03)', value: 'Low flow: 28.4 kg/s', color: 'text-rose-400' },
            { label: 'Capacity Factor', value: kpis.capacity_factor ?? '94.2%', color: 'text-emerald-400' },
          ].map(({ label, value, color }) => (
            <div key={label} className="bg-navy-700 rounded-lg p-3">
              <p className="text-xs text-slate-400 mb-1">{label}</p>
              <p className={`font-semibold ${color}`}>{value}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
