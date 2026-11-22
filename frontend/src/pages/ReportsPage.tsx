import React, { useState, useEffect } from 'react';
import { Download, FileText, Filter, CheckCircle2, Table, RefreshCw } from 'lucide-react';
import { Button } from '../components/ui/Button';
import { Card, CardContent, CardHeader } from '../components/ui/Card';
import { api } from '../services/api';
import { Category, ReportItem } from '../types';

interface ReportsPageProps {
  onNavigate: (page: string, params?: any) => void;
}

export const ReportsPage: React.FC<ReportsPageProps> = () => {
  const [categories, setCategories] = useState<Category[]>([]);
  const [selectedCategory, setSelectedCategory] = useState('');
  const [selectedPriority, setSelectedPriority] = useState('');
  const [selectedStatus, setSelectedStatus] = useState('');
  const [selectedArea, setSelectedArea] = useState('');
  
  const [previewReports, setPreviewReports] = useState<ReportItem[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    api.getCategories().then(setCategories).catch(() => {});
  }, []);

  useEffect(() => {
    loadPreview();
  }, [selectedCategory, selectedPriority, selectedStatus, selectedArea]);

  const loadPreview = async () => {
    setLoading(true);
    try {
      const res = await api.getAdminReports({
        category_id: selectedCategory || undefined,
        priority: selectedPriority || undefined,
        status: selectedStatus || undefined,
        area: selectedArea || undefined,
        limit: 10,
      });
      setPreviewReports(res.items);
      setTotalCount(res.total);
    } catch {
      // Handle error
    } finally {
      setLoading(false);
    }
  };

  const handleDownloadCsv = () => {
    const url = api.getExportUrl({
      category_id: selectedCategory || undefined,
      priority: selectedPriority || undefined,
      status: selectedStatus || undefined,
      area: selectedArea || undefined,
    });
    window.open(url, '_blank');
  };

  return (
    <div className="space-y-6 py-8">
      
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Municipal Reports & Data Exports</h1>
        <p className="text-xs text-slate-500 mt-1">
          Export filtered civic datasets for departmental audit, engineering work orders, and municipal business intelligence.
        </p>
      </div>

      {/* Filter and Export Options */}
      <Card>
        <CardHeader
          title="Export Configuration & Filtering"
          subtitle="Configure criteria to generate verified CSV and analytical reports"
          action={
            <Button
              variant="secondary"
              onClick={handleDownloadCsv}
              icon={<Download className="w-4 h-4" />}
            >
              Export Filtered CSV ({totalCount} Records)
            </Button>
          }
        />
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-4 gap-3">
            
            <div className="space-y-1">
              <label className="text-xs font-semibold text-slate-700">Filter by Category</label>
              <select
                value={selectedCategory}
                onChange={(e) => setSelectedCategory(e.target.value)}
                className="w-full text-xs border border-slate-300 rounded-lg px-3 py-2 bg-white focus:ring-2 focus:ring-teal-500"
              >
                <option value="">All Categories</option>
                {categories.map((c) => (
                  <option key={c.id} value={c.id}>{c.name}</option>
                ))}
              </select>
            </div>

            <div className="space-y-1">
              <label className="text-xs font-semibold text-slate-700">Filter by Priority</label>
              <select
                value={selectedPriority}
                onChange={(e) => setSelectedPriority(e.target.value)}
                className="w-full text-xs border border-slate-300 rounded-lg px-3 py-2 bg-white focus:ring-2 focus:ring-teal-500"
              >
                <option value="">All Priorities</option>
                <option value="Critical">Critical</option>
                <option value="High">High</option>
                <option value="Medium">Medium</option>
                <option value="Low">Low</option>
              </select>
            </div>

            <div className="space-y-1">
              <label className="text-xs font-semibold text-slate-700">Filter by Status</label>
              <select
                value={selectedStatus}
                onChange={(e) => setSelectedStatus(e.target.value)}
                className="w-full text-xs border border-slate-300 rounded-lg px-3 py-2 bg-white focus:ring-2 focus:ring-teal-500"
              >
                <option value="">All Statuses</option>
                <option value="Submitted">Submitted</option>
                <option value="Under Review">Under Review</option>
                <option value="Verified">Verified</option>
                <option value="Assigned">Assigned</option>
                <option value="In Progress">In Progress</option>
                <option value="Resolved">Resolved</option>
              </select>
            </div>

            <div className="space-y-1">
              <label className="text-xs font-semibold text-slate-700">Filter by Ward / Area</label>
              <select
                value={selectedArea}
                onChange={(e) => setSelectedArea(e.target.value)}
                className="w-full text-xs border border-slate-300 rounded-lg px-3 py-2 bg-white focus:ring-2 focus:ring-teal-500"
              >
                <option value="">All Municipal Wards</option>
                <option value="Koramangala">Koramangala</option>
                <option value="Indiranagar">Indiranagar</option>
                <option value="Whitefield">Whitefield</option>
                <option value="HSR Layout">HSR Layout</option>
                <option value="CBD / Central">CBD / Central</option>
                <option value="Jayanagar">Jayanagar</option>
                <option value="Malleshwaram">Malleshwaram</option>
              </select>
            </div>

          </div>
        </CardContent>
      </Card>

      {/* Dataset Preview */}
      <Card>
        <CardHeader
          title={`Dataset Preview (Showing 10 of ${totalCount} matched records)`}
          subtitle="Real-time synchronized data from database records"
          icon={<Table className="w-5 h-5 text-slate-600" />}
        />
        <CardContent>
          <div className="overflow-x-auto rounded-lg border border-slate-200">
            <table className="w-full text-left text-xs border-collapse">
              <thead className="bg-slate-50 border-b border-slate-200 text-slate-600 font-semibold uppercase tracking-wider">
                <tr>
                  <th className="px-4 py-2.5">Tracking Number</th>
                  <th className="px-4 py-2.5">Title</th>
                  <th className="px-4 py-2.5">Category</th>
                  <th className="px-4 py-2.5">Priority</th>
                  <th className="px-4 py-2.5">Status</th>
                  <th className="px-4 py-2.5">Ward / Area</th>
                  <th className="px-4 py-2.5">Submission Date</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-slate-700">
                {loading ? (
                  <tr>
                    <td colSpan={7} className="text-center py-6 text-slate-400">Loading preview...</td>
                  </tr>
                ) : previewReports.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="text-center py-6 text-slate-400">No records match filter criteria.</td>
                  </tr>
                ) : (
                  previewReports.map((r) => (
                    <tr key={r.id} className="hover:bg-slate-50/80">
                      <td className="px-4 py-2.5 font-mono font-bold text-slate-900">#{r.tracking_number}</td>
                      <td className="px-4 py-2.5 font-medium text-slate-900 max-w-xs truncate">{r.title}</td>
                      <td className="px-4 py-2.5">{r.verified_category || r.category}</td>
                      <td className="px-4 py-2.5 font-semibold text-slate-800">{r.priority_level} ({Math.round(r.priority_score)})</td>
                      <td className="px-4 py-2.5">{r.status}</td>
                      <td className="px-4 py-2.5">{r.area || 'Bengaluru'}</td>
                      <td className="px-4 py-2.5 text-slate-500">{new Date(r.created_at).toLocaleDateString()}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

    </div>
  );
};
