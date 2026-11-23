import React, { useState, useEffect } from 'react';
import {
  FileText, AlertTriangle, CheckCircle2, Clock, MapPin,
  TrendingUp, Layers, Filter, RefreshCw, Download, ArrowUpRight,
  ShieldAlert, Activity, RotateCcw
} from 'lucide-react';
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, LineChart, Line, CartesianGrid, Legend
} from 'recharts';
import { Button } from '../components/ui/Button';
import { Card, CardContent, CardHeader, StatCard } from '../components/ui/Card';
import { api } from '../services/api';
import { OverviewKPIs, ChartData, Category } from '../types';
import { useToast } from '../context/ToastContext';

interface AdminDashboardProps {
  onNavigate: (page: string, params?: any) => void;
}

export const AdminDashboard: React.FC<AdminDashboardProps> = ({ onNavigate }) => {
  const { showToast } = useToast();
  const [kpis, setKpis] = useState<OverviewKPIs | null>(null);
  const [charts, setCharts] = useState<ChartData | null>(null);
  const [categories, setCategories] = useState<Category[]>([]);
  const [loading, setLoading] = useState(true);
  const [resetting, setResetting] = useState(false);

  // Filters
  const [selectedCategory, setSelectedCategory] = useState<string>('');
  const [selectedPriority, setSelectedPriority] = useState<string>('');
  const [selectedArea, setSelectedArea] = useState<string>('');
  const [selectedDays, setSelectedDays] = useState<number | undefined>(undefined);

  useEffect(() => {
    api.getCategories().then(setCategories).catch(() => {});
  }, []);

  useEffect(() => {
    loadDashboardData();
  }, [selectedCategory, selectedPriority, selectedArea, selectedDays]);

  const loadDashboardData = async () => {
    setLoading(true);
    try {
      const filterParams = {
        category_id: selectedCategory || undefined,
        priority: selectedPriority || undefined,
        area: selectedArea || undefined,
        days: selectedDays || undefined,
      };

      const [kpiData, chartData] = await Promise.all([
        api.getKPIs(filterParams),
        api.getCharts(filterParams),
      ]);

      setKpis(kpiData);
      setCharts(chartData);
    } catch (e) {
      // Handle error
    } finally {
      setLoading(false);
    }
  };

  const handleResetDemo = async () => {
    if (!window.confirm("Reset demo dataset? This will restore the 140+ realistic Bengaluru test civic reports and duplicate clusters.")) {
      return;
    }
    setResetting(true);
    try {
      await api.resetDemoData();
      showToast('success', 'Demo Dataset Reseeded', 'Restored 140+ Bengaluru reports, departments, and duplicate clusters.');
      await loadDashboardData();
    } catch (err: any) {
      showToast('error', 'Reset Failed', err.message || 'Could not reset demo dataset.');
    } finally {
      setResetting(false);
    }
  };

  const PRIORITY_COLORS: Record<string, string> = {
    Critical: '#ef4444',
    High: '#f97316',
    Medium: '#eab308',
    Low: '#22c55e',
  };

  return (
    <div className="space-y-8 py-8">
      
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse" />
            <span className="text-xs font-semibold text-emerald-600 uppercase tracking-wider">Live Municipal Dispatch Active</span>
          </div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight mt-0.5">Municipal Operations Control Center</h1>
          <p className="text-xs text-slate-500">Real-time civic telemetry, computer vision defect triage, and departmental workload distribution</p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={handleResetDemo}
            loading={resetting}
            icon={<RotateCcw className="w-3.5 h-3.5 text-amber-600" />}
            title="Reset database to fresh Bengaluru demo test dataset"
          >
            Reset Demo Data
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={loadDashboardData}
            icon={<RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />}
          >
            Refresh
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => onNavigate('map')}
            icon={<MapPin className="w-3.5 h-3.5 text-teal-600" />}
          >
            Live GIS Map
          </Button>
          <Button
            variant="primary"
            size="sm"
            onClick={() => onNavigate('issue-management')}
            icon={<FileText className="w-3.5 h-3.5" />}
          >
            Manage Issue Ledger
          </Button>
        </div>
      </div>

      {/* Filter Bar */}
      <Card className="bg-slate-50 border-slate-200">
        <CardContent className="p-4">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div className="flex items-center gap-2 text-xs font-semibold text-slate-700">
              <Filter className="w-4 h-4 text-slate-500" />
              <span>Operational Filters:</span>
            </div>

            <div className="flex flex-wrap items-center gap-3">
              {/* Category Filter */}
              <select
                aria-label="Filter by Category"
                value={selectedCategory}
                onChange={(e) => setSelectedCategory(e.target.value)}
                className="text-xs border border-slate-300 rounded-lg px-3 py-1.5 bg-white focus:ring-2 focus:ring-teal-500"
              >
                <option value="">All Categories</option>
                {categories.map((c) => (
                  <option key={c.id} value={c.id}>{c.name}</option>
                ))}
              </select>

              {/* Priority Filter */}
              <select
                aria-label="Filter by Priority"
                value={selectedPriority}
                onChange={(e) => setSelectedPriority(e.target.value)}
                className="text-xs border border-slate-300 rounded-lg px-3 py-1.5 bg-white focus:ring-2 focus:ring-teal-500"
              >
                <option value="">All Priorities</option>
                <option value="Critical">Critical</option>
                <option value="High">High</option>
                <option value="Medium">Medium</option>
                <option value="Low">Low</option>
              </select>

              {/* Area Filter */}
              <select
                aria-label="Filter by Municipal Ward"
                value={selectedArea}
                onChange={(e) => setSelectedArea(e.target.value)}
                className="text-xs border border-slate-300 rounded-lg px-3 py-1.5 bg-white focus:ring-2 focus:ring-teal-500"
              >
                <option value="">All Municipal Wards</option>
                <option value="Koramangala">Koramangala</option>
                <option value="Indiranagar">Indiranagar</option>
                <option value="Whitefield">Whitefield</option>
                <option value="HSR Layout">HSR Layout</option>
                <option value="CBD / Central">CBD / Central</option>
                <option value="Jayanagar">Jayanagar</option>
                <option value="Malleshwaram">Malleshwaram</option>
                <option value="Electronic City">Electronic City</option>
                <option value="Hebbal">Hebbal</option>
              </select>

              {/* Date Filter */}
              <select
                aria-label="Filter by Time Period"
                value={selectedDays || ''}
                onChange={(e) => setSelectedDays(e.target.value ? parseInt(e.target.value) : undefined)}
                className="text-xs border border-slate-300 rounded-lg px-3 py-1.5 bg-white focus:ring-2 focus:ring-teal-500"
              >
                <option value="">All Time</option>
                <option value="7">Last 7 Days</option>
                <option value="14">Last 14 Days</option>
                <option value="30">Last 30 Days</option>
              </select>

              {(selectedCategory || selectedPriority || selectedArea || selectedDays) && (
                <button
                  onClick={() => {
                    setSelectedCategory('');
                    setSelectedPriority('');
                    setSelectedArea('');
                    setSelectedDays(undefined);
                  }}
                  className="text-xs text-red-600 hover:text-red-700 font-semibold underline"
                >
                  Clear Filters
                </button>
              )}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 8 Primary Calculated KPI Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard
          title="Total Reports"
          value={kpis?.total_reports ?? 0}
          subtitle="Database records indexed"
          icon={<FileText className="w-5 h-5 text-blue-600" />}
          accentColor="bg-blue-50 text-blue-600"
        />
        <StatCard
          title="Active Open Issues"
          value={kpis?.open_reports ?? 0}
          subtitle="Requiring remediation"
          icon={<Clock className="w-5 h-5 text-amber-600" />}
          accentColor="bg-amber-50 text-amber-600"
        />
        <StatCard
          title="Critical Safety Hazards"
          value={kpis?.critical_reports ?? 0}
          subtitle="Immediate dispatch priority"
          icon={<AlertTriangle className="w-5 h-5 text-red-600" />}
          accentColor="bg-red-50 text-red-600"
        />
        <StatCard
          title="Resolved Tickets"
          value={kpis?.resolved_reports ?? 0}
          subtitle={`Resolution rate: ${kpis?.resolution_rate_percent ?? 0}%`}
          icon={<CheckCircle2 className="w-5 h-5 text-emerald-600" />}
          accentColor="bg-emerald-50 text-emerald-600"
        />
        <StatCard
          title="Avg Turnaround Time"
          value={`${kpis?.avg_resolution_time_days ?? 1.6}d`}
          subtitle={`${kpis?.avg_resolution_time_hours ?? 38} hrs benchmark SLA`}
          icon={<Activity className="w-5 h-5 text-indigo-600" />}
          accentColor="bg-indigo-50 text-indigo-600"
        />
        <StatCard
          title="Recent 7-Day Volume"
          value={kpis?.recent_7_days_reports ?? 0}
          subtitle="Fresh citizen submissions"
          icon={<TrendingUp className="w-5 h-5 text-teal-600" />}
          accentColor="bg-teal-50 text-teal-600"
        />
        <StatCard
          title="Duplicate Clusters"
          value={kpis?.duplicate_reports_detected ?? 0}
          subtitle={`${kpis?.confirmed_duplicates ?? 0} confirmed merges`}
          icon={<Layers className="w-5 h-5 text-purple-600" />}
          accentColor="bg-purple-50 text-purple-600"
        />
        <StatCard
          title="Resolution Efficiency"
          value={`${kpis?.resolution_rate_percent ?? 0}%`}
          subtitle="Inspected & closed"
          icon={<CheckCircle2 className="w-5 h-5 text-teal-600" />}
          accentColor="bg-teal-50 text-teal-600"
        />
      </div>

      {/* Interactive Charts Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        
        {/* Chart 1: 14-Day Ingestion vs Resolution Timeline */}
        <Card>
          <CardHeader
            title="Ingestion vs Resolution Timeline"
            subtitle="Daily volume of citizen submissions vs completed remediations"
          />
          <CardContent>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={charts?.timeline_trend || []}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                  <XAxis dataKey="date" stroke="#64748b" fontSize={11} />
                  <YAxis stroke="#64748b" fontSize={11} />
                  <Tooltip
                    contentStyle={{ backgroundColor: '#ffffff', borderColor: '#e2e8f0', borderRadius: '8px', fontSize: '12px' }}
                  />
                  <Legend wrapperStyle={{ fontSize: '12px' }} />
                  <Line type="monotone" dataKey="submitted" name="Submitted" stroke="#0f172a" strokeWidth={2} dot={{ r: 3 }} />
                  <Line type="monotone" dataKey="resolved" name="Resolved" stroke="#0d9488" strokeWidth={2} dot={{ r: 3 }} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>

        {/* Chart 2: Issues by Category */}
        <Card>
          <CardHeader
            title="Defect Distribution by Category"
            subtitle="Volume distribution of reported infrastructure issues"
          />
          <CardContent>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={charts?.issues_by_category || []} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                  <XAxis type="number" stroke="#64748b" fontSize={11} />
                  <YAxis dataKey="category" type="category" width={110} stroke="#64748b" fontSize={10} tickFormatter={(v) => v.length > 14 ? `${v.substring(0, 14)}...` : v} />
                  <Tooltip
                    contentStyle={{ backgroundColor: '#ffffff', borderColor: '#e2e8f0', borderRadius: '8px', fontSize: '12px' }}
                  />
                  <Bar dataKey="count" name="Issues" fill="#0d9488" radius={[0, 4, 4, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>

        {/* Chart 3: Issues by Priority Breakdown */}
        <Card>
          <CardHeader
            title="Priority Tier Breakdown"
            subtitle="Automated 5-factor priority classification (Critical, High, Medium, Low)"
          />
          <CardContent>
            <div className="h-64 flex items-center justify-center">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={charts?.issues_by_priority || []}
                    cx="50%"
                    cy="50%"
                    innerRadius={50}
                    outerRadius={80}
                    paddingAngle={4}
                    dataKey="count"
                    nameKey="priority"
                  >
                    {(charts?.issues_by_priority || []).map((entry) => (
                      <Cell key={entry.priority} fill={PRIORITY_COLORS[entry.priority] || '#94a3b8'} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{ backgroundColor: '#ffffff', borderColor: '#e2e8f0', borderRadius: '8px', fontSize: '12px' }}
                  />
                  <Legend wrapperStyle={{ fontSize: '12px' }} />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>

        {/* Chart 4: Average Resolution Time by Category */}
        <Card>
          <CardHeader
            title="Turnaround Time by Category"
            subtitle="Average hours to inspect, repair, and verify resolution"
          />
          <CardContent>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={charts?.avg_time_by_category || []}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                  <XAxis dataKey="category" stroke="#64748b" fontSize={10} tickFormatter={(v) => v.split(' ')[0]} />
                  <YAxis stroke="#64748b" fontSize={11} unit="h" />
                  <Tooltip
                    formatter={(val) => [`${val} hours`, 'Avg Turnaround']}
                    contentStyle={{ backgroundColor: '#ffffff', borderColor: '#e2e8f0', borderRadius: '8px', fontSize: '12px' }}
                  />
                  <Bar dataKey="avg_hours" name="Avg Hours" fill="#6366f1" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>

      </div>

      {/* Repeated Issues & Hotspots Table */}
      <Card>
        <CardHeader
          title="Geographic Issue Concentration & High-Density Wards"
          subtitle="Municipal sectors requiring strategic asphalt resurfacing and enhanced drainage allocation"
          action={
            <Button variant="outline" size="sm" onClick={() => onNavigate('map')}>
              Open GIS Map View →
            </Button>
          }
        />
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {(charts?.repeated_locations || []).map((loc) => (
              <div key={loc.area} className="p-4 rounded-xl border border-slate-200 bg-slate-50 flex items-center justify-between">
                <div>
                  <div className="font-semibold text-sm text-slate-900">{loc.area}</div>
                  <div className="text-xs text-slate-500 mt-0.5">High reporting density sector</div>
                </div>
                <div className="text-right">
                  <div className="text-xl font-bold text-slate-900">{loc.count}</div>
                  <div className="text-[10px] text-slate-400 uppercase font-semibold">Reports</div>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

    </div>
  );
};
