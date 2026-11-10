import React, { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { Server, RefreshCw, CheckCircle, XCircle, Clock, Play, Info } from 'lucide-react';
import { getDataSources, getSourceMetadata, syncNasaPower, syncOwid, syncOpenMeteo } from '../services/api.js';
import SectionHeader from '../components/SectionHeader.jsx';
import LoadingSpinner from '../components/LoadingSpinner.jsx';
import ProvenanceBadge from '../components/ProvenanceBadge.jsx';

export default function SourcesPage() {
  const [sources, setSources] = useState([]);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(null);
  const [notification, setNotification] = useState(null);

  // NASA POWER form state
  const [nasaForm, setNasaForm] = useState({ latitude: '28.0', longitude: '74.0', start: '2023-01-01', end: '2023-01-31' });
  // Open-Meteo form state
  const [meteoForm, setMeteoForm] = useState({ latitude: '28.0', longitude: '74.0' });

  const fetchData = async () => {
    setLoading(true);
    try {
      const res = await getDataSources();
      setSources(res?.sources || []);
    } finally { setLoading(false); }
  };

  useEffect(() => { fetchData(); }, []);

  const notify = (msg, type = 'success') => {
    setNotification({ msg, type });
    setTimeout(() => setNotification(null), 5000);
  };

  const handleSync = async (sourceKey, payload = {}) => {
    setSyncing(sourceKey);
    try {
      if (sourceKey === 'nasa_power') await syncNasaPower(payload);
      else if (sourceKey === 'owid') await syncOwid(payload);
      else if (sourceKey === 'open_meteo') await syncOpenMeteo(payload);
      notify(`${sourceKey.replace('_', ' ')} sync triggered successfully!`);
      await fetchData();
    } catch (e) {
      notify(`Sync failed: ${e.response?.data?.detail || e.message}`, 'error');
    } finally { setSyncing(null); }
  };

  const sourceInfo = {
    nasa_power: {
      name: 'NASA POWER',
      desc: 'Historical environmental & solar resource data from NASA Langley Research Center.',
      url: 'https://power.larc.nasa.gov',
      license: 'CC BY 4.0',
      provenance: 'REAL_EXTERNAL_DATA',
    },
    owid: {
      name: 'Our World in Data Energy',
      desc: 'Global renewable energy statistics across countries and years.',
      url: 'https://ourworldindata.org/energy',
      license: 'CC BY 4.0',
      provenance: 'REAL_EXTERNAL_DATA',
    },
    open_meteo: {
      name: 'Open-Meteo',
      desc: 'Current weather forecasts and historical reanalysis at plant locations.',
      url: 'https://open-meteo.com',
      license: 'CC BY 4.0',
      provenance: 'REAL_EXTERNAL_DATA',
    },
  };

  return (
    <div className="p-6 max-w-screen-2xl mx-auto">
      <div className="flex items-center gap-3 mb-6">
        <Server size={22} className="text-pink-400" />
        <h1 className="text-xl font-bold text-white">External Data Sources</h1>
      </div>

      {notification && (
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className={`mb-5 flex items-center gap-3 px-4 py-3 rounded-xl border text-sm ${
            notification.type === 'error'
              ? 'bg-rose-500/10 border-rose-500/30 text-rose-400'
              : 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400'
          }`}
        >
          {notification.type === 'error' ? <XCircle size={16} /> : <CheckCircle size={16} />}
          {notification.msg}
        </motion.div>
      )}

      {/* NASA POWER */}
      <div className="bg-navy-800 border border-navy-600 rounded-xl p-5 mb-4">
        <SectionHeader
          title="NASA POWER — Historical Environmental Data"
          icon={Server}
          color="blue"
          subtitle="power.larc.nasa.gov · CC BY 4.0"
        />
        <div className="mb-4">
          <ProvenanceBadge type="REAL_EXTERNAL_DATA" source="NASA POWER API" />
          <p className="text-xs text-slate-400 mt-2">
            Retrieves historical solar irradiance, temperature, wind speed and precipitation data.
            Used for environmental context — not actual plant generation output.
          </p>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
          {[
            { label: 'Latitude', key: 'latitude', placeholder: '28.0' },
            { label: 'Longitude', key: 'longitude', placeholder: '74.0' },
            { label: 'Start Date', key: 'start', type: 'date' },
            { label: 'End Date', key: 'end', type: 'date' },
          ].map(({ label, key, placeholder, type = 'text' }) => (
            <div key={key}>
              <label className="block text-xs text-slate-400 mb-1">{label}</label>
              <input
                type={type}
                value={nasaForm[key]}
                onChange={e => setNasaForm(f => ({ ...f, [key]: e.target.value }))}
                placeholder={placeholder}
                className="w-full bg-navy-700 border border-navy-600 rounded-lg px-3 py-2 text-sm text-white"
              />
            </div>
          ))}
        </div>
        <button
          onClick={() => handleSync('nasa_power', {
            latitude: parseFloat(nasaForm.latitude),
            longitude: parseFloat(nasaForm.longitude),
            start_date: nasaForm.start,
            end_date: nasaForm.end,
          })}
          disabled={syncing === 'nasa_power'}
          className="flex items-center gap-2 px-5 py-2.5 bg-blue-500/20 border border-blue-500/30 text-blue-400 rounded-lg text-sm hover:bg-blue-500/30 transition-colors disabled:opacity-50"
        >
          {syncing === 'nasa_power' ? <RefreshCw size={14} className="animate-spin" /> : <Play size={14} />}
          {syncing === 'nasa_power' ? 'Syncing...' : 'Fetch NASA POWER Data'}
        </button>
      </div>

      {/* OWID */}
      <div className="bg-navy-800 border border-navy-600 rounded-xl p-5 mb-4">
        <SectionHeader
          title="Our World in Data — Global Energy Statistics"
          icon={Server}
          color="indigo"
          subtitle="ourworldindata.org/energy · CC BY 4.0"
        />
        <div className="mb-4">
          <ProvenanceBadge type="REAL_EXTERNAL_DATA" source="OWID Energy Dataset" />
          <p className="text-xs text-slate-400 mt-2">
            Downloads the latest OWID energy CSV dataset (~9MB) and processes it through Spark RDD.
            Contains country-level generation statistics across all renewable sources.
          </p>
        </div>
        <button
          onClick={() => handleSync('owid', {})}
          disabled={syncing === 'owid'}
          className="flex items-center gap-2 px-5 py-2.5 bg-indigo-500/20 border border-indigo-500/30 text-indigo-400 rounded-lg text-sm hover:bg-indigo-500/30 transition-colors disabled:opacity-50"
        >
          {syncing === 'owid' ? <RefreshCw size={14} className="animate-spin" /> : <Play size={14} />}
          {syncing === 'owid' ? 'Syncing...' : 'Sync OWID Dataset'}
        </button>
      </div>

      {/* Open-Meteo */}
      <div className="bg-navy-800 border border-navy-600 rounded-xl p-5 mb-4">
        <SectionHeader
          title="Open-Meteo — Current Weather & Forecast"
          icon={Server}
          color="sky"
          subtitle="api.open-meteo.com · Free / CC BY 4.0"
        />
        <div className="mb-4">
          <ProvenanceBadge type="REAL_EXTERNAL_DATA" source="Open-Meteo API" />
          <p className="text-xs text-slate-400 mt-2">
            Retrieves hourly weather forecasts and historical reanalysis for plant coordinates.
            Covers temperature, wind, precipitation, solar radiation and humidity.
          </p>
        </div>
        <div className="grid grid-cols-2 gap-3 mb-4 max-w-sm">
          {[
            { label: 'Latitude', key: 'latitude' },
            { label: 'Longitude', key: 'longitude' },
          ].map(({ label, key }) => (
            <div key={key}>
              <label className="block text-xs text-slate-400 mb-1">{label}</label>
              <input
                type="text"
                value={meteoForm[key]}
                onChange={e => setMeteoForm(f => ({ ...f, [key]: e.target.value }))}
                className="w-full bg-navy-700 border border-navy-600 rounded-lg px-3 py-2 text-sm text-white"
              />
            </div>
          ))}
        </div>
        <button
          onClick={() => handleSync('open_meteo', {
            latitude: parseFloat(meteoForm.latitude),
            longitude: parseFloat(meteoForm.longitude),
          })}
          disabled={syncing === 'open_meteo'}
          className="flex items-center gap-2 px-5 py-2.5 bg-sky-500/20 border border-sky-500/30 text-sky-400 rounded-lg text-sm hover:bg-sky-500/30 transition-colors disabled:opacity-50"
        >
          {syncing === 'open_meteo' ? <RefreshCw size={14} className="animate-spin" /> : <Play size={14} />}
          {syncing === 'open_meteo' ? 'Syncing...' : 'Sync Open-Meteo Weather'}
        </button>
      </div>

      {/* Source Status Table */}
      {sources.length > 0 && (
        <div className="bg-navy-800 border border-navy-600 rounded-xl overflow-hidden">
          <div className="px-5 py-4 border-b border-navy-700 flex justify-between items-center">
            <h3 className="text-sm font-semibold text-white">Sync Status</h3>
            <button onClick={fetchData} className="p-1.5 text-slate-400 hover:text-white"><RefreshCw size={13} /></button>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-navy-700 text-left">
                  <th className="px-4 py-3 text-xs text-slate-400 uppercase">Source</th>
                  <th className="px-4 py-3 text-xs text-slate-400 uppercase">Status</th>
                  <th className="px-4 py-3 text-xs text-slate-400 uppercase">Last Sync</th>
                  <th className="px-4 py-3 text-xs text-slate-400 uppercase">Records</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-navy-700">
                {sources.map(s => (
                  <tr key={s.id} className="hover:bg-navy-700/40">
                    <td className="px-4 py-3 text-white font-medium">{s.name}</td>
                    <td className="px-4 py-3">
                      <span className={`text-xs flex items-center gap-1 ${s.is_active ? 'text-emerald-400' : 'text-slate-500'}`}>
                        {s.is_active ? <CheckCircle size={12} /> : <Clock size={12} />}
                        {s.is_active ? 'Active' : 'Inactive'}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-slate-400 text-xs">{s.last_sync_at ? new Date(s.last_sync_at).toLocaleString() : 'Never'}</td>
                    <td className="px-4 py-3 text-slate-300 font-mono">{s.records_synced?.toLocaleString() || '—'}</td>
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
