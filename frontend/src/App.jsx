import React, { useState } from 'react';
import { BrowserRouter, Routes, Route, NavLink, useLocation } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  LayoutDashboard, Sun, Wind, Droplets, Flame, Leaf,
  AlertTriangle, CloudSun, Globe, Zap, Database,
  FileText, Server, ChevronLeft, ChevronRight, Activity
} from 'lucide-react';
import Dashboard from './pages/Dashboard.jsx';
import SolarPage from './pages/SolarPage.jsx';
import WindPage from './pages/WindPage.jsx';
import HydroPage from './pages/HydroPage.jsx';
import GeothermalPage from './pages/GeothermalPage.jsx';
import BiomassPage from './pages/BiomassPage.jsx';
import AnomaliesPage from './pages/AnomaliesPage.jsx';
import WeatherPage from './pages/WeatherPage.jsx';
import GlobalEnergyPage from './pages/GlobalEnergyPage.jsx';
import SparkJobsPage from './pages/SparkJobsPage.jsx';
import DatasetsPage from './pages/DatasetsPage.jsx';
import ReportsPage from './pages/ReportsPage.jsx';
import SourcesPage from './pages/SourcesPage.jsx';

const NAV_SECTIONS = [
  {
    label: 'Overview',
    items: [
      { to: '/', icon: LayoutDashboard, label: 'Dashboard', end: true },
    ],
  },
  {
    label: 'Energy Sources',
    items: [
      { to: '/solar', icon: Sun, label: 'Solar Energy', color: 'text-amber-400' },
      { to: '/wind', icon: Wind, label: 'Wind Energy', color: 'text-blue-400' },
      { to: '/hydro', icon: Droplets, label: 'Hydropower', color: 'text-cyan-400' },
      { to: '/geothermal', icon: Flame, label: 'Geothermal', color: 'text-orange-400' },
      { to: '/biomass', icon: Leaf, label: 'Biomass', color: 'text-emerald-400' },
    ],
  },
  {
    label: 'Monitoring',
    items: [
      { to: '/anomalies', icon: AlertTriangle, label: 'Anomalies', color: 'text-rose-400' },
      { to: '/weather', icon: CloudSun, label: 'Weather', color: 'text-sky-400' },
      { to: '/spark', icon: Zap, label: 'Spark Jobs', color: 'text-violet-400' },
    ],
  },
  {
    label: 'Data & Reports',
    items: [
      { to: '/global', icon: Globe, label: 'Global Energy', color: 'text-indigo-400' },
      { to: '/datasets', icon: Database, label: 'Datasets', color: 'text-teal-400' },
      { to: '/sources', icon: Server, label: 'Data Sources', color: 'text-pink-400' },
      { to: '/reports', icon: FileText, label: 'Reports', color: 'text-lime-400' },
    ],
  },
];

function Sidebar({ collapsed, onToggle }) {
  const location = useLocation();
  return (
    <motion.aside
      animate={{ width: collapsed ? 64 : 240 }}
      transition={{ duration: 0.25, ease: 'easeInOut' }}
      className="fixed inset-y-0 left-0 z-30 bg-navy-900 border-r border-navy-700 flex flex-col overflow-hidden"
    >
      {/* Logo */}
      <div className="flex items-center gap-3 px-4 py-4 border-b border-navy-700 min-h-[64px]">
        <div className="flex-shrink-0 p-1.5 rounded-lg bg-emerald-500/20 border border-emerald-500/30">
          <Activity size={18} className="text-emerald-400" />
        </div>
        <AnimatePresence>
          {!collapsed && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.15 }}
              className="overflow-hidden"
            >
              <p className="text-xs font-bold text-white leading-tight whitespace-nowrap">REIP</p>
              <p className="text-[9px] text-emerald-400 leading-tight whitespace-nowrap">Energy Intelligence</p>
            </motion.div>
          )}
        </AnimatePresence>
        <button
          onClick={onToggle}
          className="ml-auto flex-shrink-0 p-1 rounded text-slate-500 hover:text-white hover:bg-navy-700 transition-colors"
        >
          {collapsed ? <ChevronRight size={14} /> : <ChevronLeft size={14} />}
        </button>
      </div>

      {/* Nav */}
      <nav className="flex-1 overflow-y-auto py-3 px-2 space-y-1">
        {NAV_SECTIONS.map((section) => (
          <div key={section.label} className="mb-3">
            {!collapsed && (
              <p className="px-2 pb-1 text-[10px] font-semibold text-slate-500 uppercase tracking-widest">{section.label}</p>
            )}
            {section.items.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.end}
                className={({ isActive }) =>
                  `flex items-center gap-3 px-2 py-2 rounded-lg text-sm transition-all duration-150 ${
                    isActive
                      ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/20'
                      : 'text-slate-400 hover:bg-navy-700 hover:text-white border border-transparent'
                  }`
                }
                title={collapsed ? item.label : ''}
              >
                <item.icon size={16} className={`flex-shrink-0 ${item.color || ''}`} />
                {!collapsed && (
                  <span className="whitespace-nowrap overflow-hidden text-ellipsis">{item.label}</span>
                )}
              </NavLink>
            ))}
          </div>
        ))}
      </nav>

      {/* Footer */}
      <div className="px-3 py-3 border-t border-navy-700">
        {!collapsed && (
          <p className="text-[9px] text-slate-600 leading-relaxed">
            Apache Spark RDD · Supabase · Open-Meteo · NASA POWER · OWID
          </p>
        )}
      </div>
    </motion.aside>
  );
}

function AppShell() {
  const [collapsed, setCollapsed] = useState(false);
  const location = useLocation();
  const sidebarWidth = collapsed ? 64 : 240;

  return (
    <div className="min-h-screen bg-navy-950 text-white">
      <Sidebar collapsed={collapsed} onToggle={() => setCollapsed(c => !c)} />
      <motion.main
        animate={{ marginLeft: sidebarWidth }}
        transition={{ duration: 0.25, ease: 'easeInOut' }}
        className="min-h-screen"
      >
        <AnimatePresence mode="wait">
          <motion.div
            key={location.pathname}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.2 }}
          >
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/solar" element={<SolarPage />} />
              <Route path="/wind" element={<WindPage />} />
              <Route path="/hydro" element={<HydroPage />} />
              <Route path="/geothermal" element={<GeothermalPage />} />
              <Route path="/biomass" element={<BiomassPage />} />
              <Route path="/anomalies" element={<AnomaliesPage />} />
              <Route path="/weather" element={<WeatherPage />} />
              <Route path="/global" element={<GlobalEnergyPage />} />
              <Route path="/spark" element={<SparkJobsPage />} />
              <Route path="/datasets" element={<DatasetsPage />} />
              <Route path="/sources" element={<SourcesPage />} />
              <Route path="/reports" element={<ReportsPage />} />
            </Routes>
          </motion.div>
        </AnimatePresence>
      </motion.main>
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AppShell />
    </BrowserRouter>
  );
}
