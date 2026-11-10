import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  AlertCircle, CheckCircle, ChevronLeft, ChevronRight, Database, Download,
  FileText, Play, RefreshCw, Trash2, Upload, X,
} from 'lucide-react';
import {
  CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts';
import { supabase } from '../lib/supabase.js';
import {
  cancelDatasetProcessing, deleteDataset, downloadDataset, getDataset, getDatasetPreview, getDatasets,
  processSampleDataset, triggerDatasetProcessing, uploadDatasetFile,
} from '../services/api.js';
import SectionHeader from '../components/SectionHeader.jsx';
import LoadingSpinner from '../components/LoadingSpinner.jsx';

const SOURCES = [
  { key: 'solar', label: 'Solar', color: 'text-amber-400 bg-amber-500/10 border-amber-500/20', file: 'bhadla_solar_telemetry.csv' },
  { key: 'wind', label: 'Wind', color: 'text-blue-400 bg-blue-500/10 border-blue-500/20', file: 'muppandal_wind_telemetry.csv' },
  { key: 'hydropower', label: 'Hydropower', color: 'text-cyan-400 bg-cyan-500/10 border-cyan-500/20', file: 'tehri_hydro_telemetry.csv' },
  { key: 'geothermal', label: 'Geothermal', color: 'text-orange-400 bg-orange-500/10 border-orange-500/20', file: 'olkaria_geothermal_telemetry.csv' },
  { key: 'biomass', label: 'Biomass', color: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20', file: 'ironbridge_biomass_telemetry.csv' },
];
const PAGE_SIZE = 50;
const ACTIVE_STATES = new Set(['queued', 'validating', 'processing', 'persisting']);

function errorMessage(error) {
  const detail = error?.response?.data?.detail;
  if (typeof detail === 'string') return detail;
  if (detail) return JSON.stringify(detail);
  return error?.message || 'An unexpected error occurred.';
}

function StatusBadge({ status }) {
  const normalized = (status || 'unknown').toLowerCase();
  const tone = normalized === 'completed'
    ? 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20'
    : normalized === 'failed'
      ? 'text-rose-400 bg-rose-500/10 border-rose-500/20'
      : 'text-amber-300 bg-amber-500/10 border-amber-500/20';
  return <span className={`inline-flex rounded-full border px-2 py-0.5 text-xs capitalize ${tone}`}>{normalized}</span>;
}

function DatasetDetails({ datasetId, onClose, notify }) {
  const [dataset, setDataset] = useState(null);
  const [preview, setPreview] = useState({ records: [], total: 0 });
  const [classification, setClassification] = useState('');
  const [offset, setOffset] = useState(0);
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    try {
      const [nextDataset, nextPreview] = await Promise.all([
        getDataset(datasetId),
        getDatasetPreview(datasetId, PAGE_SIZE, offset, classification || null),
      ]);
      setDataset(nextDataset);
      setPreview(nextPreview);
    } catch (error) {
      notify(`Could not load dataset details: ${errorMessage(error)}`, 'error');
    } finally {
      setLoading(false);
    }
  }, [datasetId, offset, classification, notify]);

  useEffect(() => { load(); }, [load]);
  useEffect(() => {
    if (!dataset || !ACTIVE_STATES.has(dataset.processing_status)) return undefined;
    const timer = window.setInterval(load, 2500);
    return () => window.clearInterval(timer);
  }, [dataset, load]);

  const columns = useMemo(
    () => [...new Set(preview.records.flatMap((row) => Object.keys(row.record || {})))].slice(0, 8),
    [preview.records],
  );
  const visibleRecords = useMemo(() => {
    const query = search.trim().toLowerCase();
    return query
      ? preview.records.filter((row) => JSON.stringify(row.record).toLowerCase().includes(query))
      : preview.records;
  }, [preview.records, search]);

  const quality = dataset?.quality_report || {};
  const analytics = dataset?.analytics || {};

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-black/70 p-4 md:p-8">
      <section className="my-auto w-full max-w-6xl rounded-2xl border border-navy-600 bg-navy-900 shadow-2xl">
        <div className="flex items-start justify-between border-b border-navy-700 p-5">
          <div className="min-w-0">
            <h2 className="truncate text-lg font-semibold text-white">{dataset?.original_filename || 'Dataset details'}</h2>
            <p className="mt-1 text-xs text-slate-400">
              {dataset?.energy_source} · {dataset?.file_format?.toUpperCase()} · {dataset?.progress_stage || 'Loading'}
            </p>
          </div>
          <button onClick={onClose} aria-label="Close details" className="ml-4 rounded-lg p-2 text-slate-400 hover:bg-navy-700 hover:text-white">
            <X size={18} />
          </button>
        </div>
        {loading && !dataset ? <LoadingSpinner /> : (
          <div className="space-y-5 p-5">
            <div className="flex flex-wrap items-center gap-3">
              <StatusBadge status={dataset?.processing_status} />
              <span className="text-xs text-slate-400">{dataset?.total_records?.toLocaleString() || 0} rows</span>
              {dataset?.processing_error && <span className="text-sm text-rose-400">{dataset.processing_error}</span>}
              {dataset && ACTIVE_STATES.has(dataset.processing_status) && (
                <button onClick={async () => {
                  try {
                    await cancelDatasetProcessing(datasetId);
                    notify('Dataset processing cancelled.');
                    await load();
                  } catch (error) {
                    notify(`Could not cancel processing: ${errorMessage(error)}`, 'error');
                  }
                }} className="rounded-lg border border-rose-500/30 px-3 py-1.5 text-xs text-rose-300 hover:bg-rose-500/10">
                  Cancel processing
                </button>
              )}
            </div>
            {dataset?.processing_status === 'completed' && (
              <>
                <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                  {[
                    ['Valid', quality.valid_rows ?? dataset.valid_records ?? 0],
                    ['Warnings', quality.warning_rows ?? dataset.warning_records ?? 0],
                    ['Invalid', quality.invalid_rows ?? dataset.invalid_records ?? 0],
                    ['Duplicates', quality.duplicate_rows ?? dataset.duplicate_records ?? 0],
                  ].map(([label, value]) => (
                    <div key={label} className="rounded-xl border border-navy-700 bg-navy-800 p-4">
                      <p className="text-xs uppercase tracking-wide text-slate-400">{label}</p>
                      <p className="mt-1 text-xl font-semibold text-white">{Number(value).toLocaleString()}</p>
                    </div>
                  ))}
                </div>
                <div className="grid gap-4 lg:grid-cols-2">
                  <div className="rounded-xl border border-navy-700 bg-navy-800 p-4">
                    <h3 className="mb-3 text-sm font-semibold text-white">Quality report</h3>
                    <p className="text-sm text-slate-300">Validation score: {quality.validation_score_pct ?? 0}%</p>
                    <p className="mt-1 text-xs text-slate-400">
                      {quality.invalid_timestamps || 0} invalid timestamps · {quality.negative_readings || 0} negative readings flagged
                    </p>
                    {!!quality.warnings?.length && <ul className="mt-3 list-disc space-y-1 pl-5 text-xs text-amber-300">{quality.warnings.map((warning) => <li key={warning}>{warning}</li>)}</ul>}
                  </div>
                  <div className="rounded-xl border border-navy-700 bg-navy-800 p-4">
                    <h3 className="mb-3 text-sm font-semibold text-white">Numeric summaries</h3>
                    {Object.keys(analytics.measured_or_derived || {}).length === 0
                      ? <p className="text-xs text-slate-400">No numeric columns were detected.</p>
                      : <div className="max-h-40 space-y-2 overflow-auto">
                        {Object.entries(analytics.measured_or_derived).map(([column, stat]) => (
                          <div key={column} className="flex justify-between gap-3 text-xs">
                            <span className="truncate text-slate-300">{column} · avg {Number(stat.average).toPrecision(5)}</span>
                            <span className="shrink-0 text-slate-500">{stat.observations} rows</span>
                          </div>
                        ))}
                      </div>}
                  </div>
                </div>
                {!!analytics.by_date?.length && (
                  <div className="h-64 rounded-xl border border-navy-700 bg-navy-800 p-4">
                    <h3 className="mb-3 text-sm font-semibold text-white">Energy by date · {analytics.by_date[0].column}</h3>
                    <ResponsiveContainer width="100%" height="85%">
                      <LineChart data={analytics.by_date}>
                        <CartesianGrid stroke="#26364f" strokeDasharray="3 3" />
                        <XAxis dataKey="date" tick={{ fill: '#94a3b8', fontSize: 10 }} />
                        <YAxis tick={{ fill: '#94a3b8', fontSize: 10 }} />
                        <Tooltip contentStyle={{ background: '#101b2d', border: '1px solid #334155' }} />
                        <Line type="monotone" dataKey="value" stroke="#2dd4bf" dot={false} />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                )}
              </>
            )}
            {dataset?.schema_report?.columns?.length > 0 && (
              <div className="rounded-xl border border-navy-700 bg-navy-800 p-4">
                <h3 className="mb-3 text-sm font-semibold text-white">Detected schema</h3>
                <div className="flex flex-wrap gap-2">
                  {dataset.schema_report.columns.map((column) => (
                    <span key={column.name} className="rounded-md border border-navy-600 bg-navy-700 px-2 py-1 text-xs text-slate-300">
                      {column.name} <span className="text-teal-300">{column.type}</span>
                    </span>
                  ))}
                </div>
              </div>
            )}
            <div className="rounded-xl border border-navy-700 bg-navy-800">
              <div className="flex flex-wrap items-center justify-between gap-3 border-b border-navy-700 p-4">
                <h3 className="text-sm font-semibold text-white">Record preview</h3>
                <div className="flex flex-wrap gap-2">
                  <input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search this page" className="w-40 rounded-lg border border-navy-600 bg-navy-900 px-3 py-1.5 text-xs text-white" />
                  <select value={classification} onChange={(event) => { setClassification(event.target.value); setOffset(0); }} className="rounded-lg border border-navy-600 bg-navy-900 px-2 py-1.5 text-xs text-white">
                    <option value="">All classifications</option>
                    <option value="valid">Valid</option><option value="warning">Warning</option>
                    <option value="invalid">Invalid</option><option value="duplicate">Duplicate</option>
                  </select>
                </div>
              </div>
              <div className="max-h-80 overflow-auto">
                {visibleRecords.length === 0 ? <p className="p-5 text-sm text-slate-500">No records on this page.</p> : (
                  <table className="w-full text-left text-xs">
                    <thead className="sticky top-0 bg-navy-800 text-slate-400"><tr>
                      <th className="p-3">#</th><th className="p-3">Quality</th>
                      {columns.map((column) => <th className="p-3" key={column}>{column}</th>)}
                    </tr></thead>
                    <tbody className="divide-y divide-navy-700">
                      {visibleRecords.map((row) => <tr key={row.row_number}>
                        <td className="p-3 text-slate-500">{row.row_number}</td>
                        <td className="p-3 capitalize text-slate-300">{row.classification}</td>
                        {columns.map((column) => <td className="max-w-48 truncate p-3 text-slate-300" key={column}>{String(row.record?.[column] ?? '—')}</td>)}
                      </tr>)}
                    </tbody>
                  </table>
                )}
              </div>
              <div className="flex items-center justify-between border-t border-navy-700 p-3 text-xs text-slate-400">
                <span>{preview.total.toLocaleString()} matching records</span>
                <div className="flex items-center gap-2">
                  <button disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))} className="rounded p-1 hover:bg-navy-700 disabled:opacity-40"><ChevronLeft size={16} /></button>
                  <span>{preview.total ? Math.floor(offset / PAGE_SIZE) + 1 : 0} / {Math.max(1, Math.ceil(preview.total / PAGE_SIZE))}</span>
                  <button disabled={offset + PAGE_SIZE >= preview.total} onClick={() => setOffset(offset + PAGE_SIZE)} className="rounded p-1 hover:bg-navy-700 disabled:opacity-40"><ChevronRight size={16} /></button>
                </div>
              </div>
            </div>
          </div>
        )}
      </section>
    </div>
  );
}

