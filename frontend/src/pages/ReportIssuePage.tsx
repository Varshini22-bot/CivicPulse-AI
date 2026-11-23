import React, { useState, useEffect, useRef } from 'react';
import {
  Camera, MapPin, Upload, X, AlertTriangle, CheckCircle,
  Cpu, Navigation, FileText, ArrowRight, ShieldCheck, Sparkles, ThumbsUp, Info
} from 'lucide-react';
import { Button } from '../components/ui/Button';
import { Card, CardContent, CardHeader } from '../components/ui/Card';
import { Modal } from '../components/ui/Modal';
import { LeafletMap } from '../components/maps/LeafletMap';
import { useToast } from '../context/ToastContext';
import { api } from '../services/api';
import { Category, ReportDetail, PreSubmissionDuplicateCandidate } from '../types';

interface ReportIssuePageProps {
  onNavigate: (page: string, params?: any) => void;
}

export const ReportIssuePage: React.FC<ReportIssuePageProps> = ({ onNavigate }) => {
  const { showToast } = useToast();
  const [categories, setCategories] = useState<Category[]>([]);
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [categoryCode, setCategoryCode] = useState('pothole');
  const [latitude, setLatitude] = useState(12.9344);
  const [longitude, setLongitude] = useState(77.6256);
  const [gpsAccuracy, setGpsAccuracy] = useState<number | null>(null);
  const [locating, setLocating] = useState(false);
  const [address, setAddress] = useState('80ft Road, 4th Block, Koramangala');
  const [area, setArea] = useState('Koramangala');
  
  // Image handling
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [imagePreview, setImagePreview] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const cameraInputRef = useRef<HTMLInputElement>(null);

  // Pre-submission Duplicate Warning States
  const [duplicateCandidates, setDuplicateCandidates] = useState<PreSubmissionDuplicateCandidate[]>([]);
  const [showDuplicateModal, setShowDuplicateModal] = useState(false);
  const [checkingDuplicates, setCheckingDuplicates] = useState(false);
  const [upvoting, setUpvoting] = useState(false);
  
  // Processing Pipeline States
  const [submitting, setSubmitting] = useState(false);
  const [currentStep, setCurrentStep] = useState<number>(0);
  const [submittedReport, setSubmittedReport] = useState<ReportDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.getCategories().then(setCategories).catch(() => {});
  }, []);

  const handleImageChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      setImageFile(file);
      setImagePreview(URL.createObjectURL(file));
    }
  };

  const removeImage = () => {
    setImageFile(null);
    if (imagePreview) URL.revokeObjectURL(imagePreview);
    setImagePreview(null);
    if (fileInputRef.current) fileInputRef.current.value = '';
    if (cameraInputRef.current) cameraInputRef.current.value = '';
  };

  const setPresetLocation = (name: string, lat: number, lng: number, landmark: string) => {
    setArea(name);
    setLatitude(lat);
    setLongitude(lng);
    setGpsAccuracy(null);
    setAddress(landmark);
  };

  const handleGetCurrentLocation = () => {
    if (!navigator.geolocation) {
      showToast('error', 'Location Error', 'Geolocation is not supported by your browser.');
      return;
    }
    setLocating(true);
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setLocating(false);
        const lat = pos.coords.latitude;
        const lng = pos.coords.longitude;
        const acc = pos.coords.accuracy;
        setLatitude(lat);
        setLongitude(lng);
        setGpsAccuracy(acc);
        setAddress(`GPS Location (${lat.toFixed(5)}, ${lng.toFixed(5)})`);
        setArea('Bengaluru');
        showToast('info', 'GPS Acquired', `Coordinates captured with ±${Math.round(acc)}m accuracy.`);
      },
      (err) => {
        setLocating(false);
        showToast('error', 'Location Failed', err.message || 'Permission denied. Using selected map pin.');
      },
      { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 }
    );
  };

  const executeSubmission = async () => {
    setError(null);
    setSubmitting(true);
    setCurrentStep(1); // Report Submitted

    const formData = new FormData();
    formData.append('title', title);
    formData.append('description', description);
    formData.append('category_code', categoryCode);
    formData.append('latitude', String(latitude));
    formData.append('longitude', String(longitude));
    formData.append('address', address);
    formData.append('area', area);
    if (imageFile) {
      formData.append('image', imageFile);
    }

    try {
      setTimeout(() => setCurrentStep(2), 300); // Image Analysis
      setTimeout(() => setCurrentStep(3), 700); // Classification & Severity
      setTimeout(() => setCurrentStep(4), 1100); // Duplicate Scan & Priority

      const result = await api.submitReport(formData);
      setCurrentStep(5); // Complete
      setSubmittedReport(result);
      showToast('success', 'Civic Report Logged', `Report #${result.tracking_number} triaged as ${result.priority_level} priority.`);
    } catch (err: any) {
      setError(err.message || 'Failed to submit issue report');
      showToast('error', 'Submission Failed', err.message || 'Please check required fields and try again.');
      setSubmitting(false);
      setCurrentStep(0);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setCheckingDuplicates(true);
    try {
      const candidates = await api.checkPresubmissionDuplicates(categoryCode, latitude, longitude);
      if (candidates && candidates.length > 0) {
        setDuplicateCandidates(candidates);
        setShowDuplicateModal(true);
        setCheckingDuplicates(false);
        return;
      }
    } catch (err) {
      // Proceed on non-blocking duplicate check error
    }
    setCheckingDuplicates(false);
    executeSubmission();
  };

  const handleUpvoteAndClose = async (reportId: string) => {
    setUpvoting(true);
    try {
      const res = await api.upvoteReport(reportId);
      showToast('success', 'Issue Supported!', `You supported existing ticket #${res.tracking_number}. Community priority increased.`);
      setShowDuplicateModal(false);
      onNavigate('issue-details', { reportId });
    } catch (err: any) {
      showToast('error', 'Upvote Failed', err.message || 'Could not support existing report.');
    } finally {
      setUpvoting(false);
    }
  };

  const handleReportAnyway = () => {
    setShowDuplicateModal(false);
    executeSubmission();
  };

  return (
    <div className="max-w-4xl mx-auto py-8 px-4 sm:px-6 space-y-8">
      
      {/* Page Title */}
      <div>
        <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Report a Public Infrastructure Issue</h1>
        <p className="text-xs text-slate-500 mt-1">
          Upload photo evidence and pin the location. The CivicPulse AI engine will analyze damage, evaluate safety risk, and dispatch municipal teams.
        </p>
      </div>

      {/* Pre-Submission Duplicate Warning Modal */}
      <Modal
        isOpen={showDuplicateModal}
        onClose={() => setShowDuplicateModal(false)}
        title="Similar Issue Reported Nearby"
        subtitle="To prevent municipal duplicate backlogs, you can support an existing report instead of creating a new one."
        maxWidth="lg"
      >
        <div className="space-y-4 text-left">
          {duplicateCandidates.length > 0 && (
            <div className="p-4 rounded-xl border border-amber-200 bg-amber-50/70 space-y-3">
              <div className="flex items-start gap-3">
                <AlertTriangle className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
                <div>
                  <h4 className="text-sm font-bold text-amber-900">
                    A similar issue was reported {duplicateCandidates[0].distance_meters.toFixed(0)}m away {duplicateCandidates[0].time_diff_hours <= 1 ? 'less than an hour ago' : `${duplicateCandidates[0].time_diff_hours.toFixed(0)} hours ago`}
                  </h4>
                  <p className="text-xs text-amber-700 mt-0.5">
                    Ticket <strong>#{duplicateCandidates[0].tracking_number}</strong>: "{duplicateCandidates[0].title}"
                  </p>
                </div>
              </div>

              {duplicateCandidates[0].image_url && (
                <div className="rounded-lg overflow-hidden border border-amber-200 h-36 bg-slate-100">
                  <img
                    src={duplicateCandidates[0].image_url}
                    alt="Nearby reported issue"
                    className="w-full h-full object-cover"
                  />
                </div>
              )}

              <div className="text-xs text-slate-600 space-y-1 bg-white/80 p-2.5 rounded-lg border border-amber-200/60">
                <div><strong>Category:</strong> {duplicateCandidates[0].category}</div>
                <div><strong>Current Status:</strong> {duplicateCandidates[0].status}</div>
                <div><strong>Citizen Upvotes:</strong> {duplicateCandidates[0].upvote_count} supporter(s)</div>
              </div>
            </div>
          )}

          <div className="flex flex-col sm:flex-row items-center justify-end gap-3 pt-3 border-t border-slate-200">
            <Button
              type="button"
              variant="outline"
              onClick={handleReportAnyway}
              disabled={upvoting}
            >
              Report Anyway (Different Defect)
            </Button>

            {duplicateCandidates.length > 0 && (
              <Button
                type="button"
                variant="primary"
                loading={upvoting}
                onClick={() => handleUpvoteAndClose(duplicateCandidates[0].id)}
                icon={<ThumbsUp className="w-4 h-4" />}
              >
                View & Upvote Existing Report
              </Button>
            )}
          </div>
        </div>
      </Modal>

      {/* Multi-Stage AI Pipeline Processing Overlay Modal */}
      {submitting && (
        <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-2xl border border-slate-200 space-y-6">
            <div className="text-center space-y-2">
              <div className="w-12 h-12 rounded-xl bg-teal-50 border border-teal-200 text-teal-600 mx-auto flex items-center justify-center animate-pulse">
                <Cpu className="w-6 h-6" />
              </div>
              <h3 className="text-lg font-bold text-slate-900">AI Intelligence Pipeline Active</h3>
              <p className="text-xs text-slate-500">Processing report and computing geospatial priority index...</p>
            </div>

            {/* Steps Visualizer */}
            <div className="space-y-3">
              {[
                { step: 1, label: 'Report metadata received & validated' },
                { step: 2, label: 'Computer vision feature extraction running' },
                { step: 3, label: 'Defect classified & severity estimated (1–10)' },
                { step: 4, label: 'Geospatial duplicate detection & radius scan' },
                { step: 5, label: '5-factor priority score assigned' },
              ].map((s) => (
                <div key={s.step} className="flex items-center gap-3 text-xs">
                  {currentStep >= s.step ? (
                    <span className="w-5 h-5 rounded-full bg-emerald-500 text-white flex items-center justify-center font-bold text-[10px]">✓</span>
                  ) : currentStep === s.step - 1 ? (
                    <span className="w-5 h-5 rounded-full border-2 border-teal-500 border-t-transparent animate-spin shrink-0" />
                  ) : (
                    <span className="w-5 h-5 rounded-full bg-slate-200 text-slate-400 flex items-center justify-center font-semibold text-[10px]">{s.step}</span>
                  )}
                  <span className={currentStep >= s.step ? 'font-semibold text-slate-800' : 'text-slate-400'}>
                    {s.label}
                  </span>
                </div>
              ))}
            </div>

            {currentStep === 5 && submittedReport && (
              <div className="pt-4 border-t border-slate-100 space-y-3">
                <div className="p-3 rounded-lg bg-teal-50 border border-teal-200 text-teal-800 text-xs">
                  <div className="font-semibold">Tracking ID: #{submittedReport.tracking_number}</div>
                  <div>AI Category: <strong>{submittedReport.category}</strong> (Confidence: {submittedReport.ai_prediction ? `${Math.round(submittedReport.ai_prediction.confidence * 100)}%` : 'Verified'})</div>
                  <div>Assigned Priority: <strong>{submittedReport.priority_level}</strong> (Score: {submittedReport.priority_score}/100)</div>
                </div>

                <Button
                  variant="primary"
                  className="w-full"
                  onClick={() => onNavigate('issue-details', { reportId: submittedReport.id })}
                  icon={<ArrowRight className="w-4 h-4" />}
                >
                  View Full Issue Tracking Details
                </Button>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Main Submission Form */}
      <form onSubmit={handleSubmit} className="space-y-6">
        
        {error && (
          <div className="p-4 rounded-xl bg-red-50 border border-red-200 text-red-700 text-xs flex items-center gap-2">
            <AlertTriangle className="w-5 h-5 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* Section 1: Issue Overview */}
        <Card>
          <CardHeader title="1. Issue Overview" subtitle="Provide a concise title, category, and thorough description" />
          <CardContent className="space-y-4">
            
            <div className="space-y-1">
              <label htmlFor="report-title-input" className="text-xs font-semibold text-slate-700">Issue Title *</label>
              <input
                id="report-title-input"
                type="text"
                required
                minLength={5}
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="e.g. Hazardous deep pothole on Koramangala 80ft Road near junction"
                className="w-full px-3.5 py-2 text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-teal-500 focus:outline-hidden"
              />
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="space-y-1">
                <div className="flex items-center justify-between">
                  <label htmlFor="report-category-select" className="text-xs font-semibold text-slate-700">Civic Category *</label>
                  <span className="text-[10px] text-teal-700 font-medium">Citizen Choice Authoritative</span>
                </div>
                <select
                  id="report-category-select"
                  value={categoryCode}
                  onChange={(e) => setCategoryCode(e.target.value)}
                  className="w-full px-3.5 py-2 text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-teal-500 focus:outline-hidden bg-white"
                >
                  {categories.map((c) => (
                    <option key={c.code} value={c.code}>
                      {c.name}
                    </option>
                  ))}
                </select>
                <p className="text-[11px] text-slate-500 flex items-center gap-1 mt-1">
                  <Info className="w-3 h-3 text-slate-400 shrink-0" />
                  Your chosen category is authoritative. Municipal AI offers suggestions but will not change your selection without your consent.
                </p>
              </div>

              <div className="space-y-1">
                <label htmlFor="report-area-input" className="text-xs font-semibold text-slate-700">Ward / Neighborhood Area *</label>
                <input
                  id="report-area-input"
                  type="text"
                  required
                  value={area}
                  onChange={(e) => setArea(e.target.value)}
                  placeholder="e.g. Koramangala, Indiranagar, Whitefield"
                  className="w-full px-3.5 py-2 text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-teal-500 focus:outline-hidden"
                />
              </div>
            </div>

            <div className="space-y-1">
              <label htmlFor="report-description-input" className="text-xs font-semibold text-slate-700">Detailed Description *</label>
              <textarea
                id="report-description-input"
                required
                minLength={10}
                rows={3}
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Describe size, depth, water logging, safety hazards to pedestrians/two-wheelers, or nearby landmarks..."
                className="w-full px-3.5 py-2 text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-teal-500 focus:outline-hidden"
              />
            </div>

          </CardContent>
        </Card>

        {/* Section 2: Photo Evidence */}
        <Card>
          <CardHeader title="2. Photographic Evidence" subtitle="Accepted formats: JPG, JPEG, PNG, WEBP (Max 10MB)" />
          <CardContent>
            {imagePreview ? (
              <div className="relative rounded-xl overflow-hidden border border-slate-200 bg-slate-100 max-w-sm">
                <img src={imagePreview} alt="Defect preview" className="w-full h-48 object-cover" />
                <button
                  type="button"
                  onClick={removeImage}
                  aria-label="Remove uploaded image"
                  className="absolute top-2 right-2 p-1.5 rounded-full bg-slate-900/80 text-white hover:bg-slate-900 transition-colors shadow-md"
                >
                  <X className="w-4 h-4" />
                </button>
                <div className="p-2 bg-white text-xs text-slate-600 flex items-center justify-between border-t border-slate-100">
                  <span className="truncate max-w-[200px]">{imageFile?.name}</span>
                  <span className="text-[10px] text-teal-600 font-semibold">Ready for CV Analysis</span>
                </div>
              </div>
            ) : (
              <div className="border-2 border-dashed border-slate-300 rounded-xl p-6 text-center space-y-4 hover:border-teal-500 transition-colors">
                <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
                  <button
                    type="button"
                    onClick={() => cameraInputRef.current?.click()}
                    className="flex items-center gap-2 px-4 py-2.5 rounded-lg bg-teal-50 text-teal-700 font-medium text-xs hover:bg-teal-100 transition-colors border border-teal-200"
                  >
                    <Camera className="w-4 h-4" />
                    <span>Take Photo (Camera)</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => fileInputRef.current?.click()}
                    className="flex items-center gap-2 px-4 py-2.5 rounded-lg bg-slate-100 text-slate-700 font-medium text-xs hover:bg-slate-200 transition-colors border border-slate-300"
                  >
                    <Upload className="w-4 h-4" />
                    <span>Browse Files</span>
                  </button>
                </div>

                <p className="text-xs text-slate-400">
                  Automated computer vision will detect defects and calculate bounding boxes. EXIF metadata is sanitized for privacy.
                </p>

                {/* Hidden file and camera inputs */}
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="image/jpeg,image/png,image/webp,image/jpg"
                  onChange={handleImageChange}
                  className="hidden"
                  aria-label="Browse image files"
                />
                <input
                  ref={cameraInputRef}
                  type="file"
                  accept="image/*"
                  capture="environment"
                  onChange={handleImageChange}
                  className="hidden"
                  aria-label="Capture photo using camera"
                />
              </div>
            )}
          </CardContent>
        </Card>

        {/* Section 3: Geospatial Location Picker */}
        <Card>
          <CardHeader
            title="3. Geospatial Location Picker"
            subtitle="Click on the map or drag the pin to set exact coordinates. Geolocation calculates accuracy circle."
            action={
              <Button
                type="button"
                variant="outline"
                size="sm"
                loading={locating}
                onClick={handleGetCurrentLocation}
                icon={<Navigation className="w-3.5 h-3.5 text-teal-600" />}
              >
                Use My GPS
              </Button>
            }
          />
          <CardContent className="space-y-4">
            
            {/* Quick Landmark Presets */}
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-xs font-semibold text-slate-500">Quick Bengaluru Landmarks:</span>
              <button
                type="button"
                onClick={() => setPresetLocation('Koramangala', 12.9344, 77.6256, '80ft Road, 4th Block, Koramangala')}
                className="px-2.5 py-1 text-xs font-medium rounded-md bg-slate-100 text-slate-700 hover:bg-teal-50 hover:text-teal-700 transition-colors"
              >
                Koramangala
              </button>
              <button
                type="button"
                onClick={() => setPresetLocation('Indiranagar', 12.9784, 77.6408, '100ft Road near Metro Station, Indiranagar')}
                className="px-2.5 py-1 text-xs font-medium rounded-md bg-slate-100 text-slate-700 hover:bg-teal-50 hover:text-teal-700 transition-colors"
              >
                Indiranagar
              </button>
              <button
                type="button"
                onClick={() => setPresetLocation('Whitefield', 12.9698, 77.7500, 'Whitefield Main Road near ITPL Junction')}
                className="px-2.5 py-1 text-xs font-medium rounded-md bg-slate-100 text-slate-700 hover:bg-teal-50 hover:text-teal-700 transition-colors"
              >
                Whitefield
              </button>
              <button
                type="button"
                onClick={() => setPresetLocation('HSR Layout', 12.9121, 77.6446, 'Sector 1, 27th Main, HSR Layout')}
                className="px-2.5 py-1 text-xs font-medium rounded-md bg-slate-100 text-slate-700 hover:bg-teal-50 hover:text-teal-700 transition-colors"
              >
                HSR Layout
              </button>
              <button
                type="button"
                onClick={() => setPresetLocation('CBD / Central', 12.9756, 77.6066, 'MG Road Metro Station Intersection')}
                className="px-2.5 py-1 text-xs font-medium rounded-md bg-slate-100 text-slate-700 hover:bg-teal-50 hover:text-teal-700 transition-colors"
              >
                MG Road / CBD
              </button>
            </div>

            {/* Interactive Leaflet Map Picker */}
            <LeafletMap
              interactivePicker={true}
              selectedLocation={[latitude, longitude]}
              gpsAccuracyMeters={gpsAccuracy}
              center={[latitude, longitude]}
              zoom={13}
              onLocationSelect={(lat, lng) => {
                setLatitude(lat);
                setLongitude(lng);
                setGpsAccuracy(null); // Manual adjustment clears GPS circle
                setAddress(`Coordinates (${lat.toFixed(5)}, ${lng.toFixed(5)})`);
              }}
              height="300px"
            />

            {gpsAccuracy && (
              <div className="flex items-center gap-2 text-xs text-teal-800 bg-teal-50 border border-teal-200 px-3 py-1.5 rounded-lg">
                <Navigation className="w-3.5 h-3.5 text-teal-600" />
                <span>GPS Accuracy: <strong>±{Math.round(gpsAccuracy)} meters</strong>. You can drag the map pin to refine location.</span>
              </div>
            )}

            {/* Selected Coordinates & Address */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-2">
              <div className="space-y-1">
                <label htmlFor="report-latitude-input" className="text-[11px] font-semibold text-slate-600">Latitude</label>
                <input
                  id="report-latitude-input"
                  type="number"
                  step="any"
                  required
                  value={latitude}
                  onChange={(e) => setLatitude(parseFloat(e.target.value))}
                  className="w-full px-3 py-1.5 text-xs font-mono border border-slate-300 rounded-lg bg-slate-50"
                />
              </div>
              <div className="space-y-1">
                <label htmlFor="report-longitude-input" className="text-[11px] font-semibold text-slate-600">Longitude</label>
                <input
                  id="report-longitude-input"
                  type="number"
                  step="any"
                  required
                  value={longitude}
                  onChange={(e) => setLongitude(parseFloat(e.target.value))}
                  className="w-full px-3 py-1.5 text-xs font-mono border border-slate-300 rounded-lg bg-slate-50"
                />
              </div>
              <div className="space-y-1">
                <label htmlFor="report-address-input" className="text-[11px] font-semibold text-slate-600">Physical Address / Landmark</label>
                <input
                  id="report-address-input"
                  type="text"
                  value={address}
                  onChange={(e) => setAddress(e.target.value)}
                  placeholder="Street / Junction description"
                  className="w-full px-3 py-1.5 text-xs border border-slate-300 rounded-lg"
                />
              </div>
            </div>

          </CardContent>
        </Card>

        {/* Submit Button */}
        <div className="flex items-center justify-end gap-4 pt-2">
          <Button
            type="button"
            variant="ghost"
            onClick={() => onNavigate('landing')}
          >
            Cancel
          </Button>
          <Button
            type="submit"
            variant="secondary"
            size="lg"
            loading={submitting || checkingDuplicates}
            icon={<ShieldCheck className="w-5 h-5" />}
          >
            Submit Report & Run AI Triage
          </Button>
        </div>

      </form>
    </div>
  );
};
