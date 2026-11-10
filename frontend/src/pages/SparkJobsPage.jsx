import React, { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { Zap, RefreshCw, CheckCircle, XCircle, Clock, Activity, Database } from 'lucide-react';
import { getSparkJobs, getSparkMetrics } from '../services/api.js';
import SectionHeader from '../components/SectionHeader.jsx';
import LoadingSpinner from '../components/LoadingSpinner.jsx';
import EmptyState from '../components/EmptyState.jsx';
import KpiCard from '../components/KpiCard.jsx';

const statusConfig = {
  COMPLETED: { icon: CheckCircle, color: 'text-emerald-400', bg: 'bg-emerald-500/10' },
  RUNNING: { icon: Activity, color: 'text-blue-400', bg: 'bg-blue-500/10' },
  FAILED: { icon: XCircle, color: 'text-rose-400', bg: 'bg-rose-500/10' },
  PENDING: { icon: Clock, color: 'text-amber-400', bg: 'bg-amber-500/10' },
};

const RDD_OPS = [
  'parallelize()', 'textFile()', 'map()', 'flatMap()', 'filter()', 'distinct()',
  'reduceByKey()', 'groupByKey()', 'sortByKey()', 'join()', 'leftOuterJoin()',
  'union()', 'mapValues()', 'partitionBy()', 'cache()', 'count()', 'collect()',
  'take()', 'first()', 'reduce()', 'saveAsTextFile()'
];

export default function SparkJobsPage() {
  const [jobs, setJobs] = useState([]);
  const [metrics, setMetrics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [autoRefresh, setAutoRefresh] = useState(false);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [jobRes, metRes] = await Promise.allSettled([getSparkJobs(25), getSparkMetrics()]);
      if (jobRes.status === 'fulfilled') setJobs(jobRes.value?.jobs || []);
      if (metRes.status === 'fulfilled') setMetrics(metRes.value);
    } finally { setLoading(false); }
  };

  useEffect(() => { fetchData(); }, []);
  useEffect(() => {
    if (!autoRefresh) return;
    const id = setInterval(fetchData, 10000);
    return () => clearInterval(id);
  }, [autoRefresh]);

  const StatusIcon = ({ status }) => {
    const cfg = statusConfig[status] || statusConfig.PENDING;
    const Icon = cfg.icon;
    return <span className={`flex items-center gap-1 text-xs ${cfg.color}`}><Icon size={12} />{status}</span>;
  };

  const durationMs = (job) => {
    if (!job.started_at) return '—';
    const end = job.completed_at ? new Date(job.completed_at) : new Date();
    const ms = end - new Date(job.started_at);
    if (ms < 1000) return `${ms}ms`;
    if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
    return `${(ms / 60000).toFixed(1)}m`;
  };

  return (
    <div className="p-6 max-w-screen-2xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <Zap size={22} className="text-violet-400" />
          <h1 className="text-xl font-bold text-white">Apache Spark RDD Job Monitor</h1>
        </div>
        <div className="flex items-center gap-3">
          <label className="flex items-center gap-2 text-sm text-slate-400 cursor-pointer">
            <input type="checkbox" checked={autoRefresh} onChange={e => setAutoRefresh(e.target.checked)} className="rounded" />
            Auto-refresh (10s)
          </label>
          <button onClick={fetchData} className="flex items-center gap-2 px-4 py-2 bg-violet-500/20 border border-violet-500/30 text-violet-400 rounded-lg text-sm hover:bg-violet-500/30">
            <RefreshCw size={14} />
            Refresh
          </button>
        </div>
      </div>

      {/* Metrics KPIs */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <KpiCard title="Total Jobs" value={metrics?.total_jobs ?? jobs.length} icon={Zap} color="violet" loading={loading} />
        <KpiCard title="Completed" value={metrics?.completed ?? jobs.filter(j => j.status === 'COMPLETED').length} icon={CheckCircle} color="emerald" loading={loading} />
        <KpiCard title="Failed" value={metrics?.failed ?? jobs.filter(j => j.status === 'FAILED').length} icon={XCircle} color="rose" loading={loading} />
        <KpiCard title="Records Processed" value={metrics?.total_records_processed?.toLocaleString() ?? (jobs.reduce((s, j) => s + (j.records_processed || 0), 0)).toLocaleString()} icon={Database} color="violet" loading={loading} />
      </div>

      {/* RDD Operations Reference */}
      <div className="bg-navy-800 border border-navy-600 rounded-xl p-5 mb-5">
        <SectionHeader title="RDD Transformation & Action Catalogue" icon={Zap} color="violet" subtitle="All operations implemented in spark_engine/ — PySpark 4.x RDD API" />
        <div className="flex flex-wrap gap-2">
          {RDD_OPS.map(op => (
            <span key={op} className="px-2 py-1 bg-violet-500/10 border border-violet-500/20 text-violet-300 rounded text-xs font-mono">
              {op}
            </span>
          ))}
        </div>
        <div className="mt-4 grid grid-cols-1 md:grid-cols-3 gap-3 text-xs text-slate-400">
          <div className="bg-navy-700 rounded-lg p-3">
            <p className="text-violet-400 font-semibold mb-1">Pipeline Stages</p>
            <p>1. load_csv_lines() → textFile()</p>
            <p>2. clean_and_parse_csv() → map() + filter()</p>
            <p>3. process_*_rdd() → map() + mapValues()</p>
            <p>4. aggregate_daily_summaries() → reduceByKey() + sortByKey()</p>
            <p>5. detect_anomalies_rdd() → flatMap() + reduceByKey()</p>
            <p>6. temporal_join() → leftOuterJoin() + union()</p>
          </div>
          <div className="bg-navy-700 rounded-lg p-3">
            <p className="text-blue-400 font-semibold mb-1">SparkContext Config</p>
            <p>Master: local[*]</p>
            <p>App: RenewableEnergyPlatform</p>
            <p>JAVA_HOME: C:\Program Files\Java\jdk-17</p>
            <p>PySpark: 4.x</p>
            <p>Python: venv\Scripts\python.exe</p>
          </div>
          <div className="bg-navy-700 rounded-lg p-3">
            <p className="text-emerald-400 font-semibold mb-1">Data Sources</p>
            <p>bhadla_solar_telemetry.csv</p>
            <p>muppandal_wind_telemetry.csv</p>
            <p>tehri_hydro_telemetry.csv</p>
            <p>olkaria_geothermal_telemetry.csv</p>
            <p>ironbridge_biomass_telemetry.csv</p>
          </div>
        </div>
      </div>

      {/* Jobs Table */}
      <div className="bg-navy-800 border border-navy-600 rounded-xl overflow-hidden">
        <div className="px-5 py-4 border-b border-navy-700">
          <h3 className="text-sm font-semibold text-white">Recent Spark Jobs</h3>
        </div>
        {loading ? (
          <LoadingSpinner message="Loading Spark jobs..." />
        ) : jobs.length === 0 ? (
          <EmptyState
            title="No Spark jobs yet"
            message="Run a pipeline from any energy source page to see jobs here."
            icon={Zap}
          />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-navy-700 text-left">
                  <th className="px-4 py-3 text-xs text-slate-400 uppercase">Job ID</th>
                  <th className="px-4 py-3 text-xs text-slate-400 uppercase">Source</th>
                  <th className="px-4 py-3 text-xs text-slate-400 uppercase">Type</th>
                  <th className="px-4 py-3 text-xs text-slate-400 uppercase">Status</th>
                  <th className="px-4 py-3 text-xs text-slate-400 uppercase">Records</th>
                  <th className="px-4 py-3 text-xs text-slate-400 uppercase">Duration</th>
                  <th className="px-4 py-3 text-xs text-slate-400 uppercase">Started</th>
                  <th className="px-4 py-3 text-xs text-slate-400 uppercase">Error</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-navy-700">
                {jobs.map((job) => (
                  <motion.tr key={job.id} initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="hover:bg-navy-700/40">
                    <td className="px-4 py-3 font-mono text-xs text-slate-400">{job.id?.slice(0, 8)}…</td>
                    <td className="px-4 py-3 text-slate-300 capitalize">{job.energy_source}</td>
                    <td className="px-4 py-3 text-slate-400 text-xs">{job.job_type}</td>
                    <td className="px-4 py-3"><StatusIcon status={job.status} /></td>
                    <td className="px-4 py-3 text-slate-300 font-mono">{job.records_processed?.toLocaleString() || '—'}</td>
                    <td className="px-4 py-3 text-slate-300 font-mono">{durationMs(job)}</td>
                    <td className="px-4 py-3 text-slate-500 text-xs whitespace-nowrap">
                      {job.started_at ? new Date(job.started_at).toLocaleString() : '—'}
                    </td>
                    <td className="px-4 py-3 text-rose-400 text-xs max-w-xs truncate" title={job.error_message}>
                      {job.error_message || '—'}
                    </td>
                  </motion.tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
