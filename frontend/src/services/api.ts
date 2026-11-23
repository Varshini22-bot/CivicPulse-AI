import {
  AuthResponse, User, Category, ReportItem, ReportDetail,
  MapMarker, Hotspot, OverviewKPIs, ChartData, AIMetrics,
  Department, DuplicateCandidate, NotificationItem,
  PreSubmissionDuplicateCandidate, ResolutionAuditItem, RecurringCorridor, DispatchRoute
} from '../types';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000/api';

class ApiService {
  private getToken(): string | null {
    return localStorage.getItem('civicpulse_token');
  }

  private async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const token = this.getToken();
    const headers: Record<string, string> = {
      ...(options.headers as Record<string, string> || {}),
    };

    if (token && !headers['Authorization']) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    if (!(options.body instanceof FormData) && !headers['Content-Type']) {
      headers['Content-Type'] = 'application/json';
    }

    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      ...options,
      headers,
    });

    if (!response.ok) {
      let errorMsg = `Error ${response.status}: ${response.statusText}`;
      try {
        const errorData = await response.json();
        if (errorData.detail) {
          errorMsg = typeof errorData.detail === 'string' ? errorData.detail : JSON.stringify(errorData.detail);
        }
      } catch (e) {
        // Fallback to text
      }
      throw new Error(errorMsg);
    }

    // For file downloads or text response
    const contentType = response.headers.get('content-type');
    if (contentType && contentType.includes('text/csv')) {
      return (await response.text()) as unknown as T;
    }

    return response.json();
  }

  // --- Auth ---
  async login(email: string, password: string): Promise<AuthResponse> {
    const res = await this.request<AuthResponse>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });
    localStorage.setItem('civicpulse_token', res.access_token);
    localStorage.setItem('civicpulse_user', JSON.stringify(res.user));
    return res;
  }

  async register(data: { email: string; password: string; full_name: string; phone?: string; role?: string }): Promise<AuthResponse> {
    const res = await this.request<AuthResponse>('/auth/register', {
      method: 'POST',
      body: JSON.stringify(data),
    });
    localStorage.setItem('civicpulse_token', res.access_token);
    localStorage.setItem('civicpulse_user', JSON.stringify(res.user));
    return res;
  }

  async getMe(): Promise<User> {
    return this.request<User>('/auth/me');
  }

  logout(): void {
    localStorage.removeItem('civicpulse_token');
    localStorage.removeItem('civicpulse_user');
  }

  getCurrentUser(): User | null {
    const userStr = localStorage.getItem('civicpulse_user');
    if (!userStr) return null;
    try {
      return JSON.parse(userStr);
    } catch {
      return null;
    }
  }

  // --- Categories & Reports ---
  async getCategories(): Promise<Category[]> {
    return this.request<Category[]>('/reports/categories');
  }

  async submitReport(formData: FormData): Promise<ReportDetail> {
    return this.request<ReportDetail>('/reports', {
      method: 'POST',
      body: formData,
    });
  }

  async getMyReports(): Promise<ReportItem[]> {
    return this.request<ReportItem[]>('/reports/my');
  }

  async getReportById(id: string): Promise<ReportDetail> {
    return this.request<ReportDetail>(`/reports/${id}`);
  }

  async withdrawReport(id: string): Promise<ReportDetail> {
    return this.request<ReportDetail>(`/reports/${id}/withdraw`, {
      method: 'POST',
    });
  }

  async trackReportByNumber(trackingNumber: string): Promise<ReportDetail> {
    return this.request<ReportDetail>(`/reports/track/${encodeURIComponent(trackingNumber)}`);
  }

  async checkPresubmissionDuplicates(categoryCode: string, latitude: number, longitude: number): Promise<PreSubmissionDuplicateCandidate[]> {
    return this.request<PreSubmissionDuplicateCandidate[]>('/reports/check-duplicate', {
      method: 'POST',
      body: JSON.stringify({ category_code: categoryCode, latitude, longitude }),
    });
  }

  async upvoteReport(reportId: string): Promise<ReportDetail> {
    return this.request<ReportDetail>(`/reports/${reportId}/upvote`, {
      method: 'POST',
    });
  }

  // --- Admin Operations ---
  async getAdminReports(params: {
    status?: string;
    priority?: string;
    category_id?: string;
    area?: string;
    search?: string;
    sort_by?: string;
    sort_dir?: string;
    page?: number;
    limit?: number;
  } = {}): Promise<{ items: ReportItem[]; total: number; page: number; limit: number; total_pages: number }> {
    const query = new URLSearchParams();
    Object.entries(params).forEach(([key, val]) => {
      if (val !== undefined && val !== null && val !== '') {
        query.append(key, String(val));
      }
    });
    return this.request(`/admin/reports?${query.toString()}`);
  }

  async updateReportStatus(id: string, status: string, notes?: string, resolution_image_url?: string): Promise<ReportDetail> {
    return this.request<ReportDetail>(`/admin/reports/${id}/status`, {
      method: 'PATCH',
      body: JSON.stringify({ status, notes, resolution_image_url }),
    });
  }

  async overrideAIPrediction(id: string, verified_category_code?: string, human_severity?: number, notes?: string): Promise<ReportDetail> {
    return this.request<ReportDetail>(`/admin/reports/${id}/override`, {
      method: 'POST',
      body: JSON.stringify({ verified_category_code, human_severity, notes }),
    });
  }

  async assignReport(id: string, department_id: string, staff_id?: string, notes?: string): Promise<ReportDetail> {
    return this.request<ReportDetail>(`/admin/reports/${id}/assign`, {
      method: 'POST',
      body: JSON.stringify({ department_id, staff_id, notes }),
    });
  }

  async getDepartments(): Promise<Department[]> {
    return this.request<Department[]>('/admin/departments');
  }

  async executeBulkAction(payload: {
    report_ids: string[];
    action: 'change_status' | 'assign_department' | 'mark_duplicate';
    status?: string;
    department_id?: string;
    canonical_report_id?: string;
    notes?: string;
  }): Promise<{ status: string; action: string; affected_count: number }> {
    return this.request('/admin/reports/bulk-action', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  async getResolutionAuditQueue(): Promise<ResolutionAuditItem[]> {
    return this.request<ResolutionAuditItem[]>('/admin/resolution-audit');
  }

  async auditResolutionDecision(reportId: string, decision: 'confirm' | 'reject_reopen', notes?: string): Promise<ReportDetail> {
    return this.request<ReportDetail>(`/admin/reports/${reportId}/audit-resolution`, {
      method: 'POST',
      body: JSON.stringify({ decision, notes }),
    });
  }

  // --- Duplicates ---
  async getDuplicateCandidates(): Promise<any[]> {
    return this.request<any[]>('/admin/duplicates');
  }

  async resolveDuplicate(candidate_id: string, status: 'confirmed' | 'rejected', notes?: string): Promise<any> {
    return this.request(`/admin/duplicates/${candidate_id}/resolve`, {
      method: 'POST',
      body: JSON.stringify({ status, notes }),
    });
  }

  // --- Map ---
  async getMapReports(params: { category_id?: string; priority?: string; status?: string; area?: string } = {}): Promise<MapMarker[]> {
    const query = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => {
      if (v) query.append(k, v);
    });
    return this.request<MapMarker[]>(`/map/reports?${query.toString()}`);
  }

  async getHotspots(eps_meters: number = 800, min_samples: number = 3): Promise<Hotspot[]> {
    return this.request<Hotspot[]>(`/map/hotspots?eps_meters=${eps_meters}&min_samples=${min_samples}`);
  }

  async getHotspotsV2(cluster_method: 'hdbscan' | 'dbscan' = 'hdbscan', half_life_days: number = 14, min_samples: number = 3): Promise<Hotspot[]> {
    return this.request<Hotspot[]>(`/map/hotspots-v2?cluster_method=${cluster_method}&half_life_days=${half_life_days}&min_samples=${min_samples}`);
  }

  async getRecurringCorridors(): Promise<RecurringCorridor[]> {
    return this.request<RecurringCorridor[]>('/map/recurring-corridors');
  }

  async getDispatchRoute(params: { start_lat?: number; start_lon?: number; max_stops?: number; ward?: string } = {}): Promise<DispatchRoute> {
    const query = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== '') query.append(k, String(v));
    });
    return this.request<DispatchRoute>(`/map/dispatch-route?${query.toString()}`);
  }

  async getNearbyReports(latitude: number, longitude: number, radius_meters: number = 1000): Promise<any[]> {
    return this.request<any[]>(`/map/nearby?latitude=${latitude}&longitude=${longitude}&radius_meters=${radius_meters}`);
  }

  // --- Analytics & Export ---
  async getKPIs(params: { category_id?: string; priority?: string; area?: string; days?: number } = {}): Promise<OverviewKPIs> {
    const query = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== '') query.append(k, String(v));
    });
    return this.request<OverviewKPIs>(`/analytics/kpis?${query.toString()}`);
  }

  async getCharts(params: { category_id?: string; priority?: string; area?: string; days?: number } = {}): Promise<ChartData> {
    const query = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== '') query.append(k, String(v));
    });
    return this.request<ChartData>(`/analytics/charts?${query.toString()}`);
  }

  async getAIMetrics(): Promise<AIMetrics> {
    return this.request<AIMetrics>('/analytics/ai-metrics');
  }

  getExportUrl(params: { category_id?: string; priority?: string; status?: string; area?: string } = {}): string {
    const query = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => {
      if (v) query.append(k, v);
    });
    return `${API_BASE_URL}/analytics/export?${query.toString()}`;
  }

  // --- Notifications ---
  async getNotifications(): Promise<NotificationItem[]> {
    return this.request<NotificationItem[]>('/notifications');
  }

  async markNotificationRead(id: string): Promise<any> {
    return this.request(`/notifications/${id}/read`, { method: 'PATCH' });
  }

  async markAllNotificationsRead(): Promise<any> {
    return this.request('/notifications/read-all', { method: 'POST' });
  }

  // --- System / Maintenance ---
  async resetDemoData(): Promise<{ status: string; message: string }> {
    return this.request<{ status: string; message: string }>('/admin/reset-demo-data', {
      method: 'POST',
    });
  }
}

export const api = new ApiService();
