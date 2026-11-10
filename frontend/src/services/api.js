import axios from 'axios';
import { supabase } from '../lib/supabase.js';

const API_BASE = '/api';

const api = axios.create({
  baseURL: API_BASE,
  timeout: 45000,
  headers: {
    'Content-Type': 'application/json',
  },
});

api.interceptors.request.use(async (config) => {
  const { data, error } = await supabase.auth.getSession();
  if (error) throw error;
  const accessToken = data.session?.access_token;
  if (accessToken) config.headers.Authorization = `Bearer ${accessToken}`;
  if (typeof FormData !== 'undefined' && config.data instanceof FormData) {
    if (typeof config.headers.delete === 'function') {
      config.headers.delete('Content-Type');
    } else {
      delete config.headers['Content-Type'];
    }
  }
  return config;
});

export const getOverviewKpis = async () => {
  const res = await api.get('/analytics/overview');
  return res.data;
};

export const getPlants = async (energySource = null) => {
  const params = energySource ? { energy_source: energySource } : {};
  const res = await api.get('/plants', { params });
  return res.data;
};

export const getPlantDetail = async (plantId) => {
  const res = await api.get(`/plants/${plantId}`);
  return res.data;
};

export const getSourceAnalytics = async (energySource, plantId = null) => {
  const params = plantId ? { plant_id: plantId } : {};
  const res = await api.get(`/analytics/${energySource}`, { params });
  return res.data;
};

export const getGenerationForecast = async (plantId = null) => {
  const params = plantId ? { plant_id: plantId } : {};
  const res = await api.get('/analytics/advanced/forecasting', { params });
  return res.data;
};

export const getCarbonAvoidance = async () => {
  const res = await api.get('/analytics/advanced/carbon-avoidance');
  return res.data;
};

export const getCurrentWeather = async (plantId = null) => {
  const params = plantId ? { plant_id: plantId } : {};
  const res = await api.get('/weather/current', { params });
  return res.data;
};

export const getWeatherForecast = async (plantId = null, hours = 24) => {
  const params = { hours };
  if (plantId) params.plant_id = plantId;
  const res = await api.get('/weather/forecast', { params });
  return res.data;
};

export const getWeatherHistory = async (plantId = null, limit = 30) => {
  const params = { limit };
  if (plantId) params.plant_id = plantId;
  const res = await api.get('/weather/history', { params });
  return res.data;
};

export const getOwidCountries = async () => {
  const res = await api.get('/global-energy/countries');
  return res.data;
};

export const getOwidGeneration = async (isoCode = null, year = null, limit = 50) => {
  const params = { limit };
  if (isoCode) params.iso_code = isoCode;
  if (year) params.year = year;
  const res = await api.get('/global-energy/generation', { params });
  return res.data;
};

export const getIndiaVsWorld = async () => {
  const res = await api.get('/global-energy/india-vs-world');
  return res.data;
};

export const getAnomalies = async (status = null, severity = null, energySource = null, plantId = null) => {
  const params = { limit: 200 };
  if (status) params.status = status;
  if (severity) params.severity = severity;
  if (energySource) params.energy_source = energySource;
  if (plantId) params.plant_id = plantId;
  const res = await api.get('/anomalies', { params });
  return res.data;
};

export const updateAnomalyStatus = async (anomalyId, status, resolutionNotes = '') => {
  const res = await api.patch(`/anomalies/${anomalyId}/status`, {
    status,
    resolution_notes: resolutionNotes,
  });
  return res.data;
};

export const getSparkJobs = async (limit = 25) => {
  const res = await api.get('/spark/jobs', { params: { limit } });
  return res.data;
};

export const getSparkMetrics = async () => {
  const res = await api.get('/spark/metrics');
  return res.data;
};

export const getDatasets = async (energySource = null, limit = 100, offset = 0) => {
  const params = { limit, offset };
  if (energySource) params.energy_source = energySource;
  const res = await api.get('/datasets', { params });
  return res.data;
};

export const getDataset = async (datasetId) => {
  const res = await api.get(`/datasets/${datasetId}`);
  return res.data;
};

export const getDatasetStatus = async (datasetId) => {
  const res = await api.get(`/datasets/${datasetId}/status`);
  return res.data;
};

export const getDatasetPreview = async (datasetId, limit = 50, offset = 0, classification = null) => {
  const params = { limit, offset };
  if (classification) params.classification = classification;
  const res = await api.get(`/datasets/${datasetId}/preview`, { params });
  return res.data;
};

export const getDatasetAnalytics = async (datasetId) => {
  const res = await api.get(`/datasets/${datasetId}/analytics`);
  return res.data;
};

export const getDatasetVisualizations = async (datasetId) => {
  const res = await api.get(`/datasets/${datasetId}/visualizations`);
  return res.data;
};

export const downloadDataset = async (datasetId) => {
  const res = await api.get(`/datasets/${datasetId}/download`, { responseType: 'blob' });
  return res.data;
};

export const deleteDataset = async (datasetId) => {
  await api.delete(`/datasets/${datasetId}`);
};

export const uploadDatasetFile = async (formData, options = {}) => {
  const res = await api.post('/datasets/upload', formData, {
    timeout: 180000,
    signal: options.signal,
    onUploadProgress: options.onUploadProgress,
  });
  return res.data;
};

export const triggerDatasetProcessing = async (datasetId) => {
  const res = await api.post(`/datasets/${datasetId}/process`);
  return res.data;
};

export const cancelDatasetProcessing = async (datasetId) => {
  const res = await api.post(`/datasets/${datasetId}/cancel`);
  return res.data;
};

export const processSampleDataset = async (energySource, plantId = null) => {
  const params = { energy_source: energySource };
  if (plantId) params.plant_id = plantId;
  const res = await api.post('/datasets/process-sample', null, { params });
  return res.data;
};

export const syncNasaPower = async (data) => {
  const res = await api.post('/sources/nasa-power/sync', data);
  return res.data;
};

export const syncOwid = async (data = {}) => {
  const res = await api.post('/sources/owid/sync', data);
  return res.data;
};

export const syncOpenMeteo = async (data) => {
  const res = await api.post('/sources/open-meteo/sync', data);
  return res.data;
};

export const getDataSources = async () => {
  const res = await api.get('/sources/status');
  return res.data;
};

export const getSourceMetadata = async () => {
  const res = await api.get('/sources/metadata');
  return res.data;
};

export const getReportTypes = async () => {
  const res = await api.get('/reports/overview');
  return res.data;
};

export const generateReport = async (reportType, exportFormat = 'json', plantId = null) => {
  if (exportFormat === 'csv') {
    const res = await api.post(
      '/reports/generate',
      { report_type: reportType, export_format: 'csv', plant_id: plantId },
      { responseType: 'blob' }
    );
    return res.data;
  }
  const res = await api.post('/reports/generate', {
    report_type: reportType,
    export_format: 'json',
    plant_id: plantId,
  });
  return res.data;
};

export default api;