export default function DatasetsPage() {
  const [datasets, setDatasets] = useState([]);
  const [session, setSession] = useState(null);
  const [authReady, setAuthReady] = useState(false);
  const [authMode, setAuthMode] = useState('signin');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [authBusy, setAuthBusy] = useState(false);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadSource, setUploadSource] = useState('solar');
  const [uploadDescription, setUploadDescription] = useState('');
  const [notification, setNotification] = useState(null);
  const [detailId, setDetailId] = useState(null);
  const [dragging, setDragging] = useState(false);
  const fileRef = useRef(null);
  const uploadController = useRef(null);
  const noticeTimer = useRef(null);

  const notify = useCallback((message, type = 'success') => {
    setNotification({ message, type });
    window.clearTimeout(noticeTimer.current);
    noticeTimer.current = window.setTimeout(() => setNotification(null), 6000);
  }, []);

  const fetchData = useCallback(async () => {
    if (!session) return;
    setLoading(true);
    try {
      const result = await getDatasets();
      setDatasets(result.datasets || []);
    } catch (error) {
      notify(`Could not load datasets: ${errorMessage(error)}`, 'error');
    } finally {
      setLoading(false);
    }
  }, [session, notify]);

  useEffect(() => {
    let active = true;
    const { data: authListener } = supabase.auth.onAuthStateChange((_event, nextSession) => {
      if (active) setSession(nextSession);
    });
    supabase.auth.getSession().then(({ data, error }) => {
      if (!active) return;
      if (error) notify(`Could not read Supabase session: ${error.message}`, 'error');
      setSession(data.session);
      setAuthReady(true);
    }).catch((error) => {
      if (active) {
        notify(`Could not read Supabase session: ${error.message}`, 'error');
        setAuthReady(true);
      }
    });
    return () => {
      active = false;
      authListener.subscription.unsubscribe();
      window.clearTimeout(noticeTimer.current);
    };
  }, [notify]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const hasActiveJobs = datasets.some((dataset) => ACTIVE_STATES.has(dataset.processing_status));
  useEffect(() => {
    if (!hasActiveJobs || !session) return undefined;
    const timer = window.setInterval(fetchData, 2500);
    return () => window.clearInterval(timer);
  }, [fetchData, hasActiveJobs, session]);

  const handleAuth = async (event) => {
    event.preventDefault();
    setAuthBusy(true);
    try {
      const result = authMode === 'signup'
        ? await supabase.auth.signUp({ email, password })
        : await supabase.auth.signInWithPassword({ email, password });
      if (result.error) throw result.error;
      if (authMode === 'signup' && !result.data.session) {
        notify('Account created. Check your email to confirm it, then sign in.');
      } else {
        notify(authMode === 'signup' ? 'Account created and signed in.' : 'Signed in successfully.');
      }
    } catch (error) {
      notify(`Authentication failed: ${error.message}`, 'error');
    } finally {
      setAuthBusy(false);
    }
  };

  const handleSignOut = async () => {
    const { error } = await supabase.auth.signOut();
    if (error) notify(`Could not sign out: ${error.message}`, 'error');
    else {
      setDatasets([]);
      setDetailId(null);
      notify('Signed out.');
    }
  };

  const handleUpload = async (file) => {
    if (!file) return;
    if (!/\.(csv|xlsx|xls|json)$/i.test(file.name)) {
      notify('Choose a CSV, XLSX, XLS, or JSON file.', 'error');
      return;
    }
    const formData = new FormData();
    formData.append('file', file);
    formData.append('energy_source', uploadSource);
    formData.append('description', uploadDescription);
    const controller = new AbortController();
    uploadController.current = controller;
    setUploading(true);
    setUploadProgress(0);
    try {
      const result = await uploadDatasetFile(formData, {
        signal: controller.signal,
        onUploadProgress: (event) => {
          if (event.total) setUploadProgress(Math.round((event.loaded * 100) / event.total));
        },
      });
      notify(`${file.name} uploaded. Spark processing is ${result.status}.`);
      await fetchData();
    } catch (error) {
      if (error.name !== 'CanceledError' && error.name !== 'AbortError') {
        notify(`Upload failed: ${errorMessage(error)}`, 'error');
      } else {
        notify('Upload cancelled.');
      }
    } finally {
      uploadController.current = null;
      setUploading(false);
      setUploadProgress(0);
      if (fileRef.current) fileRef.current.value = '';
    }
  };

  const handleSample = async (source) => {
    try {
      await processSampleDataset(source);
      notify(`Spark pipeline completed for ${source}.`);
    } catch (error) {
      notify(`Sample pipeline failed: ${errorMessage(error)}`, 'error');
    }
  };

  const handleDownload = async (dataset) => {
    try {
      const blob = await downloadDataset(dataset.id);
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = dataset.original_filename;
      link.click();
      URL.revokeObjectURL(url);
    } catch (error) {
      notify(`Download failed: ${errorMessage(error)}`, 'error');
    }
  };

  const handleDelete = async (dataset) => {
    if (!window.confirm(`Delete "${dataset.original_filename}" and its processed records?`)) return;
    try {
      await deleteDataset(dataset.id);
      setDatasets((current) => current.filter((item) => item.id !== dataset.id));
      if (detailId === dataset.id) setDetailId(null);
      notify('Dataset and its processed records were deleted.');
    } catch (error) {
      notify(`Delete failed: ${errorMessage(error)}`, 'error');
    }
  };

  return (
    <div className="mx-auto max-w-screen-2xl p-6">
      <div className="mb-6 flex items-center gap-3">
        <Database size={22} className="text-teal-400" />
        <div><h1 className="text-xl font-bold text-white">Dataset Management</h1><p className="mt-1 text-xs text-slate-400">Upload and quality-check renewable energy records with Apache Spark RDD.</p></div>
      </div>

      {notification && (
        <div role="status" className={`mb-5 flex items-center gap-3 rounded-xl border px-4 py-3 text-sm ${notification.type === 'error' ? 'border-rose-500/30 bg-rose-500/10 text-rose-300' : 'border-emerald-500/30 bg-emerald-500/10 text-emerald-300'}`}>
          {notification.type === 'error' ? <AlertCircle size={16} /> : <CheckCircle size={16} />}{notification.message}
        </div>
      )}

      <section className="mb-5 rounded-xl border border-navy-600 bg-navy-800 p-5">
        <SectionHeader title="Sample Pipelines" icon={Play} color="cyan" subtitle="Run the existing bundled telemetry examples. These do not represent live measurements." />
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5">
          {SOURCES.map(({ key, label, color, file }) => (
            <div key={key} className="rounded-xl border border-navy-600 bg-navy-700 p-4">
              <p className={`mb-2 text-xs font-semibold uppercase tracking-wider ${color.split(' ')[0]}`}>{label}</p>
              <p className="mb-3 break-all font-mono text-xs text-slate-500">{file}</p>
              <button onClick={() => handleSample(key)} className={`flex w-full items-center justify-center gap-2 rounded-lg border py-2 text-xs transition-colors ${color}`}>
                <Play size={12} /> Run Spark Pipeline
              </button>
            </div>
          ))}
        </div>
      </section>

      <section className="mb-5 rounded-xl border border-navy-600 bg-navy-800 p-5">
        <SectionHeader title="Upload a Dataset" icon={Upload} color="cyan" subtitle="Accepted: CSV, XLSX, XLS, and JSON. Files are owner-scoped and validated before analysis." />
        {!authReady ? <LoadingSpinner /> : !session ? (
          <div className="grid gap-5 lg:grid-cols-[1fr_1.2fr]">
            <p className="text-sm leading-6 text-slate-300">Sign in with Supabase Auth to upload and manage private datasets. The backend verifies your access token; the demo API tokens are not accepted here.</p>
            <form onSubmit={handleAuth} className="grid gap-3 sm:grid-cols-2">
              <input type="email" required autoComplete="email" value={email} onChange={(event) => setEmail(event.target.value)} placeholder="Email" className="rounded-lg border border-navy-600 bg-navy-900 px-3 py-2 text-sm text-white" />
              <input type="password" required minLength={6} autoComplete={authMode === 'signup' ? 'new-password' : 'current-password'} value={password} onChange={(event) => setPassword(event.target.value)} placeholder="Password" className="rounded-lg border border-navy-600 bg-navy-900 px-3 py-2 text-sm text-white" />
              <div className="flex items-center gap-3 sm:col-span-2">
                <button disabled={authBusy} className="rounded-lg bg-teal-500/20 px-4 py-2 text-sm text-teal-300 disabled:opacity-50">{authBusy ? 'Please wait…' : authMode === 'signup' ? 'Create account' : 'Sign in'}</button>
                <button type="button" onClick={() => setAuthMode(authMode === 'signup' ? 'signin' : 'signup')} className="text-xs text-slate-400 hover:text-white">{authMode === 'signup' ? 'Have an account? Sign in' : 'New here? Create account'}</button>
              </div>
            </form>
          </div>
        ) : (
          <>
            <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
              <p className="text-xs text-slate-400">Signed in as <span className="text-slate-200">{session.user.email}</span></p>
              <button onClick={handleSignOut} className="text-xs text-slate-400 hover:text-white">Sign out</button>
            </div>
            <div className="flex flex-wrap items-center gap-3">
              <select value={uploadSource} onChange={(event) => setUploadSource(event.target.value)} className="rounded-lg border border-navy-600 bg-navy-700 px-3 py-2 text-sm text-white">
                {SOURCES.map((source) => <option key={source.key} value={source.key}>{source.label}</option>)}
              </select>
              <input value={uploadDescription} onChange={(event) => setUploadDescription(event.target.value)} maxLength={2000} placeholder="Optional description" className="min-w-52 flex-1 rounded-lg border border-navy-600 bg-navy-700 px-3 py-2 text-sm text-white" />
              <input ref={fileRef} type="file" accept=".csv,.xlsx,.xls,.json" className="hidden" onChange={(event) => handleUpload(event.target.files?.[0])} />
              <button onClick={() => fileRef.current?.click()} disabled={uploading} className="flex items-center gap-2 rounded-lg border border-teal-500/30 bg-teal-500/20 px-4 py-2 text-sm text-teal-300 disabled:opacity-50">
                {uploading ? <RefreshCw size={14} className="animate-spin" /> : <Upload size={14} />}{uploading ? `Uploading ${uploadProgress}%` : 'Choose file'}
              </button>
              {uploading && <button onClick={() => uploadController.current?.abort()} className="rounded-lg px-3 py-2 text-xs text-rose-300 hover:bg-rose-500/10">Cancel upload</button>}
              <div onDragOver={(event) => { event.preventDefault(); setDragging(true); }} onDragLeave={() => setDragging(false)} onDrop={(event) => { event.preventDefault(); setDragging(false); if (!uploading) handleUpload(event.dataTransfer.files?.[0]); }} className={`min-w-52 flex-1 rounded-lg border border-dashed px-3 py-2 text-center text-xs ${dragging ? 'border-teal-400 text-teal-300' : 'border-navy-600 text-slate-500'}`}>
                Drop a supported file here
              </div>
              <button onClick={fetchData} aria-label="Refresh datasets" className="rounded-lg p-2 text-slate-400 hover:bg-navy-700 hover:text-white"><RefreshCw size={15} /></button>
            </div>
            {uploading && <div className="mt-4 h-1.5 overflow-hidden rounded-full bg-navy-700"><div className="h-full bg-teal-400 transition-all" style={{ width: `${uploadProgress}%` }} /></div>}
          </>
        )}
      </section>

      {session && <section className="overflow-hidden rounded-xl border border-navy-600 bg-navy-800">
        <div className="flex items-center justify-between border-b border-navy-700 px-5 py-4">
          <div><h2 className="text-sm font-semibold text-white">Your dataset history</h2><p className="mt-1 text-xs text-slate-500">{datasets.length} datasets on this page</p></div>
          <button onClick={fetchData} aria-label="Refresh history" className="rounded-lg p-2 text-slate-400 hover:bg-navy-700 hover:text-white"><RefreshCw size={14} /></button>
        </div>
        {loading && datasets.length === 0 ? <LoadingSpinner /> : datasets.length === 0 ? (
          <div className="py-12 text-center text-sm text-slate-500"><FileText size={22} className="mx-auto mb-2 opacity-50" />No uploaded datasets yet.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead><tr className="border-b border-navy-700 text-xs uppercase text-slate-400">
                <th className="px-4 py-3">File</th><th className="px-4 py-3">Source</th><th className="px-4 py-3">Rows</th><th className="px-4 py-3">Status</th><th className="px-4 py-3">Uploaded</th><th className="px-4 py-3">Actions</th>
              </tr></thead>
              <tbody className="divide-y divide-navy-700">
                {datasets.map((dataset) => (
                  <tr key={dataset.id} className="hover:bg-navy-700/40">
                    <td className="max-w-xs truncate px-4 py-3 font-medium text-white">{dataset.original_filename}</td>
                    <td className="px-4 py-3 capitalize text-slate-300">{dataset.energy_source}</td>
                    <td className="px-4 py-3 font-mono text-slate-300">{dataset.total_records?.toLocaleString() || '—'}</td>
                    <td className="px-4 py-3"><StatusBadge status={dataset.processing_status} />{dataset.processing_error && <p className="mt-1 max-w-xs truncate text-xs text-rose-400" title={dataset.processing_error}>{dataset.processing_error}</p>}</td>
                    <td className="px-4 py-3 text-xs text-slate-500">{dataset.uploaded_at ? new Date(dataset.uploaded_at).toLocaleString() : '—'}</td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-1">
                        <button onClick={() => setDetailId(dataset.id)} title="Details and preview" className="rounded p-2 text-teal-300 hover:bg-navy-700"><FileText size={15} /></button>
                        <button onClick={() => handleDownload(dataset)} title="Download original" className="rounded p-2 text-slate-300 hover:bg-navy-700"><Download size={15} /></button>
                        {['completed', 'failed', 'cancelled'].includes(dataset.processing_status) && <button onClick={async () => { try { await triggerDatasetProcessing(dataset.id); await fetchData(); } catch (error) { notify(`Reprocess failed: ${errorMessage(error)}`, 'error'); } }} title="Reprocess" className="rounded p-2 text-violet-300 hover:bg-navy-700"><RefreshCw size={15} /></button>}
                        {(['queued', 'completed', 'failed', 'cancelled'].includes(dataset.processing_status)) && <button onClick={() => handleDelete(dataset)} title="Delete dataset" className="rounded p-2 text-rose-300 hover:bg-navy-700"><Trash2 size={15} /></button>}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>}

      {detailId && <DatasetDetails datasetId={detailId} onClose={() => setDetailId(null)} notify={notify} />}
    </div>
  );
}
