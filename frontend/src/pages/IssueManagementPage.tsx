import React, { useState, useEffect } from 'react';
import {
  Search, Filter, Eye, UserCheck, RefreshCw, ChevronLeft,
  ChevronRight, ArrowUpDown, FileText, CheckCircle2, AlertTriangle,
  Layers, ShieldAlert, Check, X, ArrowRight, CornerDownRight, ThumbsUp
} from 'lucide-react';
import { Button } from '../components/ui/Button';
import { Card, CardContent, CardHeader } from '../components/ui/Card';
import { PriorityBadge, StatusBadge, CategoryBadge } from '../components/ui/Badge';
import { Modal } from '../components/ui/Modal';
import { useToast } from '../context/ToastContext';
import { api } from '../services/api';
import { ReportItem, Department, Category, ResolutionAuditItem, RecurringCorridor } from '../types';

interface IssueManagementPageProps {
  onNavigate: (page: string, params?: any) => void;
}

export const IssueManagementPage: React.FC<IssueManagementPageProps> = ({ onNavigate }) => {
  const { showToast } = useToast();
  
  // Navigation Tabs: Triage Queue | Resolution Audit | Chronic Corridors
  const [activeTab, setActiveTab] = useState<'triage' | 'resolution_audit' | 'chronic_corridors'>('triage');

  // --- Triage Ledger State ---
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

  // Sorting: Default to Priority v2 descending
  const [sortBy, setSortBy] = useState('priority_score');
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc');

  // Bulk Selection
  const [selectedReportIds, setSelectedReportIds] = useState<string[]>([]);
  const [bulkAction, setBulkAction] = useState<'change_status' | 'assign_department' | ''>('');
  const [bulkStatus, setBulkStatus] = useState('Verified');
  const [bulkDeptId, setBulkDeptId] = useState('');
  const [bulkProcessing, setBulkProcessing] = useState(false);

  // Metadata
  const [departments, setDepartments] = useState<Department[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);

  // Modals for single ticket operations
  const [statusModalReport, setStatusModalReport] = useState<ReportItem | null>(null);
  const [newStatus, setNewStatus] = useState('');
  const [statusNotes, setStatusNotes] = useState('');
  const [statusUpdating, setStatusUpdating] = useState(false);

  const [assignModalReport, setAssignModalReport] = useState<ReportItem | null>(null);
  const [selectedDeptId, setSelectedDeptId] = useState('');
  const [selectedStaffId, setSelectedStaffId] = useState('');
  const [assignNotes, setAssignNotes] = useState('');
  const [assigning, setAssigning] = useState(false);

  // --- Resolution Verification Audit Queue State ---
  const [auditQueue, setAuditQueue] = useState<ResolutionAuditItem[]>([]);
  const [auditLoading, setAuditLoading] = useState(false);
  const [auditProcessingId, setAuditProcessingId] = useState<string | null>(null);

  // --- Chronic Recurrence Corridors State ---
  const [corridors, setCorridors] = useState<RecurringCorridor[]>([]);
  const [corridorsLoading, setCorridorsLoading] = useState(false);

  useEffect(() => {
    api.getCategories().then(setCategories).catch(() => {});
    api.getDepartments().then(setDepartments).catch(() => {});
  }, []);

  useEffect(() => {
    if (activeTab === 'triage') {
      loadReports();
    } else if (activeTab === 'resolution_audit') {
      loadResolutionAudit();
    } else if (activeTab === 'chronic_corridors') {
      loadChronicCorridors();
    }
  }, [activeTab, page, statusFilter, priorityFilter, categoryFilter, areaFilter, sortBy, sortDir]);

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

  const loadResolutionAudit = async () => {
    setAuditLoading(true);
    try {
      const items = await api.getResolutionAuditQueue();
      setAuditQueue(items);
    } catch {
      showToast('error', 'Audit Load Failed', 'Could not load resolution audit queue.');
    } finally {
      setAuditLoading(false);
    }
  };

  const loadChronicCorridors = async () => {
    setCorridorsLoading(true);
    try {
      const data = await api.getRecurringCorridors();
      setCorridors(data);
    } catch {
      showToast('error', 'Corridors Load Failed', 'Could not load recurring road corridors.');
    } finally {
      setCorridorsLoading(false);
    }
  };

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    loadReports();
  };

  // --- Bulk Selection Handlers ---
  const handleSelectAll = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.checked) {
      setSelectedReportIds(reports.map(r => r.id));
    } else {
      setSelectedReportIds([]);
    }
  };

  const handleToggleSelect = (id: string) => {
    setSelectedReportIds(prev =>
      prev.includes(id) ? prev.filter(item => item !== id) : [...prev, id]
    );
  };

  const handleExecuteBulkAction = async () => {
    if (selectedReportIds.length === 0 || !bulkAction) return;
    setBulkProcessing(true);
    try {
      const payload: any = {
        report_ids: selectedReportIds,
        action: bulkAction,
      };
      if (bulkAction === 'change_status') {
        payload.status = bulkStatus;
      } else if (bulkAction === 'assign_department') {
        payload.department_id = bulkDeptId;
      }

      const res = await api.executeBulkAction(payload);
      showToast('success', 'Bulk Action Applied', `Updated ${res.affected_count} civic issue tickets.`);
      setSelectedReportIds([]);
      setBulkAction('');
      await loadReports();
    } catch (e: any) {
      showToast('error', 'Bulk Action Failed', e.message || 'Could not execute bulk operation.');
    } finally {
      setBulkProcessing(false);
    }
  };

  // --- Resolution Verification Actions ---
  const handleAuditDecision = async (reportId: string, decision: 'confirm' | 'reject_reopen') => {
    setAuditProcessingId(reportId);
    try {
      await api.auditResolutionDecision(reportId, decision);
      showToast(
        'success',
        decision === 'confirm' ? 'Resolution Confirmed' : 'Ticket Reopened',
        decision === 'confirm'
          ? 'Marked as supervisor-verified completion.'
          : 'Reopened ticket to In Progress for field remediation.'
      );
      await loadResolutionAudit();
    } catch (e: any) {
      showToast('error', 'Audit Failed', e.message || 'Could not submit audit decision.');
    } finally {
      setAuditProcessingId(null);
    }
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
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Municipal Operations & Triage</h1>
          <p className="text-xs text-slate-500 mt-1">
            Priority v2 dispatch ledger, bulk work-order processing, and before/after resolution verification audits.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => {
              if (activeTab === 'triage') loadReports();
              else if (activeTab === 'resolution_audit') loadResolutionAudit();
              else loadChronicCorridors();
            }}
            icon={<RefreshCw className={`w-3.5 h-3.5 ${loading || auditLoading || corridorsLoading ? 'animate-spin' : ''}`} />}
          >
            Refresh View
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

      {/* Navigation Tabs */}
      <div className="flex items-center gap-2 border-b border-slate-200">
        <button
          onClick={() => setActiveTab('triage')}
          className={`px-4 py-2.5 text-xs font-semibold border-b-2 transition-colors ${
            activeTab === 'triage'
              ? 'border-teal-600 text-teal-800 bg-teal-50/50'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          Priority v2 Triage Ledger ({total})
        </button>
        <button
          onClick={() => setActiveTab('resolution_audit')}
          className={`px-4 py-2.5 text-xs font-semibold border-b-2 transition-colors flex items-center gap-1.5 ${
            activeTab === 'resolution_audit'
              ? 'border-teal-600 text-teal-800 bg-teal-50/50'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          <span>Resolution Audit Queue</span>
          {auditQueue.filter(i => i.resolution_verification_status === 'flagged_for_review').length > 0 && (
            <span className="w-2 h-2 rounded-full bg-amber-500 animate-pulse" />
          )}
        </button>
        <button
          onClick={() => setActiveTab('chronic_corridors')}
          className={`px-4 py-2.5 text-xs font-semibold border-b-2 transition-colors flex items-center gap-1.5 ${
            activeTab === 'chronic_corridors'
              ? 'border-teal-600 text-teal-800 bg-teal-50/50'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          <span>Chronic Corridors (OSM Recurrence)</span>
        </button>
      </div>

      {/* TAB 1: PRIORITY V2 TRIAGE LEDGER */}
      {activeTab === 'triage' && (
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

            {/* Bulk Action Controls Bar */}
            {selectedReportIds.length > 0 && (
              <div className="flex flex-wrap items-center justify-between gap-3 p-3 bg-teal-50 border border-teal-200 rounded-lg text-xs">
                <div className="flex items-center gap-2 text-teal-900 font-semibold">
                  <Check className="w-4 h-4 text-teal-600" />
                  <span>{selectedReportIds.length} tickets selected for bulk operation</span>
                </div>

                <div className="flex flex-wrap items-center gap-2">
                  <select
                    value={bulkAction}
                    onChange={(e) => setBulkAction(e.target.value as any)}
                    className="text-xs border border-teal-300 rounded-md px-2 py-1 bg-white focus:ring-2 focus:ring-teal-500"
                  >
                    <option value="">Select Bulk Action...</option>
                    <option value="change_status">Batch Status Change</option>
                    <option value="assign_department">Dispatch to Department</option>
                  </select>

                  {bulkAction === 'change_status' && (
                    <select
                      value={bulkStatus}
                      onChange={(e) => setBulkStatus(e.target.value)}
                      className="text-xs border border-teal-300 rounded-md px-2 py-1 bg-white"
                    >
                      <option value="Under Review">Under Review</option>
                      <option value="Verified">Verified</option>
                      <option value="Assigned">Assigned</option>
                      <option value="In Progress">In Progress</option>
                      <option value="Resolved">Resolved</option>
                    </select>
                  )}

                  {bulkAction === 'assign_department' && (
                    <select
                      value={bulkDeptId}
                      onChange={(e) => setBulkDeptId(e.target.value)}
                      className="text-xs border border-teal-300 rounded-md px-2 py-1 bg-white"
                    >
                      <option value="">Select Department...</option>
                      {departments.map((d) => (
                        <option key={d.id} value={d.id}>{d.name}</option>
                      ))}
                    </select>
                  )}

                  <Button
                    variant="primary"
                    size="sm"
                    loading={bulkProcessing}
                    disabled={!bulkAction || (bulkAction === 'assign_department' && !bulkDeptId)}
                    onClick={handleExecuteBulkAction}
                  >
                    Apply Bulk Action
                  </Button>

                  <button
                    type="button"
                    onClick={() => setSelectedReportIds([])}
                    className="text-slate-500 hover:text-slate-700 p-1"
                    aria-label="Clear selection"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>
              </div>
            )}

            {/* Table */}
            <div className="overflow-x-auto rounded-lg border border-slate-200">
              <table className="w-full text-left text-xs border-collapse">
                <thead className="bg-slate-50 border-b border-slate-200 text-slate-600 font-semibold uppercase tracking-wider">
                  <tr>
                    <th className="px-3 py-3 w-8">
                      <input
                        type="checkbox"
                        checked={reports.length > 0 && selectedReportIds.length === reports.length}
                        onChange={handleSelectAll}
                        aria-label="Select all reports on current page"
                        className="rounded border-slate-300 text-teal-600 focus:ring-teal-500"
                      />
                    </th>
                    <th className="px-3 py-3">Tracking ID</th>
                    <th className="px-3 py-3">Issue Title</th>
                    <th className="px-3 py-3">Category</th>
                    <th className="px-3 py-3">Ward</th>
                    <th
                      className="px-3 py-3 cursor-pointer hover:bg-slate-100"
                      onClick={() => {
                        if (sortBy === 'priority_score') {
                          setSortDir(sortDir === 'desc' ? 'asc' : 'desc');
                        } else {
                          setSortBy('priority_score');
                          setSortDir('desc');
                        }
                      }}
                    >
                      <div className="flex items-center gap-1">
                        <span>Priority v2</span>
                        <ArrowUpDown className="w-3 h-3 text-slate-400" />
                      </div>
                    </th>
                    <th className="px-3 py-3">Status</th>
                    <th className="px-3 py-3">Assigned To</th>
                    <th className="px-3 py-3">Date</th>
                    <th className="px-3 py-3 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 bg-white">
                  {loading ? (
                    <tr>
                      <td colSpan={10} className="text-center py-10 text-slate-400">
                        <RefreshCw className="w-5 h-5 animate-spin mx-auto mb-2 text-teal-600" />
                        Loading priority dispatch queue...
                      </td>
                    </tr>
                  ) : reports.length === 0 ? (
                    <tr>
                      <td colSpan={10} className="text-center py-10 text-slate-400">
                        No civic issue records match the selected filter criteria.
                      </td>
                    </tr>
                  ) : (
                    reports.map((r) => {
                      const isSelected = selectedReportIds.includes(r.id);
                      return (
                        <tr key={r.id} className={`hover:bg-slate-50/80 transition-colors ${isSelected ? 'bg-teal-50/40' : ''}`}>
                          <td className="px-3 py-3">
                            <input
                              type="checkbox"
                              checked={isSelected}
                              onChange={() => handleToggleSelect(r.id)}
                              aria-label={`Select report ${r.tracking_number}`}
                              className="rounded border-slate-300 text-teal-600 focus:ring-teal-500"
                            />
                          </td>
                          <td className="px-3 py-3 font-mono font-semibold text-slate-900">
                            #{r.tracking_number}
                            {r.is_duplicate && (
                              <span className="block text-[10px] text-amber-600 font-sans">Duplicate</span>
                            )}
                          </td>
                          <td className="px-3 py-3 max-w-[220px]">
                            <div className="font-medium text-slate-900 truncate" title={r.title}>{r.title}</div>
                            <div className="text-[11px] text-slate-400 truncate">{r.address || 'Street not specified'}</div>
                          </td>
                          <td className="px-3 py-3">
                            <CategoryBadge category={r.category} />
                          </td>
                          <td className="px-3 py-3 text-slate-600 font-medium">
                            {r.area || 'Bengaluru'}
                          </td>
                          <td className="px-3 py-3">
                            <PriorityBadge
                              level={r.priority_level}
                              score={Math.round(r.priority_score)}
                            />
                          </td>
                          <td className="px-3 py-3">
                            <StatusBadge status={r.status} />
                          </td>
                          <td className="px-3 py-3 text-slate-600">
                            {r.assigned_department ? (
                              <span className="font-medium truncate block max-w-[140px]" title={r.assigned_department}>
                                {r.assigned_department}
                              </span>
                            ) : (
                              <span className="text-slate-400 italic">Unassigned</span>
                            )}
                          </td>
                          <td className="px-3 py-3 text-slate-400 whitespace-nowrap">
                            {new Date(r.created_at).toLocaleDateString()}
                          </td>
                          <td className="px-3 py-3 text-right">
                            <div className="flex items-center justify-end gap-1">
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => onNavigate('issue-details', { reportId: r.id })}
                                title="View Issue Details"
                                aria-label={`View details for #${r.tracking_number}`}
                              >
                                <Eye className="w-3.5 h-3.5 text-slate-600" />
                              </Button>

                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => {
                                  setStatusModalReport(r);
                                  setNewStatus(r.status);
                                }}
                                title="Change Status"
                                aria-label={`Change status for #${r.tracking_number}`}
                              >
                                <CheckCircle2 className="w-3.5 h-3.5 text-teal-600" />
                              </Button>

                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => {
                                  setAssignModalReport(r);
                                }}
                                title="Dispatch Department"
                                aria-label={`Dispatch department for #${r.tracking_number}`}
                              >
                                <UserCheck className="w-3.5 h-3.5 text-indigo-600" />
                              </Button>
                            </div>
                          </td>
                        </tr>
                      );
                    })
                  )}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            <div className="flex items-center justify-between text-xs text-slate-500 pt-2">
              <div>
                Showing <strong>{(page - 1) * limit + 1}</strong> to <strong>{Math.min(page * limit, total)}</strong> of <strong>{total}</strong> issues
              </div>

              <div className="flex items-center gap-1">
                <Button
                  variant="outline"
                  size="sm"
                  disabled={page <= 1}
                  onClick={() => setPage(page - 1)}
                  icon={<ChevronLeft className="w-3.5 h-3.5" />}
                >
                  Prev
                </Button>
                <span className="px-3 py-1 font-semibold text-slate-700">
                  Page {page} of {totalPages}
                </span>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={page >= totalPages}
                  onClick={() => setPage(page + 1)}
                  icon={<ChevronRight className="w-3.5 h-3.5" />}
                >
                  Next
                </Button>
              </div>
            </div>

          </CardContent>
        </Card>
      )}

      {/* TAB 2: RESOLUTION VERIFICATION AUDIT QUEUE */}
      {activeTab === 'resolution_audit' && (
        <div className="space-y-4">
          <div className="p-4 rounded-xl bg-teal-50 border border-teal-200 text-teal-900 text-xs">
            <h3 className="font-bold text-sm mb-1">Automated Resolution Verification & Supervisor Sign-Off</h3>
            <p className="leading-relaxed">
              When field contractors resolve public work orders, before and after photos are audited for spatial proximity,
              OpenCLIP visual scene background similarity (&ge;55%), and defect disappearance.
              Human municipal supervisors review and confirm completion evidence below.
            </p>
          </div>

          {auditLoading ? (
            <div className="text-center py-12 text-slate-400">
              <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2 text-teal-600" />
              Loading resolution audit queue...
            </div>
          ) : auditQueue.length === 0 ? (
            <div className="text-center py-12 text-slate-400 bg-white rounded-xl border border-slate-200">
              No resolved tickets currently pending verification audit.
            </div>
          ) : (
            <div className="grid grid-cols-1 gap-4">
              {auditQueue.map((item) => {
                const isProcessing = auditProcessingId === item.id;
                const isFlagged = item.resolution_verification_status === 'flagged_for_review';
                const isVerified = item.resolution_verification_status === 'verified';

                return (
                  <Card key={item.id} className={isFlagged ? 'border-amber-300 shadow-sm' : ''}>
                    <CardContent className="p-5 space-y-4">
                      
                      {/* Header row */}
                      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 border-b border-slate-100 pb-3">
                        <div>
                          <div className="flex items-center gap-2">
                            <span className="font-mono font-bold text-sm text-slate-900">#{item.tracking_number}</span>
                            <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full uppercase tracking-wider ${
                              isVerified ? 'bg-emerald-100 text-emerald-800' :
                              isFlagged ? 'bg-amber-100 text-amber-800' : 'bg-slate-100 text-slate-700'
                            }`}>
                              Audit: {item.resolution_verification_status.replace('_', ' ')}
                            </span>
                          </div>
                          <h4 className="text-sm font-semibold text-slate-800 mt-1">{item.title}</h4>
                          <p className="text-xs text-slate-500">{item.category} • Ward: {item.area || 'Bengaluru'}</p>
                        </div>

                        <div className="flex items-center gap-2">
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => onNavigate('issue-details', { reportId: item.id })}
                            icon={<Eye className="w-3.5 h-3.5" />}
                          >
                            Dossier
                          </Button>
                          <Button
                            variant="primary"
                            size="sm"
                            loading={isProcessing}
                            onClick={() => handleAuditDecision(item.id, 'confirm')}
                            icon={<Check className="w-3.5 h-3.5" />}
                          >
                            Confirm Resolution
                          </Button>
                          <Button
                            variant="outline"
                            size="sm"
                            className="text-red-700 hover:bg-red-50 hover:border-red-300"
                            loading={isProcessing}
                            onClick={() => handleAuditDecision(item.id, 'reject_reopen')}
                            icon={<X className="w-3.5 h-3.5 text-red-600" />}
                          >
                            Reject & Reopen
                          </Button>
                        </div>
                      </div>

                      {/* Before / After Photo Comparison */}
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                        <div className="space-y-1.5">
                          <span className="text-xs font-semibold text-slate-700">Before (Citizen Report Photo):</span>
                          <div className="h-48 rounded-lg overflow-hidden border border-slate-200 bg-slate-100">
                            {item.image_url ? (
                              <img src={item.image_url} alt="Before report defect" className="w-full h-full object-cover" />
                            ) : (
                              <div className="h-full flex items-center justify-center text-xs text-slate-400">No before photo</div>
                            )}
                          </div>
                        </div>

                        <div className="space-y-1.5">
                          <span className="text-xs font-semibold text-slate-700">After (Contractor Resolution Evidence):</span>
                          <div className="h-48 rounded-lg overflow-hidden border border-slate-200 bg-slate-100">
                            {item.resolution_image_url ? (
                              <img src={item.resolution_image_url} alt="After repair completion" className="w-full h-full object-cover" />
                            ) : (
                              <div className="h-full flex items-center justify-center text-xs text-slate-400">No completion photo submitted</div>
                            )}
                          </div>
                        </div>
                      </div>

                      {/* AI Verification Scoring Metrics */}
                      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 bg-slate-50 p-3 rounded-lg border border-slate-200/80 text-xs">
                        <div>
                          <span className="text-slate-500 block">Composite Verification</span>
                          <strong className="text-slate-900 text-sm">
                            {item.verification_score !== undefined ? `${Math.round(item.verification_score * 100)}%` : 'N/A'}
                          </strong>
                        </div>
                        <div>
                          <span className="text-slate-500 block">Scene Consistency</span>
                          <strong className="text-slate-900 text-sm">
                            {item.scene_consistency !== undefined ? `${Math.round(item.scene_consistency * 100)}%` : 'N/A'}
                          </strong>
                        </div>
                        <div>
                          <span className="text-slate-500 block">Defect Disappeared</span>
                          <strong className={item.defect_disappeared ? 'text-emerald-700 text-sm' : 'text-red-600 text-sm'}>
                            {item.defect_disappeared ? 'Yes (Clear)' : 'Active Defect Detected'}
                          </strong>
                        </div>
                        <div>
                          <span className="text-slate-500 block">Resolved At</span>
                          <span className="text-slate-700 font-medium">
                            {item.resolved_at ? new Date(item.resolved_at).toLocaleDateString() : 'Pending'}
                          </span>
                        </div>
                      </div>

                      {item.reasons && item.reasons.length > 0 && (
                        <div className="text-xs text-slate-600 space-y-1 bg-white p-2.5 rounded-lg border border-slate-200">
                          <span className="font-semibold text-slate-700">Audit Diagnostics:</span>
                          <ul className="list-disc list-inside space-y-0.5 text-[11px] text-slate-500">
                            {item.reasons.map((r, idx) => (
                              <li key={idx}>{r}</li>
                            ))}
                          </ul>
                        </div>
                      )}

                    </CardContent>
                  </Card>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* TAB 3: CHRONIC CORRIDORS (OPENSTREETMAP RECURRENCE) */}
      {activeTab === 'chronic_corridors' && (
        <div className="space-y-4">
          <div className="p-4 rounded-xl bg-amber-50 border border-amber-200 text-amber-900 text-xs">
            <h3 className="font-bold text-sm mb-1">OpenStreetMap Road Recurrence Analysis</h3>
            <p className="leading-relaxed">
              Arterial corridors exhibiting repeated infrastructure failure (&ge;3 reports within 90 days) indicate
              sub-surface drainage failure or heavy axle-load degradation rather than isolated surface cavities.
              Advisories below provide civil engineering recommendations for permanent rehabilitation.
            </p>
          </div>

          {corridorsLoading ? (
            <div className="text-center py-12 text-slate-400">
              <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2 text-teal-600" />
              Scanning OpenStreetMap road network...
            </div>
          ) : corridors.length === 0 ? (
            <div className="text-center py-12 text-slate-400 bg-white rounded-xl border border-slate-200">
              No chronic recurring corridors detected on current dataset.
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {corridors.map((c) => (
                <Card key={c.road_id} className={c.chronic_status === 'severe' ? 'border-red-300' : 'border-amber-300'}>
                  <CardHeader
                    title={c.road_name}
                    subtitle={`Ward: ${c.ward || 'Bengaluru'} • Highway: ${c.highway_type}`}
                    action={
                      <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full uppercase ${
                        c.chronic_status === 'severe' ? 'bg-red-100 text-red-800' : 'bg-amber-100 text-amber-800'
                      }`}>
                        {c.chronic_status} recurrence
                      </span>
                    }
                  />
                  <CardContent className="space-y-3 text-xs">
                    <div className="grid grid-cols-3 gap-2 bg-slate-50 p-2.5 rounded-lg border border-slate-200/80">
                      <div>
                        <span className="text-slate-500 block">Total Reports</span>
                        <strong className="text-slate-900 text-sm">{c.incident_count}</strong>
                      </div>
                      <div>
                        <span className="text-slate-500 block">Active Issues</span>
                        <strong className="text-amber-700 text-sm">{c.active_incident_count}</strong>
                      </div>
                      <div>
                        <span className="text-slate-500 block">Avg Priority</span>
                        <strong className="text-slate-900 text-sm">{c.avg_priority_score}</strong>
                      </div>
                    </div>

                    <div className="p-3 rounded-lg bg-white border border-slate-200 space-y-1">
                      <span className="font-semibold text-slate-800 block text-xs">Civil Engineering Root-Cause Advisory:</span>
                      <p className="text-slate-600 leading-relaxed text-[11px]">{c.root_cause_advisory}</p>
                    </div>

                    <Button
                      variant="outline"
                      size="sm"
                      className="w-full"
                      onClick={() => onNavigate('map')}
                      icon={<ArrowRight className="w-3.5 h-3.5" />}
                    >
                      View Corridor on GIS Map
                    </Button>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Status Modal */}
      {statusModalReport && (
        <Modal
          isOpen={true}
          onClose={() => setStatusModalReport(null)}
          title={`Update Status: #${statusModalReport.tracking_number}`}
          subtitle="Transition issue state across municipal SLA pipeline"
        >
          <div className="space-y-4">
            <div className="space-y-1">
              <label htmlFor="modal-status-select" className="text-xs font-semibold text-slate-700">New Operational Status *</label>
              <select
                id="modal-status-select"
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
              <label htmlFor="modal-status-notes" className="text-xs font-semibold text-slate-700">Audit Transition Notes</label>
              <textarea
                id="modal-status-notes"
                rows={3}
                value={statusNotes}
                onChange={(e) => setStatusNotes(e.target.value)}
                placeholder="Document verification findings, contractor dispatch reference, or rejection rationale..."
                className="w-full text-xs border border-slate-300 rounded-lg p-2.5 focus:ring-2 focus:ring-teal-500"
              />
            </div>

            <div className="flex justify-end gap-2 pt-2">
              <Button variant="ghost" size="sm" onClick={() => setStatusModalReport(null)}>
                Cancel
              </Button>
              <Button
                variant="primary"
                size="sm"
                loading={statusUpdating}
                onClick={handleUpdateStatus}
              >
                Confirm Transition
              </Button>
            </div>
          </div>
        </Modal>
      )}

      {/* Assign Modal */}
      {assignModalReport && (
        <Modal
          isOpen={true}
          onClose={() => setAssignModalReport(null)}
          title={`Dispatch Work Order: #${assignModalReport.tracking_number}`}
          subtitle="Assign responsible municipal department and field responder"
        >
          <div className="space-y-4">
            <div className="space-y-1">
              <label htmlFor="modal-assign-dept" className="text-xs font-semibold text-slate-700">Responsible Department *</label>
              <select
                id="modal-assign-dept"
                value={selectedDeptId}
                onChange={(e) => {
                  setSelectedDeptId(e.target.value);
                  setSelectedStaffId('');
                }}
                className="w-full text-xs border border-slate-300 rounded-lg px-3 py-2 bg-white focus:ring-2 focus:ring-teal-500"
              >
                <option value="">Select Department...</option>
                {departments.map((d) => (
                  <option key={d.id} value={d.id}>{d.name} ({d.code})</option>
                ))}
              </select>
            </div>

            {selectedDeptObj && (
              <div className="space-y-1">
                <label htmlFor="modal-assign-staff" className="text-xs font-semibold text-slate-700">Field Engineer / Staff</label>
                <select
                  id="modal-assign-staff"
                  value={selectedStaffId}
                  onChange={(e) => setSelectedStaffId(e.target.value)}
                  className="w-full text-xs border border-slate-300 rounded-lg px-3 py-2 bg-white focus:ring-2 focus:ring-teal-500"
                >
                  <option value="">General Municipal Pool</option>
                  {selectedDeptObj.staff_members.map((s) => (
                    <option key={s.id} value={s.id}>{s.name} ({s.designation})</option>
                  ))}
                </select>
              </div>
            )}

            <div className="space-y-1">
              <label htmlFor="modal-assign-notes" className="text-xs font-semibold text-slate-700">Work Order Instructions</label>
              <textarea
                id="modal-assign-notes"
                rows={3}
                value={assignNotes}
                onChange={(e) => setAssignNotes(e.target.value)}
                placeholder="Include urgency level, asphalt compaction requirement, safety barricades..."
                className="w-full text-xs border border-slate-300 rounded-lg p-2.5 focus:ring-2 focus:ring-teal-500"
              />
            </div>

            <div className="flex justify-end gap-2 pt-2">
              <Button variant="ghost" size="sm" onClick={() => setAssignModalReport(null)}>
                Cancel
              </Button>
              <Button
                variant="primary"
                size="sm"
                loading={assigning}
                disabled={!selectedDeptId}
                onClick={handleAssign}
              >
                Dispatch Work Order
              </Button>
            </div>
          </div>
        </Modal>
      )}

    </div>
  );
};
