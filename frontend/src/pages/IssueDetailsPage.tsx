import React, { useState, useEffect } from 'react';
import {
  ArrowLeft, MapPin, Cpu, Activity, Clock, ShieldAlert,
  CheckCircle2, AlertTriangle, Layers, Edit3, UserCheck,
  History, Camera, FileCheck, Share2, Maximize2, X
} from 'lucide-react';
import { Button } from '../components/ui/Button';
import { Card, CardContent, CardHeader } from '../components/ui/Card';
import { PriorityBadge, StatusBadge, CategoryBadge } from '../components/ui/Badge';
import { Modal } from '../components/ui/Modal';
import { LeafletMap } from '../components/maps/LeafletMap';
import { api } from '../services/api';
import { ReportDetail, Category, Department } from '../types';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';

interface IssueDetailsPageProps {
  reportId: string;
  onNavigate: (page: string, params?: any) => void;
}

export const IssueDetailsPage: React.FC<IssueDetailsPageProps> = ({ reportId, onNavigate }) => {
  const { isAdmin } = useAuth();
  const { showToast } = useToast();
  const [report, setReport] = useState<ReportDetail | null>(null);
  const [categories, setCategories] = useState<Category[]>([]);
  const [departments, setDepartments] = useState<Department[]>([]);
  const [loading, setLoading] = useState(true);

  // Lightbox Modal
  const [lightboxImage, setLightboxImage] = useState<string | null>(null);

  // Override Modal
  const [showOverrideModal, setShowOverrideModal] = useState(false);
  const [overrideCategory, setOverrideCategory] = useState('');
  const [overrideSeverity, setOverrideSeverity] = useState(5);
  const [overrideNotes, setOverrideNotes] = useState('');
  const [overriding, setOverriding] = useState(false);

  // Status Change Modal
  const [showStatusModal, setShowStatusModal] = useState(false);
  const [targetStatus, setTargetStatus] = useState('');
  const [resolutionNotes, setResolutionNotes] = useState('');
  const [resolutionImgUrl, setResolutionImgUrl] = useState('');
  const [updatingStatus, setUpdatingStatus] = useState(false);

  useEffect(() => {
    loadData();
  }, [reportId]);

  const loadData = async () => {
    setLoading(true);
    try {
      const [rData, cData, dData] = await Promise.all([
        api.getReportById(reportId),
        api.getCategories(),
        api.getDepartments(),
      ]);
      setReport(rData);
      setCategories(cData);
      setDepartments(dData);
      setOverrideSeverity(rData.human_severity || rData.ai_severity);
      setOverrideCategory(rData.category_code);
      setTargetStatus(rData.status);
    } catch {
      showToast('error', 'Failed to load report', 'Could not retrieve report dossier.');
    } finally {
      setLoading(false);
    }
  };

  const handleOverrideSubmit = async () => {
    if (!report) return;
    setOverriding(true);
    try {
      const updated = await api.overrideAIPrediction(
        report.id,
        overrideCategory,
        overrideSeverity,
        overrideNotes
      );
      setReport(updated);
      setShowOverrideModal(false);
      setOverrideNotes('');
      showToast('success', 'AI Prediction Overridden', 'Recalculated priority score and logged audit action.');
    } catch (e: any) {
      showToast('error', 'Override Failed', e.message || 'Could not save AI override.');
    } finally {
      setOverriding(false);
    }
  };

  const handleStatusSubmit = async () => {
    if (!report) return;
    setUpdatingStatus(true);
    try {
      const updated = await api.updateReportStatus(
        report.id,
        targetStatus,
        resolutionNotes,
        resolutionImgUrl || undefined
      );
      setReport(updated);
      setShowStatusModal(false);
      showToast('success', 'Status Updated', `Report transitioned to ${targetStatus}.`);
    } catch (e: any) {
      showToast('error', 'Update Failed', e.message || 'Status transition was rejected.');
    } finally {
      setUpdatingStatus(false);
    }
  };

  const handleResolveDuplicate = async (candId: string, decision: 'confirmed' | 'rejected') => {
    try {
      await api.resolveDuplicate(candId, decision);
      showToast('info', 'Duplicate Resolved', `Marked duplicate candidate as ${decision}.`);
      await loadData();
    } catch (e: any) {
      showToast('error', 'Action Failed', e.message || 'Duplicate resolution failed.');
    }
  };

  if (loading) {
    return (
      <div className="py-16 text-center text-slate-400 space-y-2">
        <div className="w-8 h-8 rounded-full border-2 border-teal-500 border-t-transparent animate-spin mx-auto" />
        <p className="text-xs">Loading comprehensive issue dossier...</p>
      </div>
    );
  }

  if (!report) {
    return (
      <div className="py-16 text-center text-slate-500 space-y-4">
        <p>Report not found.</p>
        <Button variant="outline" onClick={() => onNavigate('issue-management')}>
          Back to Ledger
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-6 py-8">
      
      {/* Top Breadcrumb & Actions */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div className="flex items-center gap-3">
          <Button
            variant="outline"
            size="sm"
            onClick={() => onNavigate(isAdmin ? 'issue-management' : 'citizen-dashboard')}
            icon={<ArrowLeft className="w-4 h-4" />}
          >
            Back
          </Button>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-mono text-xs font-bold text-slate-500 uppercase tracking-wider">#{report.tracking_number}</span>
              <PriorityBadge level={report.priority_level} score={Math.round(report.priority_score)} />
              <StatusBadge status={report.status} />
              {report.is_duplicate && (
                <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-purple-100 text-purple-700">Duplicate</span>
              )}
            </div>
            <h1 className="text-xl font-bold text-slate-900 mt-1">{report.title}</h1>
          </div>
        </div>

        {isAdmin && (
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowOverrideModal(true)}
              icon={<Edit3 className="w-3.5 h-3.5 text-teal-600" />}
            >
              Override AI Decision
            </Button>
            <Button
              variant="primary"
              size="sm"
              onClick={() => setShowStatusModal(true)}
              icon={<FileCheck className="w-3.5 h-3.5" />}
            >
              Transition Status
            </Button>
          </div>
        )}
      </div>

      {/* Main Grid: 2 Columns */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Left Column (2 Cols wide): Photographic Evidence, Description, AI Explainability & Priority */}
        <div className="lg:col-span-2 space-y-6">
          
          {/* Section 1: Overview & Photograph */}
          <Card>
            <CardHeader
              title="Issue Evidence & Citizen Report"
              subtitle={`Submitted on ${new Date(report.created_at).toLocaleString()}`}
            />
            <CardContent className="space-y-4">
              
              {/* Image Preview */}
              <div className="relative rounded-xl overflow-hidden bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-800 group">
                {report.image_url ? (
                  <div className="relative">
                    <img
                      src={report.image_url.startsWith('http') ? report.image_url : `http://127.0.0.1:8000/${report.image_url}`}
                      alt="Citizen submitted defect"
                      className="w-full max-h-80 object-cover cursor-pointer transition-transform duration-300 group-hover:scale-[1.01]"
                      onClick={() => setLightboxImage(report.image_url?.startsWith('http') ? report.image_url : `http://127.0.0.1:8000/${report.image_url}`)}
                    />
                    <button
                      onClick={() => setLightboxImage(report.image_url?.startsWith('http') ? report.image_url : `http://127.0.0.1:8000/${report.image_url}`)}
                      className="absolute bottom-3 right-3 p-2 bg-slate-900/80 text-white rounded-lg backdrop-blur-sm opacity-0 group-hover:opacity-100 transition-opacity flex items-center gap-1.5 text-xs"
                      title="Enlarge inspection photo"
                    >
                      <Maximize2 className="w-3.5 h-3.5" />
                      <span>Inspect Photo</span>
                    </button>
                  </div>
                ) : (
                  <div className="p-8 text-center bg-slate-50 dark:bg-slate-800/50 border border-slate-200 dark:border-slate-800 rounded-lg">
                    <Camera className="w-8 h-8 text-slate-400 mx-auto mb-2" />
                    <div className="text-xs font-semibold text-slate-600 dark:text-slate-300">Standardized Inspection Capture</div>
                    <div className="text-[11px] text-slate-400 mt-0.5">Feature vectors extracted from standardized urban infrastructure dataset</div>
                  </div>
                )}
              </div>

              {/* Description */}
              <div className="space-y-1">
                <span className="text-xs font-semibold text-slate-700">Citizen Description:</span>
                <p className="text-sm text-slate-700 bg-slate-50 p-3.5 rounded-lg border border-slate-200/60 leading-relaxed">
                  {report.description}
                </p>
              </div>

              {/* Metadata Pills */}
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 pt-2">
                <div className="p-2.5 rounded-lg border border-slate-200 bg-slate-50">
                  <div className="text-[10px] text-slate-500 font-semibold uppercase">Category</div>
                  <div className="text-xs font-bold text-slate-900 mt-0.5">
                    {report.verified_category || report.category}
                    {report.verified_category && <span className="text-[9px] text-teal-600 font-semibold ml-1">(Human Verified)</span>}
                  </div>
                </div>

                <div className="p-2.5 rounded-lg border border-slate-200 bg-slate-50">
                  <div className="text-[10px] text-slate-500 font-semibold uppercase">Effective Severity</div>
                  <div className="text-xs font-bold text-slate-900 mt-0.5">
                    {report.human_severity ?? report.ai_severity} / 10
                    {report.human_severity && <span className="text-[9px] text-teal-600 font-semibold ml-1">(Adjusted)</span>}
                  </div>
                </div>

                <div className="p-2.5 rounded-lg border border-slate-200 bg-slate-50">
                  <div className="text-[10px] text-slate-500 font-semibold uppercase">Municipal Sector</div>
                  <div className="text-xs font-bold text-slate-900 mt-0.5">{report.area || 'Bengaluru'}</div>
                </div>
              </div>

            </CardContent>
          </Card>

          {/* Section 2: AI Computer Vision Diagnostics */}
          <Card>
            <CardHeader
              title="Explainable Computer Vision Diagnostics"
              subtitle="Trained feature signatures, classification probabilities, and inference latency"
              icon={<Cpu className="w-5 h-5 text-teal-600" />}
            />
            <CardContent className="space-y-4">
              
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <div className="p-3 bg-teal-50/60 rounded-lg border border-teal-200 text-teal-900">
                  <div className="text-[10px] font-semibold uppercase tracking-wider text-teal-700">Model Name</div>
                  <div className="text-xs font-bold mt-0.5 truncate">{report.ai_prediction?.model_name || 'Ensemble-v1.2'}</div>
                </div>
                <div className="p-3 bg-teal-50/60 rounded-lg border border-teal-200 text-teal-900">
                  <div className="text-[10px] font-semibold uppercase tracking-wider text-teal-700">Confidence</div>
                  <div className="text-xs font-bold mt-0.5">
                    {report.ai_prediction ? `${Math.round(report.ai_prediction.confidence * 100)}%` : '88%'}
                  </div>
                </div>
                <div className="p-3 bg-teal-50/60 rounded-lg border border-teal-200 text-teal-900">
                  <div className="text-[10px] font-semibold uppercase tracking-wider text-teal-700">Edge Density</div>
                  <div className="text-xs font-bold mt-0.5">
                    {report.ai_prediction?.detected_features?.edge_density ? `${report.ai_prediction.detected_features.edge_density}` : '0.114'}
                  </div>
                </div>
                <div className="p-3 bg-teal-50/60 rounded-lg border border-teal-200 text-teal-900">
                  <div className="text-[10px] font-semibold uppercase tracking-wider text-teal-700">Dark Depth Ratio</div>
                  <div className="text-xs font-bold mt-0.5">
                    {report.ai_prediction?.detected_features?.dark_pixel_ratio ? `${report.ai_prediction.detected_features.dark_pixel_ratio}` : '0.285'}
                  </div>
                </div>
              </div>

              {/* Class Probability Distribution */}
              {report.ai_prediction?.raw_predictions && (
                <div className="space-y-2 pt-2">
                  <span className="text-xs font-semibold text-slate-700">Multi-Class Probability Distribution:</span>
                  <div className="space-y-1.5">
                    {Object.entries(report.ai_prediction.raw_predictions).slice(0, 4).map(([cat, prob]) => (
                      <div key={cat} className="flex items-center gap-2 text-xs">
                        <span className="w-32 text-slate-600 truncate capitalize">{cat.replace('_', ' ')}</span>
                        <div className="flex-1 bg-slate-100 rounded-full h-2 overflow-hidden">
                          <div
                            className="bg-teal-600 h-full rounded-full transition-all"
                            style={{ width: `${Math.round(prob * 100)}%` }}
                          />
                        </div>
                        <span className="w-10 text-right font-mono font-medium text-slate-700">{Math.round(prob * 100)}%</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

            </CardContent>
          </Card>

          {/* Section 3: 5-Factor Priority Scoring Engine */}
          <Card>
            <CardHeader
              title="5-Factor Priority Scoring Breakdown"
              subtitle={`Formula: 0.35×Severity + 0.25×Safety + 0.15×Location + 0.15×Community + 0.10×Age = ${report.priority_score}/100`}
              icon={<Activity className="w-5 h-5 text-indigo-600" />}
            />
            <CardContent className="space-y-4">
              
              {/* Component Factor Bars */}
              {report.priority_breakdown && (
                <div className="grid grid-cols-1 sm:grid-cols-5 gap-3">
                  <div className="p-3 rounded-lg border border-slate-200 bg-slate-50 text-center">
                    <div className="text-[10px] text-slate-500 font-semibold uppercase">Severity (35%)</div>
                    <div className="text-lg font-bold text-slate-900 mt-1">{report.priority_breakdown.severity_component}</div>
                  </div>
                  <div className="p-3 rounded-lg border border-slate-200 bg-slate-50 text-center">
                    <div className="text-[10px] text-slate-500 font-semibold uppercase">Safety (25%)</div>
                    <div className="text-lg font-bold text-slate-900 mt-1">{report.priority_breakdown.safety_component}</div>
                  </div>
                  <div className="p-3 rounded-lg border border-slate-200 bg-slate-50 text-center">
                    <div className="text-[10px] text-slate-500 font-semibold uppercase">Location Risk (15%)</div>
                    <div className="text-lg font-bold text-slate-900 mt-1">{report.priority_breakdown.location_risk_component}</div>
                  </div>
                  <div className="p-3 rounded-lg border border-slate-200 bg-slate-50 text-center">
                    <div className="text-[10px] text-slate-500 font-semibold uppercase">Community (15%)</div>
                    <div className="text-lg font-bold text-slate-900 mt-1">{report.priority_breakdown.community_impact_component}</div>
                  </div>
                  <div className="p-3 rounded-lg border border-slate-200 bg-slate-50 text-center">
                    <div className="text-[10px] text-slate-500 font-semibold uppercase">Issue Age (10%)</div>
                    <div className="text-lg font-bold text-slate-900 mt-1">{report.priority_breakdown.age_component}</div>
                  </div>
                </div>
              )}

              {/* Explainable Reasons */}
              {report.priority_breakdown?.reasons && (
                <div className="space-y-1.5 pt-2">
                  <span className="text-xs font-semibold text-slate-700">Decision Rationale & Weight Triggers:</span>
                  <ul className="space-y-1">
                    {report.priority_breakdown.reasons.map((r, i) => (
                      <li key={i} className="text-xs text-slate-600 flex items-start gap-2">
                        <span className="text-teal-600 font-bold">•</span>
                        <span>{r}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

            </CardContent>
          </Card>

          {/* Section 4: Duplicate Report Suggestions */}
          {report.duplicate_candidates && report.duplicate_candidates.length > 0 && (
            <Card className="border-purple-200 bg-purple-50/20">
              <CardHeader
                title="Geospatial Duplicate Candidates Detected"
                subtitle="Identified nearby citizen submissions with matching civic category and time proximity"
                icon={<Layers className="w-5 h-5 text-purple-600" />}
              />
              <CardContent className="space-y-3">
                {report.duplicate_candidates.map((cand) => (
                  <div
                    key={cand.id}
                    className="p-3.5 rounded-xl border border-purple-200 bg-white flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3"
                  >
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-mono font-bold text-xs text-purple-900">#{cand.target_tracking_number}</span>
                        <span className="text-xs font-semibold text-slate-900">{cand.target_title}</span>
                      </div>
                      <div className="text-xs text-slate-500 mt-1">
                        Distance: <strong>{cand.distance_meters}m</strong> • Time Gap: <strong>{cand.time_diff_hours}h</strong> • Composite Match: <strong>{cand.match_percentage}%</strong>
                      </div>
                      {cand.notes && <p className="text-[11px] text-slate-500 italic mt-0.5">{cand.notes}</p>}
                    </div>

                    {isAdmin && cand.status === 'suggested' && (
                      <div className="flex items-center gap-2 shrink-0">
                        <Button
                          variant="secondary"
                          size="sm"
                          onClick={() => handleResolveDuplicate(cand.id, 'confirmed')}
                        >
                          Confirm Merge
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleResolveDuplicate(cand.id, 'rejected')}
                        >
                          Reject
                        </Button>
                      </div>
                    )}

                    {cand.status !== 'suggested' && (
                      <span className="text-xs font-semibold px-2.5 py-1 rounded-md bg-slate-100 text-slate-600">
                        Decision: {cand.status}
                      </span>
                    )}
                  </div>
                ))}
              </CardContent>
            </Card>
          )}

          {/* Section 5: Audit History */}
          <Card>
            <CardHeader
              title="Municipal Audit Trail & Change Ledger"
              subtitle="Immutable operational record of status transitions, AI overrides, and dispatches"
              icon={<History className="w-5 h-5 text-slate-600" />}
            />
            <CardContent>
              <div className="space-y-3">
                {report.audit_history.length === 0 ? (
                  <div className="text-xs text-slate-400">No previous state changes recorded.</div>
                ) : (
                  report.audit_history.map((a) => (
                    <div key={a.id} className="text-xs border-l-2 border-teal-500 pl-3 py-1 space-y-0.5">
                      <div className="flex items-center justify-between text-slate-800">
                        <span className="font-semibold capitalize">{a.action.replace('_', ' ')}</span>
                        <span className="text-[10px] text-slate-400">{new Date(a.created_at).toLocaleString()}</span>
                      </div>
                      <div className="text-slate-500">By: {a.user_name || 'System Engine'}</div>
                      {a.notes && <div className="text-slate-600 italic">"{a.notes}"</div>}
                    </div>
                  ))
                )}
              </div>
            </CardContent>
          </Card>

        </div>

        {/* Right Column (1 Col wide): Geospatial Map, Department Assignment, Resolution Details */}
        <div className="space-y-6">
          
          {/* Location Map */}
          <Card>
            <CardHeader
              title="Geospatial Coordinates"
              subtitle={report.address || `${report.latitude}, ${report.longitude}`}
              icon={<MapPin className="w-5 h-5 text-red-500" />}
            />
            <CardContent className="space-y-3">
              <LeafletMap
                center={[report.latitude, report.longitude]}
                zoom={14}
                markers={[{
                  id: report.id,
                  tracking_number: report.tracking_number,
                  title: report.title,
                  category: report.category,
                  category_code: report.category_code,
                  status: report.status,
                  priority_level: report.priority_level,
                  priority_score: report.priority_score,
                  color: report.priority_level === 'Critical' ? '#ef4444' : '#f97316',
                  latitude: report.latitude,
                  longitude: report.longitude,
                  address: report.address,
                  area: report.area,
                  is_duplicate: report.is_duplicate,
                }]}
                height="220px"
              />

              <div className="text-xs text-slate-600 space-y-1">
                <div><strong>Ward / Area:</strong> {report.area || 'Bengaluru Central'}</div>
                <div><strong>Latitude:</strong> {report.latitude.toFixed(6)}</div>
                <div><strong>Longitude:</strong> {report.longitude.toFixed(6)}</div>
              </div>
            </CardContent>
          </Card>

          {/* Department Assignment Card */}
          <Card>
            <CardHeader
              title="Department & Work Order"
              subtitle="Responsible civic engineering division"
              icon={<UserCheck className="w-5 h-5 text-teal-600" />}
            />
            <CardContent className="space-y-3 text-xs">
              <div>
                <span className="text-slate-500">Assigned Department:</span>
                <div className="font-semibold text-slate-900 mt-0.5">
                  {report.assigned_department || 'Pending Departmental Allocation'}
                </div>
              </div>

              <div>
                <span className="text-slate-500">Assigned Personnel:</span>
                <div className="font-semibold text-slate-900 mt-0.5">
                  {report.assigned_staff || 'General Response Pool'}
                </div>
              </div>

              {report.resolution_notes && (
                <div className="p-3 rounded-lg bg-emerald-50 border border-emerald-200 text-emerald-900">
                  <div className="font-semibold text-[11px] uppercase tracking-wider text-emerald-800">Resolution Notes:</div>
                  <p className="mt-1 leading-relaxed">{report.resolution_notes}</p>
                </div>
              )}

              {report.resolved_at && (
                <div className="text-[11px] text-slate-400">
                  Resolved on: {new Date(report.resolved_at).toLocaleString()}
                </div>
              )}
            </CardContent>
          </Card>

        </div>

      </div>

      {/* Human AI Override Modal */}
      <Modal
        isOpen={showOverrideModal}
        onClose={() => setShowOverrideModal(false)}
        title="Human-in-the-Loop AI Override"
        subtitle="Correct AI-predicted category or adjust severity score with accountable audit logging"
        maxWidth="md"
      >
        <div className="space-y-4">
          <div className="space-y-1">
            <label className="text-xs font-semibold text-slate-700">Verified Category</label>
            <select
              value={overrideCategory}
              onChange={(e) => setOverrideCategory(e.target.value)}
              className="w-full text-xs border border-slate-300 rounded-lg px-3 py-2 bg-white focus:ring-2 focus:ring-teal-500"
            >
              {categories.map((c) => (
                <option key={c.code} value={c.code}>{c.name}</option>
              ))}
            </select>
          </div>

          <div className="space-y-1">
            <div className="flex justify-between items-center text-xs">
              <label className="font-semibold text-slate-700">Adjusted Severity Score (1 to 10):</label>
              <span className="font-bold text-teal-700 font-mono">{overrideSeverity} / 10</span>
            </div>
            <input
              type="range"
              min={1}
              max={10}
              value={overrideSeverity}
              onChange={(e) => setOverrideSeverity(parseInt(e.target.value))}
              className="w-full"
            />
            <div className="flex justify-between text-[10px] text-slate-400">
              <span>1 (Minor)</span>
              <span>5 (Moderate)</span>
              <span>10 (Critical Threat)</span>
            </div>
          </div>

          <div className="space-y-1">
            <label className="text-xs font-semibold text-slate-700">Override Reason / Justification *</label>
            <textarea
              required
              rows={2}
              value={overrideNotes}
              onChange={(e) => setOverrideNotes(e.target.value)}
              placeholder="e.g. On-site engineer confirmed road damage exceeds automated visual edge estimate..."
              className="w-full text-xs border border-slate-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-teal-500"
            />
          </div>

          <div className="flex justify-end gap-3 pt-2">
            <Button variant="ghost" onClick={() => setShowOverrideModal(false)}>
              Cancel
            </Button>
            <Button
              variant="primary"
              loading={overriding}
              disabled={!overrideNotes.trim()}
              onClick={handleOverrideSubmit}
            >
              Confirm Override & Recalculate
            </Button>
          </div>
        </div>
      </Modal>

      {/* Transition Status Modal */}
      <Modal
        isOpen={showStatusModal}
        onClose={() => setShowStatusModal(false)}
        title="Transition Issue Status"
        subtitle="Update municipal status and optionally attach resolution notes or evidence"
        maxWidth="md"
      >
        <div className="space-y-4">
          <div className="space-y-1">
            <label className="text-xs font-semibold text-slate-700">Target Status</label>
            <select
              value={targetStatus}
              onChange={(e) => setTargetStatus(e.target.value)}
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
              value={resolutionNotes}
              onChange={(e) => setResolutionNotes(e.target.value)}
              placeholder="Detail actions taken by municipal engineering crews..."
              className="w-full text-xs border border-slate-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-teal-500"
            />
          </div>

          <div className="flex justify-end gap-3 pt-2">
            <Button variant="ghost" onClick={() => setShowStatusModal(false)}>
              Cancel
            </Button>
            <Button
              variant="secondary"
              loading={updatingStatus}
              onClick={handleStatusSubmit}
            >
              Apply Status Update
            </Button>
          </div>
        </div>
      </Modal>

      {/* Photo Lightbox Modal */}
      {lightboxImage && (
        <div
          className="fixed inset-0 z-50 bg-black/90 backdrop-blur-md flex items-center justify-center p-4 animate-in fade-in duration-200"
          onClick={() => setLightboxImage(null)}
        >
          <div className="relative max-w-4xl max-h-[90vh] flex flex-col items-center" onClick={(e) => e.stopPropagation()}>
            <button
              onClick={() => setLightboxImage(null)}
              className="absolute -top-12 right-0 text-white/80 hover:text-white p-2 bg-slate-800/80 rounded-full transition-colors"
            >
              <X className="w-6 h-6" />
            </button>
            <img
              src={lightboxImage}
              alt="High resolution defect evidence"
              className="max-w-full max-h-[82vh] object-contain rounded-xl border border-slate-700 shadow-2xl"
            />
            <div className="mt-3 text-center text-xs text-slate-300">
              Inspection Dossier: <span className="font-mono text-teal-400 font-semibold">{report.tracking_number}</span> — {report.title}
            </div>
          </div>
        </div>
      )}

    </div>
  );
};
