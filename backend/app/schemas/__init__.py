from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, EmailStr, Field, ConfigDict

# --- Auth Schemas ---
class UserBase(BaseModel):
    email: EmailStr
    full_name: str
    phone: Optional[str] = None
    role: str = "citizen"

class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)
    full_name: str
    phone: Optional[str] = None
    role: Optional[str] = "citizen"

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserOut(UserBase):
    id: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut

# --- Category & Department Schemas ---
class CategoryOut(BaseModel):
    id: str
    code: str
    name: str
    description: Optional[str] = None
    icon: str
    safety_weight: float
    base_severity: int = 5
    keywords: List[str] = []
    model_config = ConfigDict(from_attributes=True)

class StaffOut(BaseModel):
    id: str
    department_id: str
    name: str
    email: str
    designation: str
    phone: Optional[str] = None
    is_active: bool
    model_config = ConfigDict(from_attributes=True)

class DepartmentOut(BaseModel):
    id: str
    name: str
    code: str
    contact_email: Optional[str] = None
    phone: Optional[str] = None
    description: Optional[str] = None
    staff_members: List[StaffOut] = []
    model_config = ConfigDict(from_attributes=True)

# --- AI & Priority Schemas ---
class AIPredictionOut(BaseModel):
    predicted_category_code: str
    predicted_category_name: str
    confidence: float
    raw_predictions: Optional[Dict[str, float]] = None
    detected_features: Optional[Dict[str, Any]] = None
    model_name: str
    model_version: str
    inference_time_ms: float
    processing_status: str

class PriorityScoreOut(BaseModel):
    severity_component: float
    safety_component: float
    location_risk_component: float
    community_impact_component: float
    age_component: float
    final_score: float
    priority_level: str
    reasons: List[str] = []
    scoring_version: str

# --- Audit & History ---
class AuditLogOut(BaseModel):
    id: str
    action: str
    user_name: Optional[str] = "System / AI"
    previous_state: Optional[Dict[str, Any]] = None
    new_state: Optional[Dict[str, Any]] = None
    notes: Optional[str] = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class DuplicateCandidateOut(BaseModel):
    id: str
    source_report_id: str
    target_report_id: str
    target_tracking_number: str
    target_title: str
    distance_meters: float
    category_match: bool
    time_diff_hours: float
    composite_score: float
    match_percentage: int
    status: str
    notes: Optional[str] = None

# --- Report Schemas ---
class ReportCreate(BaseModel):
    title: str = Field(..., min_length=5, max_length=255)
    description: str = Field(..., min_length=10)
    category_code: str
    latitude: float
    longitude: float
    address: Optional[str] = None
    area: Optional[str] = None

class ReportListItemOut(BaseModel):
    id: str
    tracking_number: str
    title: str
    description: str
    category: str
    category_code: str
    verified_category: Optional[str] = None
    latitude: float
    longitude: float
    address: Optional[str] = None
    area: Optional[str] = None
    status: str
    image_url: Optional[str] = None
    resolution_image_url: Optional[str] = None
    ai_severity: int
    human_severity: Optional[int] = None
    priority_score: float
    priority_level: str
    is_duplicate: bool
    is_synthetic: bool = False
    created_at: datetime
    updated_at: datetime
    resolved_at: Optional[datetime] = None
    assigned_department: Optional[str] = None
    assigned_staff: Optional[str] = None

class ReportDetailOut(ReportListItemOut):
    ai_prediction: Optional[AIPredictionOut] = None
    priority_breakdown: Optional[PriorityScoreOut] = None
    duplicate_candidates: List[DuplicateCandidateOut] = []
    audit_history: List[AuditLogOut] = []
    resolution_notes: Optional[str] = None

# --- Action Payloads ---
class StatusUpdateRequest(BaseModel):
    status: str
    notes: Optional[str] = None
    resolution_image_url: Optional[str] = None

class AIOverrideRequest(BaseModel):
    verified_category_code: Optional[str] = None
    human_severity: Optional[int] = Field(None, ge=1, le=10)
    notes: Optional[str] = None

class AssignmentRequest(BaseModel):
    department_id: str
    staff_id: Optional[str] = None
    notes: Optional[str] = None

class DuplicateActionRequest(BaseModel):
    status: str = Field(..., pattern="^(confirmed|rejected)$")
    notes: Optional[str] = None
