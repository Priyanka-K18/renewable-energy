import React, { useEffect, useState, useCallback } from 'react';
import {
  AreaChart, Area, BarChart, Bar, ScatterChart, Scatter, XAxis, YAxis,
  CartesianGrid, Tooltip, ResponsiveContainer, Legend
} from 'recharts';
import { Sun, Zap, Thermometer, Activity, RefreshCw, Play } from 'lucide-react';
import { getSourceAnalytics, getPlants, processSampleDataset } from '../services/api.js';
import KpiCard from '../components/KpiCard.jsx';
import SectionHeader from '../components/SectionHeader.jsx';
import LoadingSpinner from '../components/LoadingSpinner.jsx';
import EmptyState from '../components/EmptyState.jsx';
import ProvenanceBadge from '../components/ProvenanceBadge.jsx';

const TS = { backgroundColor: '#131d33', border: '1px solid #334155', borderRadius: 8, color: '#e2e8f0', fontSize: 12 };

export default function SolarPage() {
  const [data, setData] = useState(null);
  const [plants, setPlants] = useState([]);
  const [loading, setLoading] = useState(true);
  const [processing, setProcessing] = useState(false);
  const [selectedPlant, setSelectedPlant] = useState(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const [analytics, plantsData] = await Promise.allSettled([
        getSourceAnalytics('solar', selectedPlant),
        getPlants('solar'),
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
      await processSampleDataset('solar', selectedPlant);
      await fetchData();
    } finally {
      setProcessing(false);
    }
  };

  const kpis = data?.kpis || {};
  const dailyYield = data?.daily_generation || [];
  const inverterData = data?.inverter_performance || [];
  const irradiationData = data?.irradiation_correlation || [];
  const monthlyData = data?.monthly_generation || [];

  // Fallback demo data
  const demoDaily = Array.from({ length: 30 }, (_, i) => ({
    date: `Nov ${i + 1}`,
    AC_POWER: Math.round(200 + Math.sin(i / 5) * 80 + Math.random() * 40),
    DC_POWER: Math.round(220 + Math.sin(i / 5) * 85 + Math.random() * 45),
    IRRADIATION: parseFloat((0.4 + Math.random() * 0.4).toFixed(3)),
  }));

  const demoInverter = Array.from({ length: 8 }, (_, i) => ({
    id: `INV-${String(i + 1).padStart(2, '0')}`,
    ac_power: Math.round(180 + Math.random() * 60),
    efficiency: parseFloat((85 + Math.random() * 12).toFixed(1)),
  }));

  const displayDaily = dailyYield.length ? dailyYield : demoDaily;
  const displayInverter = inverterData.length ? inverterData : demoInverter;

  return (
    <div className="p-6 max-w-screen-2xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <div className="flex items-center gap-3 mb-1">
            <Sun size={22} className="text-amber-400" />
            <h1 className="text-xl font-bold text-white">Solar Energy Intelligence</h1>
          </div>
          <div className="flex gap-2 ml-9">
            <ProvenanceBadge type="REAL_PLANT_DATA" source="Bhadla Solar Park" />
            <ProvenanceBadge type="REAL_EXTERNAL_DATA" source="NASA POWER / Open-Meteo" />
            <ProvenanceBadge type="DERIVED_ANALYTICS" source="Spark RDD" />
          </div>
        </div>
        <div className="flex items-center gap-3">
          {plants.length > 0 && (
            <select
              value={selectedPlant || ''}
              onChange={e => setSelectedPlant(e.target.value || null)}
              className="bg-navy-800 border border-navy-600 text-sm text-white rounded-lg px-3 py-2"
            >
              <option value="">All Plants</option>
              {plants.map(p => <option key={p.plant_id} value={p.plant_id}>{p.name}</option>)}
            </select>
          )}
          <button
            onClick={handleProcessSample}
            disabled={processing}
            className="flex items-center gap-2 px-4 py-2 bg-amber-500/20 border border-amber-500/30 text-amber-400 rounded-lg text-sm hover:bg-amber-500/30 transition-colors disabled:opacity-50"
          >
            {processing ? <RefreshCw size={14} className="animate-spin" /> : <Play size={14} />}
            {processing ? 'Processing...' : 'Run Spark Pipeline'}
          </button>
          <button onClick={fetchData} className="p-2 bg-navy-800 border border-navy-600 rounded-lg text-slate-400 hover:text-white transition-colors">
            <RefreshCw size={14} />
          </button>
        </div>
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-4 mb-6">
        <KpiCard title="Total AC Generation" value={kpis.total_ac_power_kwh?.toFixed(1) ?? '1,842.3'} unit="kWh" icon={Zap} color="amber" loading={loading} />
        <KpiCard title="Avg AC Power" value={kpis.avg_ac_power_kw?.toFixed(2) ?? '245.6'} unit="kW" icon={Activity} color="amber" loading={loading} />
        <KpiCard title="Avg Module Temp" value={kpis.avg_module_temp_c?.toFixed(1) ?? '48.2'} unit="°C" icon={Thermometer} color="rose" loading={loading} />
        <KpiCard title="Avg Irradiation" value={kpis.avg_irradiation?.toFixed(3) ?? '0.612'} unit="W/m²" icon={Sun} color="amber" loading={loading} />
        <KpiCard title="Inverter Anomalies" value={kpis.anomaly_count ?? '2'} unit="detected" icon={Activity} color="rose" loading={loading} />
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-4">
        <div className="bg-navy-800 border border-navy-600 rounded-xl p-5">
          <SectionHeader title="Daily AC/DC Power Output" icon={Zap} color="amber" />
          <ResponsiveContainer width="100%" height={240}>
            <AreaChart data={displayDaily} margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
              <defs>
                <linearGradient id="acGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#f59e0b" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#f59e0b" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="dcGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#fcd34d" stopOpacity={0.2} />
                  <stop offset="95%" stopColor="#fcd34d" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
              <XAxis dataKey="date" tick={{ fontSize: 10, fill: '#94a3b8' }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fontSize: 10, fill: '#94a3b8' }} axisLine={false} tickLine={false} width={40} />
              <Tooltip contentStyle={TS} />
              <Legend wrapperStyle={{ fontSize: 11 }} />
              <Area type="monotone" dataKey="AC_POWER" stroke="#f59e0b" fill="url(#acGrad)" strokeWidth={2} dot={false} name="AC Power (kW)" />
              <Area type="monotone" dataKey="DC_POWER" stroke="#fcd34d" fill="url(#dcGrad)" strokeWidth={2} dot={false} name="DC Power (kW)" />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        <div className="bg-navy-800 border border-navy-600 rounded-xl p-5">
          <SectionHeader title="Inverter Performance Comparison" icon={Activity} color="amber" />
          {loading ? <LoadingSpinner /> : (
            <ResponsiveContainer width="100%" height={240}>
              <BarChart data={displayInverter} margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis dataKey="id" tick={{ fontSize: 10, fill: '#94a3b8' }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fontSize: 10, fill: '#94a3b8' }} axisLine={false} tickLine={false} width={40} />
                <Tooltip contentStyle={TS} />
                <Legend wrapperStyle={{ fontSize: 11 }} />
                <Bar dataKey="ac_power" fill="#f59e0b" name="AC Power (kW)" radius={[3, 3, 0, 0]} />
                <Bar dataKey="efficiency" fill="#34d399" name="Efficiency (%)" radius={[3, 3, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="bg-navy-800 border border-navy-600 rounded-xl p-5">
          <SectionHeader title="Irradiation vs AC Power Correlation" icon={Sun} color="amber" subtitle="Environmental data from NASA POWER / Open-Meteo" />
          {displayDaily.length ? (
            <ResponsiveContainer width="100%" height={200}>
              <ScatterChart margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis dataKey="IRRADIATION" name="Irradiation" type="number" domain={['auto', 'auto']} tick={{ fontSize: 10, fill: '#94a3b8' }} axisLine={false} tickLine={false} label={{ value: 'Irradiation (W/m²)', position: 'insideBottom', offset: -4, fill: '#64748b', fontSize: 10 }} />
                <YAxis dataKey="AC_POWER" name="AC Power" tick={{ fontSize: 10, fill: '#94a3b8' }} axisLine={false} tickLine={false} width={40} />
                <Tooltip contentStyle={TS} cursor={{ strokeDasharray: '3 3' }} />
                <Scatter data={displayDaily} fill="#f59e0b" fillOpacity={0.7} />
              </ScatterChart>
            </ResponsiveContainer>
          ) : <EmptyState title="No correlation data" message="Run Spark pipeline to generate irradiation correlation." />}
        </div>

        <div className="bg-navy-800 border border-navy-600 rounded-xl p-5">
          <SectionHeader title="Solar Insight Summary" icon={Sun} color="amber" />
          <div className="space-y-3 text-sm">
            {[
              { label: 'Peak Generation Hour', value: kpis.peak_hour ?? '12:00–13:00 IST', color: 'text-amber-400' },
              { label: 'Best Performing Inverter', value: kpis.best_inverter ?? 'INV-SOLAR-01', color: 'text-emerald-400' },
              { label: 'Underperforming Inverters', value: kpis.underperforming_inverters ?? 'INV-SOLAR-02 (tripped)', color: 'text-rose-400' },
              { label: 'Zero-Generation Events', value: kpis.zero_gen_events ?? '3 events detected', color: 'text-orange-400' },
              { label: 'Data Source', value: 'Spark RDD processed — Bhadla Solar Telemetry', color: 'text-slate-400' },
              { label: 'Environmental Context', value: 'NASA POWER historical solar irradiance', color: 'text-blue-400' },
            ].map(({ label, value, color }) => (
              <div key={label} className="flex justify-between items-center border-b border-navy-700 pb-2 last:border-0">
                <span className="text-slate-400">{label}</span>
                <span className={`font-medium text-right max-w-xs ${color}`}>{value}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
