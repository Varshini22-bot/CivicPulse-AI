import React, { useState, useEffect } from 'react';
import {
  FileText, Clock, CheckCircle2, AlertCircle, PlusCircle,
  Search, Filter, MapPin, Eye, Trash2, ArrowUpRight
} from 'lucide-react';
import { Button } from '../components/ui/Button';
import { Card, CardContent, CardHeader, StatCard } from '../components/ui/Card';
import { PriorityBadge, StatusBadge, CategoryBadge } from '../components/ui/Badge';
import { Modal } from '../components/ui/Modal';
import { api } from '../services/api';
import { ReportItem } from '../types';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';

interface CitizenDashboardProps {
  onNavigate: (page: string, params?: any) => void;
}

export const CitizenDashboard: React.FC<CitizenDashboardProps> = ({ onNavigate }) => {
  const { user } = useAuth();
  const { showToast } = useToast();
  const [reports, setReports] = useState<ReportItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('ALL');
  
  // Withdrawal modal state
  const [selectedWithdrawId, setSelectedWithdrawId] = useState<string | null>(null);
  const [withdrawing, setWithdrawing] = useState(false);

  useEffect(() => {
    loadReports();
  }, []);

  const loadReports = async () => {
    setLoading(true);
    try {
      const data = await api.getMyReports();
      setReports(data);
    } catch {
      showToast('error', 'Error Loading Grievances', 'Could not load your submitted reports.');
    } finally {
      setLoading(false);
    }
  };

  const handleWithdraw = async () => {
    if (!selectedWithdrawId) return;
    setWithdrawing(true);
    try {
      await api.withdrawReport(selectedWithdrawId);
      setSelectedWithdrawId(null);
      showToast('info', 'Report Withdrawn', 'Your grievance report has been withdrawn.');
      await loadReports();
    } catch (e: any) {
      showToast('error', 'Withdrawal Failed', e.message || 'Could not withdraw report.');
    } finally {
      setWithdrawing(false);
    }
  };

  const totalReports = reports.length;
  const underReview = reports.filter(r => ['Submitted', 'Under Review'].includes(r.status)).length;
  const inProgress = reports.filter(r => ['Verified', 'Assigned', 'In Progress'].includes(r.status)).length;
  const resolved = reports.filter(r => r.status === 'Resolved').length;

  const filteredReports = reports.filter((r) => {
    const matchesSearch =
      r.title.toLowerCase().includes(search.toLowerCase()) ||
      r.tracking_number.toLowerCase().includes(search.toLowerCase()) ||
      (r.address && r.address.toLowerCase().includes(search.toLowerCase()));
    const matchesStatus = statusFilter === 'ALL' || r.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  return (
    <div className="space-y-8 py-8">
      
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Citizen Grievance Portal</h1>
          <p className="text-xs text-slate-500 mt-1">
            Welcome back, {user?.full_name || 'Citizen'}. Track live triage, departmental dispatch, and resolution proof for your reports.
          </p>
        </div>
        <Button
          variant="secondary"
          onClick={() => onNavigate('report-issue')}
          icon={<PlusCircle className="w-4 h-4" />}
        >
          Submit New Issue
        </Button>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Total Reports"
          value={totalReports}
          subtitle="Submitted across all wards"
          icon={<FileText className="w-5 h-5 text-blue-600" />}
          accentColor="bg-blue-50 text-blue-600"
        />
        <StatCard
          title="Under Review"
          value={underReview}
          subtitle="AI triage & validation"
          icon={<Clock className="w-5 h-5 text-purple-600" />}
          accentColor="bg-purple-50 text-purple-600"
        />
        <StatCard
          title="In Remediation"
          value={inProgress}
          subtitle="Assigned to municipal crews"
          icon={<AlertCircle className="w-5 h-5 text-amber-600" />}
          accentColor="bg-amber-50 text-amber-600"
        />
        <StatCard
          title="Resolved"
          value={resolved}
          subtitle="Completed with evidence"
          icon={<CheckCircle2 className="w-5 h-5 text-emerald-600" />}
          accentColor="bg-emerald-50 text-emerald-600"
        />
      </div>

      {/* Reports Table Card */}
      <Card>
        <CardHeader
          title="Your Submitted Reports"
          subtitle="Real-time status updates directly synchronized with BBMP / BWSSB / BESCOM work orders"
        />
        <CardContent className="space-y-4">
          
          {/* Filter Bar */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div className="relative max-w-sm w-full">
              <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5 pointer-events-none" />
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search by ID, title, or landmark..."
                className="w-full pl-9 pr-3 py-1.5 text-xs border border-slate-300 rounded-lg focus:ring-2 focus:ring-teal-500 focus:outline-hidden"
              />
            </div>

            <div className="flex items-center gap-2">
              <Filter className="w-3.5 h-3.5 text-slate-500" />
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="text-xs border border-slate-300 rounded-lg px-2.5 py-1.5 bg-white focus:ring-2 focus:ring-teal-500"
              >
                <option value="ALL">All Statuses</option>
                <option value="Submitted">Submitted</option>
                <option value="Under Review">Under Review</option>
                <option value="Verified">Verified</option>
                <option value="Assigned">Assigned</option>
                <option value="In Progress">In Progress</option>
                <option value="Resolved">Resolved</option>
              </select>
            </div>
          </div>

          {/* Table */}
          <div className="overflow-x-auto rounded-lg border border-slate-200">
            <table className="w-full text-left text-xs border-collapse">
              <thead className="bg-slate-50 border-b border-slate-200 text-slate-600 font-semibold uppercase tracking-wider">
                <tr>
                  <th className="px-4 py-3">Tracking ID</th>
                  <th className="px-4 py-3">Issue Title</th>
                  <th className="px-4 py-3">Category</th>
                  <th className="px-4 py-3">Priority</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3">Location</th>
                  <th className="px-4 py-3">Date</th>
                  <th className="px-4 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-slate-700">
                {loading ? (
                  <tr>
                    <td colSpan={8} className="text-center py-8 text-slate-400">Loading reports...</td>
                  </tr>
                ) : filteredReports.length === 0 ? (
                  <tr>
                    <td colSpan={8} className="text-center py-8 text-slate-400">
                      No matching civic reports found. Submit an issue using the button above.
                    </td>
                  </tr>
                ) : (
                  filteredReports.map((r) => (
                    <tr key={r.id} className="hover:bg-slate-50/80 transition-colors">
                      <td className="px-4 py-3 font-mono font-bold text-slate-900">
                        #{r.tracking_number}
                      </td>
                      <td className="px-4 py-3 font-medium text-slate-900 max-w-xs truncate">
                        {r.title}
                      </td>
                      <td className="px-4 py-3">
                        <CategoryBadge category={r.category} />
                      </td>
                      <td className="px-4 py-3">
                        <PriorityBadge level={r.priority_level} score={Math.round(r.priority_score)} />
                      </td>
                      <td className="px-4 py-3">
                        <StatusBadge status={r.status} />
                      </td>
                      <td className="px-4 py-3 text-slate-500 max-w-[150px] truncate">
                        {r.area || 'Bengaluru'}
                      </td>
                      <td className="px-4 py-3 text-slate-500 whitespace-nowrap">
                        {new Date(r.created_at).toLocaleDateString()}
                      </td>
                      <td className="px-4 py-3 text-right space-x-2 whitespace-nowrap">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => onNavigate('issue-details', { reportId: r.id })}
                          icon={<Eye className="w-3.5 h-3.5 text-slate-600" />}
                        >
                          Details
                        </Button>
                        {!['In Progress', 'Resolved', 'Rejected'].includes(r.status) && (
                          <Button
                            variant="ghost"
                            size="sm"
                            className="text-red-600 hover:bg-red-50"
                            onClick={() => setSelectedWithdrawId(r.id)}
                            icon={<Trash2 className="w-3.5 h-3.5" />}
                          >
                            Withdraw
                          </Button>
                        )}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

        </CardContent>
      </Card>

      {/* Withdraw Confirmation Modal */}
      <Modal
        isOpen={!!selectedWithdrawId}
        onClose={() => setSelectedWithdrawId(null)}
        title="Withdraw Issue Report"
        subtitle="Are you sure you want to withdraw this civic report?"
        maxWidth="sm"
      >
        <div className="space-y-4">
          <p className="text-xs text-slate-600 leading-relaxed">
            Withdrawing will mark this report as Rejected/Withdrawn. This action will cancel any pending municipal dispatch.
          </p>
          <div className="flex justify-end gap-3 pt-2">
            <Button variant="ghost" onClick={() => setSelectedWithdrawId(null)}>
              Keep Report
            </Button>
            <Button
              variant="danger"
              loading={withdrawing}
              onClick={handleWithdraw}
            >
              Confirm Withdrawal
            </Button>
          </div>
        </div>
      </Modal>

    </div>
  );
};
