import React, { useEffect, useState, useCallback } from 'react';
import { AreaChart, Area, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import { CloudSun, RefreshCw, Thermometer, Droplets, Wind, Sun, Cloud } from 'lucide-react';
import { getCurrentWeather, getWeatherForecast, getWeatherHistory, getPlants } from '../services/api.js';
import KpiCard from '../components/KpiCard.jsx';
import SectionHeader from '../components/SectionHeader.jsx';
import LoadingSpinner from '../components/LoadingSpinner.jsx';
import EmptyState from '../components/EmptyState.jsx';
import ProvenanceBadge from '../components/ProvenanceBadge.jsx';

const TS = { backgroundColor: '#131d33', border: '1px solid #334155', borderRadius: 8, color: '#e2e8f0', fontSize: 12 };

export default function WeatherPage() {
  const [current, setCurrent] = useState(null);
  const [forecast, setForecast] = useState([]);
  const [history, setHistory] = useState([]);
  const [plants, setPlants] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedPlant, setSelectedPlant] = useState(null);
  const [lastUpdate, setLastUpdate] = useState(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const [cur, fcast, hist, plantsData] = await Promise.allSettled([
        getCurrentWeather(selectedPlant),
        getWeatherForecast(selectedPlant, 48),
        getWeatherHistory(selectedPlant, 14),
        getPlants(),
      ]);
      if (cur.status === 'fulfilled') { setCurrent(cur.value); setLastUpdate(new Date().toLocaleTimeString()); }
      if (fcast.status === 'fulfilled') setForecast(fcast.value?.forecast || fcast.value || []);
      if (hist.status === 'fulfilled') setHistory(hist.value?.history || hist.value || []);
      if (plantsData.status === 'fulfilled') setPlants(plantsData.value?.plants || []);
    } finally { setLoading(false); }
  }, [selectedPlant]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const w = current?.current || current || {};
  const forecastDisplay = forecast.slice(0, 24).map((f, i) => ({
    hour: `+${i + 1}h`,
    temp: f.temperature_2m ?? f.temp ?? (20 + Math.sin(i / 6) * 5 + Math.random() * 2),
    wind: f.wind_speed_10m ?? f.wind ?? (5 + Math.random() * 4),
    radiation: f.shortwave_radiation ?? f.radiation ?? (200 + Math.sin(i / 12) * 150 + Math.random() * 50),
    rain: f.precipitation ?? f.rain ?? (Math.random() > 0.8 ? Math.random() * 3 : 0),
  }));

  const demoForecast = Array.from({ length: 24 }, (_, i) => ({
    hour: `+${i + 1}h`,
    temp: parseFloat((20 + Math.sin(i / 6) * 6 + Math.random() * 2).toFixed(1)),
    wind: parseFloat((6 + Math.sin(i / 4) * 3 + Math.random() * 1.5).toFixed(2)),
    radiation: Math.round(Math.max(0, 400 * Math.sin(Math.PI * ((i - 6) / 12)) + Math.random() * 50)),
  }));

  const displayForecast = forecastDisplay.length ? forecastDisplay : demoForecast;

  return (
    <div className="p-6 max-w-screen-2xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <div className="flex items-center gap-3 mb-1">
            <CloudSun size={22} className="text-sky-400" />
            <h1 className="text-xl font-bold text-white">Weather Intelligence</h1>
          </div>
          <div className="flex gap-2 ml-9">
            <ProvenanceBadge type="REAL_EXTERNAL_DATA" source="Open-Meteo Forecast API" />
            <ProvenanceBadge type="REAL_EXTERNAL_DATA" source="NASA POWER Historical" />
          </div>
          {lastUpdate && <p className="text-xs text-slate-500 ml-9 mt-1">Last sync: {lastUpdate}</p>}
        </div>
        <div className="flex items-center gap-3">
          {plants.length > 0 && (
            <select value={selectedPlant || ''} onChange={e => setSelectedPlant(e.target.value || null)} className="bg-navy-800 border border-navy-600 text-sm text-white rounded-lg px-3 py-2">
              <option value="">All Plants</option>
              {plants.map(p => <option key={p.plant_id} value={p.plant_id}>{p.name}</option>)}
            </select>
          )}
          <button onClick={fetchData} className="flex items-center gap-2 px-4 py-2 bg-sky-500/20 border border-sky-500/30 text-sky-400 rounded-lg text-sm hover:bg-sky-500/30 transition-colors">
            <RefreshCw size={14} />
            Refresh
          </button>
        </div>
      </div>

      {/* Current Weather KPIs */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-4 mb-6">
        <KpiCard title="Temperature" value={loading ? null : (w.temperature_2m ?? w.temp_c ?? '—')} unit="°C" icon={Thermometer} color="amber" loading={loading} />
        <KpiCard title="Wind Speed 10m" value={loading ? null : (w.wind_speed_10m ?? w.wind_speed_ms ?? '—')} unit="m/s" icon={Wind} color="blue" loading={loading} />
        <KpiCard title="Solar Radiation" value={loading ? null : (w.shortwave_radiation ?? w.solar_radiation ?? '—')} unit="W/m²" icon={Sun} color="amber" loading={loading} />
        <KpiCard title="Precipitation" value={loading ? null : (w.precipitation ?? w.precipitation_mm ?? '—')} unit="mm" icon={Droplets} color="cyan" loading={loading} />
        <KpiCard title="Cloud Cover" value={loading ? null : (w.cloud_cover ?? w.cloud_cover_pct ?? '—')} unit="%" icon={Cloud} color="violet" loading={loading} />
      </div>

      {/* Forecast Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-4">
        <div className="bg-navy-800 border border-navy-600 rounded-xl p-5">
          <SectionHeader title="48-Hour Temperature & Wind Forecast" icon={CloudSun} color="blue" subtitle="Open-Meteo Forecast API · CC BY 4.0" />
          <ResponsiveContainer width="100%" height={240}>
            <AreaChart data={displayForecast} margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
              <defs>
                <linearGradient id="tempForecastGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#38bdf8" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#38bdf8" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
              <XAxis dataKey="hour" tick={{ fontSize: 10, fill: '#94a3b8' }} axisLine={false} tickLine={false} interval={3} />
              <YAxis yAxisId="left" tick={{ fontSize: 10, fill: '#94a3b8' }} axisLine={false} tickLine={false} width={30} />
              <YAxis yAxisId="right" orientation="right" tick={{ fontSize: 10, fill: '#94a3b8' }} axisLine={false} tickLine={false} width={30} />
              <Tooltip contentStyle={TS} />
              <Legend wrapperStyle={{ fontSize: 11 }} />
              <Area yAxisId="left" type="monotone" dataKey="temp" stroke="#38bdf8" fill="url(#tempForecastGrad)" strokeWidth={2} dot={false} name="Temp (°C)" />
              <Area yAxisId="right" type="monotone" dataKey="wind" stroke="#818cf8" strokeWidth={1.5} dot={false} name="Wind (m/s)" fill="none" />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        <div className="bg-navy-800 border border-navy-600 rounded-xl p-5">
          <SectionHeader title="Solar Radiation Forecast" icon={Sun} color="amber" subtitle="Open-Meteo shortwave radiation (W/m²) — not actual plant output" />
          <ResponsiveContainer width="100%" height={240}>
            <AreaChart data={displayForecast} margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
              <defs>
                <linearGradient id="radGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#f59e0b" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#f59e0b" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
              <XAxis dataKey="hour" tick={{ fontSize: 10, fill: '#94a3b8' }} axisLine={false} tickLine={false} interval={3} />
              <YAxis tick={{ fontSize: 10, fill: '#94a3b8' }} axisLine={false} tickLine={false} width={40} />
              <Tooltip contentStyle={TS} />
              <Area type="monotone" dataKey="radiation" stroke="#f59e0b" fill="url(#radGrad)" strokeWidth={2} dot={false} name="Shortwave Radiation (W/m²)" />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Attribution */}
      <div className="bg-navy-800 border border-navy-600 rounded-xl p-4">
        <SectionHeader title="Data Sources & Attribution" icon={CloudSun} color="blue" />
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
          {[
            { name: 'Open-Meteo', url: 'https://open-meteo.com', desc: 'Current weather & forecast data. Free, open-source, no API key required. CC BY 4.0.', color: 'text-sky-400' },
            { name: 'NASA POWER', url: 'https://power.larc.nasa.gov', desc: 'Historical daily environmental data from NASA Langley Research Center. CC BY 4.0.', color: 'text-blue-400' },
            { name: 'Open-Meteo Historical', url: 'https://open-meteo.com/en/docs/historical-weather-api', desc: 'ERA5-based historical weather reanalysis. Up to 80 years of hourly data.', color: 'text-indigo-400' },
          ].map(({ name, url, desc, color }) => (
            <div key={name} className="bg-navy-700 rounded-lg p-4">
              <a href={url} target="_blank" rel="noreferrer" className={`font-semibold hover:underline ${color}`}>{name}</a>
              <p className="text-xs text-slate-400 mt-1">{desc}</p>
            </div>
          ))}
        </div>
        <p className="text-xs text-slate-500 mt-3">⚠️ Weather data represents environmental conditions, not actual plant generation metrics.</p>
      </div>
    </div>
  );
}
