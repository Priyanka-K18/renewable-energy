import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { motion } from 'framer-motion';
import { AlertTriangle, CheckCircle, Filter, RefreshCw, RotateCcw, XCircle } from 'lucide-react';
import { getAnomalies, updateAnomalyStatus } from '../services/api.js';
import LoadingSpinner from '../components/LoadingSpinner.jsx';
import EmptyState from '../components/EmptyState.jsx';
import { SeverityBadge, StatusBadge } from '../components/AnomalyBadge.jsx';

const ENERGY_SOURCES = ['', 'solar', 'wind', 'hydropower', 'geothermal', 'biomass'];
const STATUSES = ['', 'Open', 'Investigating', 'Resolved', 'Ignored'];
const SEVERITIES = ['', 'Critical', 'High', 'Medium', 'Low'];

function getErrorMessage(error) {
  const detail = error?.response?.data?.detail;
  return typeof detail === 'string' ? detail : error?.message || 'An unexpected error occurred.';
}

export default function AnomaliesPage() {
  const [anomalies, setAnomalies] = useState([]);
  const [loading, setLoading] = useState(true);
  const [updating, setUpdating] = useState(null);
  const [error, setError] = useState('');
  const [filterStatus, setFilterStatus] = useState('');
  const [filterSeverity, setFilterSeverity] = useState('');
  const [filterSource, setFilterSource] = useState('');
  const [selectedAnomaly, setSelectedAnomaly] = useState(null);
  const [resolutionNote, setResolutionNote] = useState('');

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const response = await getAnomalies();
      const rows = Array.isArray(response) ? response : response?.anomalies;
      if (!Array.isArray(rows)) {
        throw new Error('The anomalies API returned an unexpected response.');
      }
      setAnomalies(rows);
    } catch (requestError) {
      setError(getErrorMessage(requestError));
      setAnomalies([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);

  const filteredAnomalies = useMemo(() => anomalies.filter((anomaly) => (
    (!filterStatus || anomaly.status?.toLowerCase() === filterStatus.toLowerCase())
    && (!filterSeverity || anomaly.severity?.toLowerCase() === filterSeverity.toLowerCase())
    && (!filterSource || anomaly.energy_source?.toLowerCase() === filterSource)
  )), [anomalies, filterSeverity, filterSource, filterStatus]);

  const handleStatusUpdate = async (anomalyId, newStatus) => {
    setUpdating(anomalyId);
    try {
      await updateAnomalyStatus(anomalyId, newStatus, resolutionNote);
      await fetchData();
      setSelectedAnomaly(null);
      setResolutionNote('');
    } catch (requestError) {
      setError(`Could not update anomaly: ${getErrorMessage(requestError)}`);
    } finally {
      setUpdating(null);
    }
  };

  const countBySeverity = (severity) => anomalies.filter(
    (anomaly) => anomaly.severity?.toLowerCase() === severity.toLowerCase(),
  ).length;

  return (
    <div className="p-6 max-w-screen-2xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <AlertTriangle size={22} className="text-rose-400" />
          <h1 className="text-xl font-bold text-white">Anomaly Management</h1>
        </div>
        <button onClick={fetchData} className="p-2 bg-navy-800 border border-navy-600 rounded-lg text-slate-400 hover:text-white"><RefreshCw size={14} /></button>
      </div>

      {/* Stats Row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        {[
          { label: 'Critical', count: countBySeverity('Critical'), color: 'text-rose-400 bg-rose-500/10 border-rose-500/20' },
          { label: 'High', count: countBySeverity('High'), color: 'text-orange-400 bg-orange-500/10 border-orange-500/20' },
          { label: 'Medium', count: countBySeverity('Medium'), color: 'text-amber-400 bg-amber-500/10 border-amber-500/20' },
          { label: 'Low', count: countBySeverity('Low'), color: 'text-blue-400 bg-blue-500/10 border-blue-500/20' },
        ].map(({ label, count, color }) => (
          <div key={label} className={`border rounded-xl p-4 ${color}`}>
            <p className="text-xs uppercase tracking-wider opacity-70">{label}</p>
            <p className="text-2xl font-bold font-mono mt-1">{count}</p>
          </div>
        ))}
      </div>

      {/* Filters */}
      <div className="bg-navy-800 border border-navy-600 rounded-xl p-4 mb-5">
        <div className="flex items-center gap-3 flex-wrap">
          <Filter size={14} className="text-slate-400 flex-shrink-0" />
          <span className="text-sm text-slate-400">Filter:</span>
          {[
            { label: 'Status', value: filterStatus, onChange: setFilterStatus, options: STATUSES },
            { label: 'Severity', value: filterSeverity, onChange: setFilterSeverity, options: SEVERITIES },
            { label: 'Source', value: filterSource, onChange: setFilterSource, options: ENERGY_SOURCES },
          ].map(({ label, value, onChange, options }) => (
            <select key={label} value={value} onChange={e => onChange(e.target.value)} className="bg-navy-700 border border-navy-600 text-sm text-white rounded-lg px-3 py-1.5">
              <option value="">All {label}s</option>
              {options.filter(Boolean).map(option => <option key={option} value={option}>{option}</option>)}
            </select>
          ))}
          {(filterStatus || filterSeverity || filterSource) && (
            <button
              onClick={() => { setFilterStatus(''); setFilterSeverity(''); setFilterSource(''); }}
              className="text-xs text-teal-300 hover:text-teal-200"
            >
              Clear filters
            </button>
          )}
        </div>
      </div>

      {/* Anomalies Table */}
      <div className="bg-navy-800 border border-navy-600 rounded-xl overflow-hidden">
        {error && (
          <div role="alert" className="m-4 flex flex-wrap items-center justify-between gap-3 rounded-lg border border-rose-500/30 bg-rose-500/10 px-4 py-3 text-sm text-rose-300">
            <span>{error}</span>
            <button onClick={fetchData} className="flex items-center gap-2 rounded-md border border-rose-400/30 px-3 py-1.5 hover:bg-rose-500/10">
              <RefreshCw size={13} /> Retry
            </button>
          </div>
        )}
        {loading ? (
          <LoadingSpinner message="Loading anomalies..." />
        ) : filteredAnomalies.length === 0 ? (
          <EmptyState
            title={error ? 'Anomalies could not be loaded' : 'No anomalies found'}
            message={error ? 'Check the API connection and retry.' : anomalies.length ? 'No anomalies match your current filters.' : 'The API returned no anomaly records yet. Process telemetry data or refresh to check again.'}
            icon={error ? XCircle : anomalies.length ? Filter : CheckCircle}
            action={error || anomalies.length === 0 ? (
              <button onClick={fetchData} className="inline-flex items-center gap-2 rounded-lg border border-navy-600 px-3 py-2 text-xs text-slate-300 hover:bg-navy-700">
                <RefreshCw size={13} /> Refresh anomalies
              </button>
            ) : null}
          />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-navy-700 text-left">
                  <th className="px-4 py-3 text-xs text-slate-400 uppercase tracking-wider">Source</th>
                  <th className="px-4 py-3 text-xs text-slate-400 uppercase tracking-wider">Type</th>
                  <th className="px-4 py-3 text-xs text-slate-400 uppercase tracking-wider">Severity</th>
                  <th className="px-4 py-3 text-xs text-slate-400 uppercase tracking-wider">Status</th>
                  <th className="px-4 py-3 text-xs text-slate-400 uppercase tracking-wider">Plant / Equipment</th>
                  <th className="px-4 py-3 text-xs text-slate-400 uppercase tracking-wider">Description</th>
                  <th className="px-4 py-3 text-xs text-slate-400 uppercase tracking-wider">Detected</th>
                  <th className="px-4 py-3 text-xs text-slate-400 uppercase tracking-wider">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-navy-700">
                {filteredAnomalies.map((a) => (
                  <motion.tr key={a.id} initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="hover:bg-navy-700/40 transition-colors">
                    <td className="px-4 py-3 text-slate-300 capitalize font-medium">{a.energy_source}</td>
                    <td className="px-4 py-3 text-slate-400">{a.anomaly_type}</td>
                    <td className="px-4 py-3"><SeverityBadge severity={a.severity} /></td>
                    <td className="px-4 py-3"><StatusBadge status={a.status} /></td>
                    <td className="px-4 py-3 text-slate-400 font-mono text-xs">
                      <span className="block">{a.plant_id || '—'}</span>
                      {a.equipment_code && <span className="block text-slate-500">{a.equipment_code}</span>}
                    </td>
                    <td className="px-4 py-3 text-slate-400 max-w-xs">
                      <p className="truncate" title={a.description}>{a.description}</p>
                    </td>
                    <td className="px-4 py-3 text-slate-500 text-xs whitespace-nowrap">
                      {a.detected_at ? new Date(a.detected_at).toLocaleString() : '—'}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex gap-2">
                        {a.status?.toLowerCase() === 'open' && (
                          <button
                            onClick={() => handleStatusUpdate(a.id, 'Investigating')}
                            disabled={updating === a.id}
                            className="text-xs px-2 py-1 bg-amber-500/20 text-amber-400 border border-amber-500/30 rounded hover:bg-amber-500/30 transition-colors"
                          >
                            Investigate
                          </button>
                        )}
                        {['open', 'investigating'].includes(a.status?.toLowerCase()) && (
                          <button
                            onClick={() => { setSelectedAnomaly(a); setResolutionNote(''); }}
                            className="text-xs px-2 py-1 bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 rounded hover:bg-emerald-500/30 transition-colors"
                          >
                            Resolve
                          </button>
                        )}
                      </div>
                    </td>
                  </motion.tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {!loading && !error && filteredAnomalies.length > 0 && (
          <div className="border-t border-navy-700 px-4 py-3 text-xs text-slate-500">
            Showing {filteredAnomalies.length} of {anomalies.length} anomalies
          </div>
        )}
      </div>

      {/* Resolve Modal */}
      {selectedAnomaly && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="bg-navy-800 border border-navy-600 rounded-xl p-6 max-w-md w-full"
          >
            <h3 className="text-base font-bold text-white mb-2">Resolve Anomaly</h3>
            <p className="text-sm text-slate-400 mb-4">{selectedAnomaly.description}</p>
            <textarea
              value={resolutionNote}
              onChange={e => setResolutionNote(e.target.value)}
              placeholder="Resolution notes (optional)..."
              className="w-full bg-navy-700 border border-navy-600 rounded-lg p-3 text-sm text-white placeholder-slate-500 resize-none"
              rows={3}
            />
            <div className="flex gap-3 mt-4">
              <button
                onClick={() => handleStatusUpdate(selectedAnomaly.id, 'Resolved')}
                disabled={updating === selectedAnomaly.id}
                className="flex-1 py-2 bg-emerald-500/20 border border-emerald-500/30 text-emerald-400 rounded-lg text-sm hover:bg-emerald-500/30 transition-colors"
              >
                {updating === selectedAnomaly.id ? <RefreshCw size={14} className="animate-spin mx-auto" /> : 'Mark Resolved'}
              </button>
              <button
                onClick={() => handleStatusUpdate(selectedAnomaly.id, 'Ignored')}
                disabled={updating === selectedAnomaly.id}
                className="flex-1 py-2 bg-slate-500/20 border border-slate-500/30 text-slate-400 rounded-lg text-sm hover:bg-slate-500/30 transition-colors"
              >
                <span className="inline-flex items-center justify-center gap-1"><RotateCcw size={13} /> Ignore</span>
              </button>
              <button onClick={() => setSelectedAnomaly(null)} className="px-4 py-2 text-slate-400 hover:text-white transition-colors text-sm">
                Cancel
              </button>
            </div>
          </motion.div>
        </div>
      )}
    </div>
  );
}
