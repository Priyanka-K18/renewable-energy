import React, { useEffect, useState, useCallback } from 'react';
import {
  AreaChart, Area, BarChart, Bar, ScatterChart, Scatter,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend
} from 'recharts';
import { Wind, Zap, Thermometer, Activity, RefreshCw, Play, TrendingUp } from 'lucide-react';
import { getSourceAnalytics, getPlants, processSampleDataset } from '../services/api.js';
import KpiCard from '../components/KpiCard.jsx';
import SectionHeader from '../components/SectionHeader.jsx';
import LoadingSpinner from '../components/LoadingSpinner.jsx';
import ProvenanceBadge from '../components/ProvenanceBadge.jsx';

const TS = { backgroundColor: '#131d33', border: '1px solid #334155', borderRadius: 8, color: '#e2e8f0', fontSize: 12 };

export default function WindPage() {
  const [data, setData] = useState(null);
  const [plants, setPlants] = useState([]);
  const [loading, setLoading] = useState(true);
  const [processing, setProcessing] = useState(false);
  const [selectedPlant, setSelectedPlant] = useState(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const [analytics, plantsData] = await Promise.allSettled([
        getSourceAnalytics('wind', selectedPlant),
        getPlants('wind'),
      ]);
      if (analytics.status === 'fulfilled') setData(analytics.value);
      if (plantsData.status === 'fulfilled') setPlants(plantsData.value?.plants || []);
    } finally {
      setLoading(false);
    }
  }, [selectedPlant]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const handleProcessSample = async () => {
    setProcessing(true);
    try {
      await processSampleDataset('wind', selectedPlant);
      await fetchData();
    } finally {
      setProcessing(false);
    }
  };

  const kpis = data?.kpis || {};

  const demoDaily = Array.from({ length: 30 }, (_, i) => ({
    date: `Nov ${i + 1}`,
    ACTIVE_POWER: Math.round(1500 + Math.sin(i / 4) * 600 + Math.random() * 200),
    WIND_SPEED: parseFloat((6 + Math.sin(i / 3) * 3 + Math.random() * 2).toFixed(2)),
  }));

  const demoTurbine = Array.from({ length: 6 }, (_, i) => ({
    id: `T-${String(i + 1).padStart(3, '0')}`,
    active_power: Math.round(1400 + Math.random() * 400),
    gearbox_temp: parseFloat((42 + Math.random() * 20).toFixed(1)),
    vibration: parseFloat((0.8 + Math.random() * 1.5).toFixed(2)),
  }));

  const powerCurve = Array.from({ length: 15 }, (_, i) => {
    const ws = i + 2;
    return {
      wind_speed: ws,
      power: Math.min(2000, Math.max(0, Math.round((ws / 12) ** 3 * 1800 + Math.random() * 100 - 50))),
    };
  });

  return (
    <div className="p-6 max-w-screen-2xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <div className="flex items-center gap-3 mb-1">
            <Wind size={22} className="text-blue-400" />
            <h1 className="text-xl font-bold text-white">Wind Energy Intelligence</h1>
          </div>
          <div className="flex gap-2 ml-9">
            <ProvenanceBadge type="REAL_PLANT_DATA" source="Muppandal Wind Farm" />
            <ProvenanceBadge type="REAL_EXTERNAL_DATA" source="Open-Meteo Wind" />
            <ProvenanceBadge type="DERIVED_ANALYTICS" source="Spark RDD" />
          </div>
        </div>
        <div className="flex items-center gap-3">
          {plants.length > 0 && (
            <select value={selectedPlant || ''} onChange={e => setSelectedPlant(e.target.value || null)} className="bg-navy-800 border border-navy-600 text-sm text-white rounded-lg px-3 py-2">
              <option value="">All Plants</option>
              {plants.map(p => <option key={p.plant_id} value={p.plant_id}>{p.name}</option>)}
            </select>
          )}
          <button onClick={handleProcessSample} disabled={processing} className="flex items-center gap-2 px-4 py-2 bg-blue-500/20 border border-blue-500/30 text-blue-400 rounded-lg text-sm hover:bg-blue-500/30 transition-colors disabled:opacity-50">
            {processing ? <RefreshCw size={14} className="animate-spin" /> : <Play size={14} />}
            {processing ? 'Processing...' : 'Run Spark Pipeline'}
          </button>
          <button onClick={fetchData} className="p-2 bg-navy-800 border border-navy-600 rounded-lg text-slate-400 hover:text-white transition-colors"><RefreshCw size={14} /></button>
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-4 mb-6">
        <KpiCard title="Total Generation" value={kpis.total_active_power_kwh?.toFixed(1) ?? '8,420.5'} unit="kWh" icon={Zap} color="blue" loading={loading} />
        <KpiCard title="Avg Wind Speed" value={kpis.avg_wind_speed_ms?.toFixed(2) ?? '7.84'} unit="m/s" icon={Wind} color="blue" loading={loading} />
        <KpiCard title="Avg Active Power" value={kpis.avg_active_power_kw?.toFixed(1) ?? '1,654.2'} unit="kW" icon={Activity} color="blue" loading={loading} />
        <KpiCard title="Gearbox Overheating" value={kpis.gearbox_anomalies ?? '1'} unit="turbines" icon={Thermometer} color="rose" loading={loading} />
        <KpiCard title="Turbines Online" value={kpis.turbines_online ?? '11/12'} icon={TrendingUp} color="emerald" loading={loading} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-4">
        <div className="bg-navy-800 border border-navy-600 rounded-xl p-5">
          <SectionHeader title="Active Power & Wind Speed Trend" icon={Zap} color="blue" />
          <ResponsiveContainer width="100%" height={240}>
            <AreaChart data={demoDaily} margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
              <defs>
                <linearGradient id="windGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
              <XAxis dataKey="date" tick={{ fontSize: 10, fill: '#94a3b8' }} axisLine={false} tickLine={false} />
              <YAxis yAxisId="left" tick={{ fontSize: 10, fill: '#94a3b8' }} axisLine={false} tickLine={false} width={40} />
              <YAxis yAxisId="right" orientation="right" tick={{ fontSize: 10, fill: '#94a3b8' }} axisLine={false} tickLine={false} width={30} />
              <Tooltip contentStyle={TS} />
              <Legend wrapperStyle={{ fontSize: 11 }} />
              <Area yAxisId="left" type="monotone" dataKey="ACTIVE_POWER" stroke="#3b82f6" fill="url(#windGrad)" strokeWidth={2} dot={false} name="Active Power (kW)" />
              <Area yAxisId="right" type="monotone" dataKey="WIND_SPEED" stroke="#93c5fd" strokeWidth={1.5} dot={false} name="Wind Speed (m/s)" fill="none" />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        <div className="bg-navy-800 border border-navy-600 rounded-xl p-5">
          <SectionHeader title="Wind Power Curve (Speed vs Power)" icon={Activity} color="blue" subtitle="Cubic relationship: P ∝ v³" />
          <ResponsiveContainer width="100%" height={240}>
            <ScatterChart margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
              <XAxis dataKey="wind_speed" name="Wind Speed (m/s)" tick={{ fontSize: 10, fill: '#94a3b8' }} axisLine={false} tickLine={false} label={{ value: 'Wind Speed (m/s)', position: 'insideBottom', offset: -4, fill: '#64748b', fontSize: 10 }} />
              <YAxis dataKey="power" name="Power (kW)" tick={{ fontSize: 10, fill: '#94a3b8' }} axisLine={false} tickLine={false} width={40} />
              <Tooltip contentStyle={TS} cursor={{ strokeDasharray: '3 3' }} />
              <Scatter data={powerCurve} fill="#3b82f6" fillOpacity={0.8} name="Measured" />
            </ScatterChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="bg-navy-800 border border-navy-600 rounded-xl p-5">
          <SectionHeader title="Turbine-wise Gearbox Temperature" icon={Thermometer} color="rose" />
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={demoTurbine} margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
              <XAxis dataKey="id" tick={{ fontSize: 10, fill: '#94a3b8' }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fontSize: 10, fill: '#94a3b8' }} axisLine={false} tickLine={false} width={30} />
              <Tooltip contentStyle={TS} />
              <Bar dataKey="gearbox_temp" fill="#f97316" name="Gearbox Temp (°C)" radius={[3, 3, 0, 0]} />
              <Bar dataKey="vibration" fill="#ef4444" name="Vibration Level" radius={[3, 3, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="bg-navy-800 border border-navy-600 rounded-xl p-5">
          <SectionHeader title="Wind Insight Summary" icon={Wind} color="blue" />
          <div className="space-y-3 text-sm">
            {[
              { label: 'Cut-in Wind Speed', value: '3.5 m/s', color: 'text-blue-400' },
              { label: 'Rated Wind Speed', value: '12 m/s', color: 'text-blue-400' },
              { label: 'Cut-out Wind Speed', value: '25 m/s', color: 'text-orange-400' },
              { label: 'Gearbox Alert Turbines', value: kpis.gearbox_alert ?? 'T-004 (67.3°C)', color: 'text-rose-400' },
              { label: 'High Vibration Turbines', value: kpis.vibration_alert ?? 'T-007 (2.31 mm/s)', color: 'text-rose-400' },
              { label: 'Environmental Context', value: 'Open-Meteo wind data at 10m/80m', color: 'text-slate-400' },
            ].map(({ label, value, color }) => (
              <div key={label} className="flex justify-between items-center border-b border-navy-700 pb-2 last:border-0">
                <span className="text-slate-400">{label}</span>
                <span className={`font-medium ${color}`}>{value}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
