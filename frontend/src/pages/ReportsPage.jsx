import React, { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { FileText, Download, RefreshCw, CheckCircle, XCircle } from 'lucide-react';
import { getReportTypes, generateReport } from '../services/api.js';
import SectionHeader from '../components/SectionHeader.jsx';
import LoadingSpinner from '../components/LoadingSpinner.jsx';

const REPORT_TYPES = [
  { key: 'overview', label: 'Platform Overview', desc: 'KPIs, generation totals, anomaly summary across all sources', color: 'text-emerald-400 border-emerald-500/30 bg-emerald-500/10' },
  { key: 'solar_analytics', label: 'Solar Analytics', desc: 'Inverter performance, irradiation, daily yield analysis', color: 'text-amber-400 border-amber-500/30 bg-amber-500/10' },
  { key: 'wind_analytics', label: 'Wind Analytics', desc: 'Turbine performance, power curve, gearbox health', color: 'text-blue-400 border-blue-500/30 bg-blue-500/10' },
  { key: 'hydro_analytics', label: 'Hydro Analytics', desc: 'Flow rate, head, turbine efficiency analysis', color: 'text-cyan-400 border-cyan-500/30 bg-cyan-500/10' },
  { key: 'geothermal_analytics', label: 'Geothermal Analytics', desc: 'Steam flow, well performance, mass flow analysis', color: 'text-orange-400 border-orange-500/30 bg-orange-500/10' },
  { key: 'biomass_analytics', label: 'Biomass Analytics', desc: 'Fuel moisture, combustion efficiency, emissions', color: 'text-lime-400 border-lime-500/30 bg-lime-500/10' },
  { key: 'anomalies', label: 'Anomaly Report', desc: 'All detected anomalies with severity and resolution status', color: 'text-rose-400 border-rose-500/30 bg-rose-500/10' },
  { key: 'global_energy', label: 'Global Energy Statistics', desc: 'OWID country-level renewable energy comparisons', color: 'text-indigo-400 border-indigo-500/30 bg-indigo-500/10' },
  { key: 'carbon_avoidance', label: 'Carbon Avoidance', desc: 'CO₂ emissions avoided by renewable generation', color: 'text-violet-400 border-violet-500/30 bg-violet-500/10' },
];

export default function ReportsPage() {
  const [loading, setLoading] = useState(false);
  const [generating, setGenerating] = useState(null);
  const [lastGenerated, setLastGenerated] = useState({});
  const [previewData, setPreviewData] = useState(null);
  const [notification, setNotification] = useState(null);

  const notify = (msg, type = 'success') => {
    setNotification({ msg, type });
    setTimeout(() => setNotification(null), 4000);
  };

  const handleGenerate = async (reportKey, format = 'json') => {
    setGenerating(`${reportKey}_${format}`);
    try {
      const data = await generateReport(reportKey, format);
      if (format === 'csv') {
        // Trigger download
        const url = URL.createObjectURL(new Blob([data], { type: 'text/csv' }));
        const a = document.createElement('a');
        a.href = url;
        a.download = `${reportKey}_${new Date().toISOString().split('T')[0]}.csv`;
        a.click();
        URL.revokeObjectURL(url);
        notify(`CSV report downloaded: ${reportKey}`);
      } else {
        setPreviewData({ key: reportKey, data });
        notify(`Report generated: ${reportKey}`);
      }
      setLastGenerated(prev => ({ ...prev, [reportKey]: new Date().toLocaleTimeString() }));
    } catch (e) {
      notify(`Report generation failed: ${e.message}`, 'error');
    } finally { setGenerating(null); }
  };

  return (
    <div className="p-6 max-w-screen-2xl mx-auto">
      <div className="flex items-center gap-3 mb-6">
        <FileText size={22} className="text-lime-400" />
        <h1 className="text-xl font-bold text-white">Report Generation</h1>
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

      {/* Report Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-6">
        {REPORT_TYPES.map(({ key, label, desc, color }, i) => (
          <motion.div
            key={key}
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.05 }}
            className="bg-navy-800 border border-navy-600 rounded-xl p-5"
          >
            <div className={`inline-flex items-center gap-1.5 px-2 py-1 rounded-full border text-xs font-medium mb-3 ${color}`}>
              <FileText size={10} />
              {label}
            </div>
            <p className="text-xs text-slate-400 mb-4">{desc}</p>
            {lastGenerated[key] && (
              <p className="text-xs text-slate-500 mb-3">Last generated: {lastGenerated[key]}</p>
            )}
            <div className="flex gap-2">
              <button
                onClick={() => handleGenerate(key, 'json')}
                disabled={generating?.startsWith(key)}
                className="flex-1 flex items-center justify-center gap-1.5 py-2 bg-navy-700 border border-navy-600 text-slate-300 rounded-lg text-xs hover:bg-navy-600 transition-colors disabled:opacity-50"
              >
                {generating === `${key}_json` ? <RefreshCw size={11} className="animate-spin" /> : <FileText size={11} />}
                JSON
              </button>
              <button
                onClick={() => handleGenerate(key, 'csv')}
                disabled={generating?.startsWith(key)}
                className="flex-1 flex items-center justify-center gap-1.5 py-2 bg-navy-700 border border-navy-600 text-slate-300 rounded-lg text-xs hover:bg-navy-600 transition-colors disabled:opacity-50"
              >
                {generating === `${key}_csv` ? <RefreshCw size={11} className="animate-spin" /> : <Download size={11} />}
                CSV
              </button>
            </div>
          </motion.div>
        ))}
      </div>

      {/* JSON Preview Panel */}
      {previewData && (
        <div className="bg-navy-800 border border-navy-600 rounded-xl p-5">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-semibold text-white">Report Preview — {previewData.key}</h3>
            <button onClick={() => setPreviewData(null)} className="text-xs text-slate-400 hover:text-white">Close ✕</button>
          </div>
          <pre className="bg-navy-900 border border-navy-700 rounded-lg p-4 text-xs text-slate-300 overflow-auto max-h-96 font-mono">
            {JSON.stringify(previewData.data, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
}
