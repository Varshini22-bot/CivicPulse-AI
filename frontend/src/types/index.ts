export interface User {
  id: string;
  email: string;
  full_name: string;
  phone?: string;
  role: 'citizen' | 'admin';
  created_at: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface Category {
  id: string;
  code: string;
  name: string;
  description?: string;
  icon: string;
  safety_weight: number;
}

export interface Staff {
  id: string;
  department_id: string;
  name: string;
  email: string;
  designation: string;
  phone?: string;
  is_active: boolean;
}

export interface Department {
  id: string;
  name: string;
  code: string;
  contact_email?: string;
  phone?: string;
  description?: string;
  staff_members: Staff[];
}

export interface ReportItem {
  id: string;
  tracking_number: string;
  title: string;
  description: string;
  category: string;
  category_code: string;
  verified_category?: string;
  latitude: number;
  longitude: number;
  address?: string;
  area?: string;
  status: 'Submitted' | 'Under Review' | 'Verified' | 'Assigned' | 'In Progress' | 'Resolved' | 'Rejected';
  image_url?: string;
  resolution_image_url?: string;
  ai_severity: number;
  human_severity?: number;
  priority_score: number;
  priority_level: 'Low' | 'Medium' | 'High' | 'Critical';
  is_duplicate: boolean;
  is_synthetic?: boolean;
  upvote_count?: number;
  road_segment_id?: string;
  resolution_verification_status?: string;
  resolution_notes?: string;
  created_at: string;
  updated_at: string;
  resolved_at?: string;
  assigned_department?: string;
  assigned_staff?: string;
}

export interface DetectionBox {
  class_name: string;
  bbox: [number, number, number, number]; // [ymin, xmin, ymax, xmax] normalized [0, 1]
  score: number;
  area?: number;
}

export interface AIPrediction {
  predicted_category_code: string;
  predicted_category_name: string;
  suggested_category_code?: string;
  suggested_category_name?: string;
  confidence: number;
  detections?: DetectionBox[];
  raw_predictions?: Record<string, number>;
  detected_features?: Record<string, any>;
  model_name: string;
  model_version: string;
  inference_time_ms: number;
  processing_status: string;
  policy_note?: string;
  is_overridden?: boolean;
  override_category_code?: string;
}

export interface PriorityBreakdown {
  severity_component: number;
  safety_component: number;
  location_risk_component: number;
  community_impact_component: number;
  age_component: number;
  final_score: number;
  priority_level: string;
  reasons: string[];
  scoring_version: string;
}

export interface DuplicateCandidate {
  id: string;
  source_report_id: string;
  target_report_id: string;
  target_tracking_number: string;
  target_title: string;
  distance_meters: number;
  category_match: boolean;
  time_diff_hours: number;
  composite_score: number;
  match_percentage: number;
  status: 'suggested' | 'confirmed' | 'rejected';
  notes?: string;
}

export interface AuditLog {
  id: string;
  action: string;
  user_name?: string;
  previous_state?: Record<string, any>;
  new_state?: Record<string, any>;
  notes?: string;
  created_at: string;
}

export interface ReportDetail extends ReportItem {
  ai_prediction?: AIPrediction;
  priority_breakdown?: PriorityBreakdown;
  duplicate_candidates: DuplicateCandidate[];
  audit_history: AuditLog[];
  resolution_notes?: string;
}

export interface MapMarker {
  id: string;
  tracking_number: string;
  title: string;
  category: string;
  category_code: string;
  status: string;
  priority_level: string;
  priority_score: number;
  color: string;
  latitude: number;
  longitude: number;
  address?: string;
  area?: string;
  is_duplicate: boolean;
  created_at?: string;
}

export interface Hotspot {
  hotspot_id: string;
  area_name: string;
  center_latitude: number;
  center_longitude: number;
  radius_meters: number;
  total_reports: number;
  dominant_category: string;
  critical_reports: number;
  high_priority_reports: number;
  average_priority_score: number;
  urgency: 'High' | 'Moderate';
  insight_summary: string;
}

export interface OverviewKPIs {
  total_reports: number;
  open_reports: number;
  critical_reports: number;
  resolved_reports: number;
  recent_7_days_reports: number;
  duplicate_reports_detected: number;
  confirmed_duplicates: number;
  resolution_rate_percent: number;
  avg_resolution_time_hours: number;
  avg_resolution_time_days: number;
}

export interface ChartData {
  issues_by_category: { category: string; count: number }[];
  issues_by_priority: { priority: string; count: number }[];
  timeline_trend: { date: string; submitted: number; resolved: number }[];
  issues_by_area: { area: string; count: number }[];
  status_distribution: { status: string; count: number }[];
  avg_time_by_category: { category: string; avg_hours: number; resolved_count: number }[];
  repeated_locations: { area: string; count: number }[];
}

export interface AIMetrics {
  model_name: string;
  version: string;
  status_message?: string;
  total_test_samples: number;
  overall_accuracy: number | null;
  macro_precision: number | null;
  macro_recall: number | null;
  macro_f1: number | null;
  per_class_metrics: Record<string, {
    precision: number | null;
    recall: number | null;
    f1_score: number | null;
    support: number;
  }>;
  classes: string[];
  confusion_matrix: number[][] | null;
  evaluation_status: string;
  evaluated_at?: string;
  note?: string;
}

export interface NotificationItem {
  id: string;
  report_id?: string;
  title: string;
  message: string;
  is_read: boolean;
  notification_type: string;
  created_at: string;
}

export interface PreSubmissionDuplicateCandidate {
  id: string;
  tracking_number: string;
  title: string;
  description: string;
  category: string;
  category_code: string;
  category_match: boolean;
  distance_meters: number;
  time_diff_hours: number;
  image_url?: string;
  status: string;
  upvote_count: number;
}

export interface ResolutionAuditItem {
  id: string;
  tracking_number: string;
  title: string;
  category: string;
  category_code: string;
  area?: string;
  status: string;
  image_url?: string;
  resolution_image_url?: string;
  resolution_verification_status: string;
  verification_score?: number;
  scene_consistency?: number;
  defect_disappeared: boolean;
  reasons: string[];
  resolved_at?: string;
  updated_at: string;
}

export interface RecurringCorridor {
  road_id: string;
  road_name: string;
  highway_type: string;
  ward?: string;
  incident_count: number;
  active_incident_count: number;
  avg_priority_score: number;
  dominant_category: string;
  coordinates: [number, number][];
  root_cause_advisory: string;
  chronic_status: 'severe' | 'moderate' | 'stable';
}

export interface DispatchRouteStop {
  stop_sequence: number;
  report_id: string;
  tracking_number: string;
  title: string;
  category: string;
  priority_score: number;
  priority_level: string;
  latitude: number;
  longitude: number;
  distance_from_prev_km: number;
  transit_minutes_from_prev: number;
  status: string;
}

export interface DispatchRoute {
  total_stops: number;
  total_transit_minutes: number;
  total_transit_km: number;
  stops: DispatchRouteStop[];
}

