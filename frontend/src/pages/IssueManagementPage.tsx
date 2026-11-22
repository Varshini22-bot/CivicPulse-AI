import React, { useState, useEffect } from 'react';
import {
  Search, Filter, Eye, UserCheck, RefreshCw, ChevronLeft,
  ChevronRight, ArrowUpDown, FileText, CheckCircle2, AlertTriangle
} from 'lucide-react';
import { Button } from '../components/ui/Button';
import { Card, CardContent, CardHeader } from '../components/ui/Card';
import { PriorityBadge, StatusBadge, CategoryBadge } from '../components/ui/Badge';
import { Modal } from '../components/ui/Modal';
import { useToast } from '../context/ToastContext';
import { api } from '../services/api';
import { ReportItem, Department, Category } from '../types';

interface IssueManagementPageProps {
  onNavigate: (page: string, params?: any) => void;
}

export const IssueManagementPage: React.FC<IssueManagementPageProps> = ({ onNavigate }) => {
  const { showToast } = useToast();
  const [reports, setReports] = useState<ReportItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [limit] = useState(15);
  const [totalPages, setTotalPages] = useState(1);
  const [loading, setLoading] = useState(true);

  // Filters
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [priorityFilter, setPriorityFilter] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('');
  const [areaFilter, setAreaFilter] = useState('');

  // Sorting
  const [sortBy, setSortBy] = useState('created_at');
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc');

  // Metadata
  const [departments, setDepartments] = useState<Department[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);

  // Modals
  const [statusModalReport, setStatusModalReport] = useState<ReportItem | null>(null);
  const [newStatus, setNewStatus] = useState('');
  const [statusNotes, setStatusNotes] = useState('');
  const [statusUpdating, setStatusUpdating] = useState(false);

  const [assignModalReport, setAssignModalReport] = useState<ReportItem | null>(null);
  const [selectedDeptId, setSelectedDeptId] = useState('');
  const [selectedStaffId, setSelectedStaffId] = useState('');
  const [assignNotes, setAssignNotes] = useState('');
  const [assigning, setAssigning] = useState(false);

  useEffect(() => {
    api.getCategories().then(setCategories).catch(() => {});
    api.getDepartments().then(setDepartments).catch(() => {});
  }, []);

  useEffect(() => {
    loadReports();
  }, [page, statusFilter, priorityFilter, categoryFilter, areaFilter, sortBy, sortDir]);

  const loadReports = async () => {
    setLoading(true);
    try {
      const res = await api.getAdminReports({
        search: search || undefined,
        status: statusFilter || undefined,
        priority: priorityFilter || undefined,
        category_id: categoryFilter || undefined,
        area: areaFilter || undefined,
        sort_by: sortBy,
        sort_dir: sortDir,
        page,
        limit,
      });
      setReports(res.items);
      setTotal(res.total);
      setTotalPages(res.total_pages);
    } catch {
      // Handle error
    } finally {
      setLoading(false);
    }
  };

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    loadReports();
  };

  const handleUpdateStatus = async () => {
    if (!statusModalReport || !newStatus) return;
    setStatusUpdating(true);
    try {
      await api.updateReportStatus(statusModalReport.id, newStatus, statusNotes);
      showToast('success', 'Status Transitioned', `Report #${statusModalReport.tracking_number} updated to '${newStatus}'.`);
      setStatusModalReport(null);
      setNewStatus('');
      setStatusNotes('');
      await loadReports();
    } catch (e: any) {
      showToast('error', 'Transition Rejected', e.message || 'Invalid status transition.');
    } finally {
      setStatusUpdating(false);
    }
  };

  const handleAssign = async () => {
    if (!assignModalReport || !selectedDeptId) return;
    setAssigning(true);
    try {
      await api.assignReport(assignModalReport.id, selectedDeptId, selectedStaffId || undefined, assignNotes);
      showToast('success', 'Work Order Dispatched', `Report #${assignModalReport.tracking_number} dispatched to municipal response crew.`);
      setAssignModalReport(null);
      setSelectedDeptId('');
      setSelectedStaffId('');
      setAssignNotes('');
      await loadReports();
    } catch (e: any) {
      showToast('error', 'Dispatch Failed', e.message || 'Department assignment failed.');
    } finally {
      setAssigning(false);
    }
  };

  const selectedDeptObj = departments.find(d => d.id === selectedDeptId);

  return (
    <div className="space-y-6 py-8">
      
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Municipal Issue Ledger & Dispatch</h1>
          <p className="text-xs text-slate-500 mt-1">
            Browse, filter, and transition civic complaints across BBMP, BWSSB, and BESCOM field departments.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={loadReports}
            icon={<RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />}
          >
            Refresh Ledger
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => onNavigate('reports-export')}
            icon={<FileText className="w-3.5 h-3.5" />}
          >
            Export CSV
          </Button>
        </div>
      </div>

      {/* Main Ledger Card */}
      <Card>
        <CardContent className="p-5 space-y-4">
          
          {/* Filters Bar */}
          <div className="grid grid-cols-1 md:grid-cols-6 gap-3">
            <form onSubmit={handleSearchSubmit} className="md:col-span-2 relative">
              <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5 pointer-events-none" />
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search tracking ID, title, street..."
                className="w-full pl-9 pr-3 py-1.5 text-xs border border-slate-300 rounded-lg focus:ring-2 focus:ring-teal-500 focus:outline-hidden"
              />
            </form>

            <select
              value={statusFilter}
              onChange={(e) => { setStatusFilter(e.target.value); setPage(1); }}
              className="text-xs border border-slate-300 rounded-lg px-2.5 py-1.5 bg-white focus:ring-2 focus:ring-teal-500"
            >
              <option value="">All Statuses</option>
              <option value="Submitted">Submitted</option>
              <option value="Under Review">Under Review</option>
              <option value="Verified">Verified</option>
              <option value="Assigned">Assigned</option>
              <option value="In Progress">In Progress</option>
              <option value="Resolved">Resolved</option>
              <option value="Rejected">Rejected</option>
            </select>

            <select
              value={priorityFilter}
              onChange={(e) => { setPriorityFilter(e.target.value); setPage(1); }}
              className="text-xs border border-slate-300 rounded-lg px-2.5 py-1.5 bg-white focus:ring-2 focus:ring-teal-500"
            >
              <option value="">All Priorities</option>
              <option value="Critical">Critical</option>
              <option value="High">High</option>
              <option value="Medium">Medium</option>
              <option value="Low">Low</option>
            </select>

            <select
              value={categoryFilter}
              onChange={(e) => { setCategoryFilter(e.target.value); setPage(1); }}
              className="text-xs border border-slate-300 rounded-lg px-2.5 py-1.5 bg-white focus:ring-2 focus:ring-teal-500"
            >
              <option value="">All Categories</option>
              {categories.map((c) => (
                <option key={c.id} value={c.id}>{c.name}</option>
              ))}
            </select>

            <select
              value={areaFilter}
              onChange={(e) => { setAreaFilter(e.target.value); setPage(1); }}
              className="text-xs border border-slate-300 rounded-lg px-2.5 py-1.5 bg-white focus:ring-2 focus:ring-teal-500"
            >
              <option value="">All Wards</option>
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
          </div>

          {/* Table */}
          <div className="overflow-x-auto rounded-lg border border-slate-200">
            <table className="w-full text-left text-xs border-collapse">
              <thead className="bg-slate-50 border-b border-slate-200 text-slate-600 font-semibold uppercase tracking-wider">
                <tr>
                  <th className="px-3 py-3">Tracking ID</th>
                  <th className="px-3 py-3">Issue Title</th>
                  <th className="px-3 py-3">Category</th>
                  <th className="px-3 py-3">Ward</th>
                  <th className="px-3 py-3">Priority</th>
                  <th className="px-3 py-3">Status</th>
                  <th className="px-3 py-3">Assigned To</th>
                  <th className="px-3 py-3">Date</th>
                  <th className="px-3 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-slate-700">
                {loading ? (
                  <tr>
                    <td colSpan={9} className="text-center py-8 text-slate-400">Loading ledger...</td>
                  </tr>
                ) : reports.length === 0 ? (
                  <tr>
                    <td colSpan={9} className="text-center py-8 text-slate-400">
                      No reports match the current filter criteria.
                    </td>
                  </tr>
                ) : (
                  reports.map((r) => (
                    <tr key={r.id} className="hover:bg-slate-50/80 transition-colors">
                      <td className="px-3 py-3 font-mono font-bold text-slate-900 whitespace-nowrap">
                        #{r.tracking_number}
                        {r.is_duplicate && (
                          <span className="ml-1 text-[9px] px-1 py-0.2 rounded-sm bg-purple-100 text-purple-700 font-bold">DUP</span>
                        )}
                      </td>
                      <td className="px-3 py-3 font-medium text-slate-900 max-w-xs truncate" title={r.title}>
                        {r.title}
                      </td>
                      <td className="px-3 py-3">
                        <CategoryBadge category={r.verified_category || r.category} />
                      </td>
                      <td className="px-3 py-3 text-slate-600 whitespace-nowrap">
                        {r.area || 'Bengaluru'}
                      </td>
                      <td className="px-3 py-3 whitespace-nowrap">
                        <PriorityBadge level={r.priority_level} score={Math.round(r.priority_score)} />
                      </td>
                      <td className="px-3 py-3 whitespace-nowrap">
                        <StatusBadge status={r.status} />
                      </td>
                      <td className="px-3 py-3 text-slate-600 max-w-[130px] truncate" title={r.assigned_department || 'Unassigned'}>
                        {r.assigned_department ? (
                          <span>{r.assigned_department.split(' ')[0]}</span>
                        ) : (
                          <span className="text-slate-400 italic">Unassigned</span>
                        )}
                      </td>
                      <td className="px-3 py-3 text-slate-500 whitespace-nowrap">
                        {new Date(r.created_at).toLocaleDateString([], { month: 'short', day: 'numeric' })}
                      </td>
                      <td className="px-3 py-3 text-right space-x-1.5 whitespace-nowrap">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => onNavigate('issue-details', { reportId: r.id })}
                          icon={<Eye className="w-3.5 h-3.5 text-slate-600" />}
                        >
                          Review
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => {
                            setStatusModalReport(r);
                            setNewStatus(r.status);
                            setStatusNotes(r.resolution_notes || '');
                          }}
                        >
                          Status
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          className="text-teal-600 hover:text-teal-700 hover:bg-teal-50"
                          onClick={() => {
                            setAssignModalReport(r);
                          }}
                          icon={<UserCheck className="w-3.5 h-3.5" />}
                        >
                          Dispatch
                        </Button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          <div className="flex items-center justify-between text-xs text-slate-500 pt-2">
            <div>
              Showing {reports.length > 0 ? (page - 1) * limit + 1 : 0} to {Math.min(page * limit, total)} of {total} reports
            </div>

            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                disabled={page <= 1}
                onClick={() => setPage(p => Math.max(1, p - 1))}
                icon={<ChevronLeft className="w-3.5 h-3.5" />}
              >
                Prev
              </Button>
              <span className="font-semibold px-2">Page {page} of {totalPages}</span>
              <Button
                variant="outline"
                size="sm"
                disabled={page >= totalPages}
                onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                icon={<ChevronRight className="w-3.5 h-3.5" />}
              >
                Next
              </Button>
            </div>
          </div>

        </CardContent>
      </Card>

      {/* Status Transition Modal */}
      <Modal
        isOpen={!!statusModalReport}
        onClose={() => setStatusModalReport(null)}
        title={`Update Report Status: #${statusModalReport?.tracking_number}`}
        subtitle="Enforces valid municipal state transitions and records audit notes"
        maxWidth="md"
      >
        <div className="space-y-4">
          <div className="p-3 rounded-lg bg-slate-50 border border-slate-200 text-xs">
            <div className="font-semibold text-slate-900">{statusModalReport?.title}</div>
            <div className="text-slate-500 mt-0.5">Current Status: <strong>{statusModalReport?.status}</strong></div>
          </div>

          <div className="space-y-1">
            <label className="text-xs font-semibold text-slate-700">Select New Status</label>
            <select
              value={newStatus}
              onChange={(e) => setNewStatus(e.target.value)}
              className="w-full text-xs border border-slate-300 rounded-lg px-3 py-2 bg-white focus:ring-2 focus:ring-teal-500"
            >
              <option value="Submitted">Submitted</option>
              <option value="Under Review">Under Review</option>
              <option value="Verified">Verified</option>
              <option value="Assigned">Assigned</option>
              <option value="In Progress">In Progress</option>
              <option value="Resolved">Resolved</option>
              <option value="Rejected">Rejected</option>
            </select>
          </div>

          <div className="space-y-1">
            <label className="text-xs font-semibold text-slate-700">Resolution / Audit Notes</label>
            <textarea
              rows={3}
              value={statusNotes}
              onChange={(e) => setStatusNotes(e.target.value)}
              placeholder="Record reason for transition, inspection details, or completion notes..."
              className="w-full text-xs border border-slate-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-teal-500"
            />
          </div>

          <div className="flex justify-end gap-3 pt-2">
            <Button variant="ghost" onClick={() => setStatusModalReport(null)}>
              Cancel
            </Button>
            <Button
              variant="primary"
              loading={statusUpdating}
              onClick={handleUpdateStatus}
            >
              Confirm Status Transition
            </Button>
          </div>
        </div>
      </Modal>

      {/* Dispatch Department Modal */}
      <Modal
        isOpen={!!assignModalReport}
        onClose={() => setAssignModalReport(null)}
        title={`Dispatch Department: #${assignModalReport?.tracking_number}`}
        subtitle="Route report to BBMP / BWSSB / BESCOM division and assign field staff"
        maxWidth="md"
      >
        <div className="space-y-4">
          <div className="p-3 rounded-lg bg-slate-50 border border-slate-200 text-xs">
            <div className="font-semibold text-slate-900">{assignModalReport?.title}</div>
            <div className="text-slate-500 mt-0.5">Category: {assignModalReport?.category} • Priority: {assignModalReport?.priority_level}</div>
          </div>

          <div className="space-y-1">
            <label className="text-xs font-semibold text-slate-700">Assign Municipal Department *</label>
            <select
              value={selectedDeptId}
              onChange={(e) => {
                setSelectedDeptId(e.target.value);
                setSelectedStaffId('');
              }}
              className="w-full text-xs border border-slate-300 rounded-lg px-3 py-2 bg-white focus:ring-2 focus:ring-teal-500"
            >
              <option value="">Select Department</option>
              {departments.map((d) => (
                <option key={d.id} value={d.id}>{d.name} ({d.code})</option>
              ))}
            </select>
          </div>

          {selectedDeptObj && selectedDeptObj.staff_members.length > 0 && (
            <div className="space-y-1">
              <label className="text-xs font-semibold text-slate-700">Assign Responsible Staff Member</label>
              <select
                value={selectedStaffId}
                onChange={(e) => setSelectedStaffId(e.target.value)}
                className="w-full text-xs border border-slate-300 rounded-lg px-3 py-2 bg-white focus:ring-2 focus:ring-teal-500"
              >
                <option value="">Unassigned (Assign to Division Pool)</option>
                {selectedDeptObj.staff_members.map((s) => (
                  <option key={s.id} value={s.id}>{s.name} — {s.designation}</option>
                ))}
              </select>
            </div>
          )}

          <div className="space-y-1">
            <label className="text-xs font-semibold text-slate-700">Dispatch Instructions</label>
            <textarea
              rows={2}
              value={assignNotes}
              onChange={(e) => setAssignNotes(e.target.value)}
              placeholder="e.g. Deploy asphalt cold-patch crew with vibrating roller..."
              className="w-full text-xs border border-slate-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-teal-500"
            />
          </div>

          <div className="flex justify-end gap-3 pt-2">
            <Button variant="ghost" onClick={() => setAssignModalReport(null)}>
              Cancel
            </Button>
            <Button
              variant="secondary"
              loading={assigning}
              disabled={!selectedDeptId}
              onClick={handleAssign}
            >
              Dispatch Work Order
            </Button>
          </div>
        </div>
      </Modal>

    </div>
  );
};
