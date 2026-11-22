import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from app.database.connection import Base

def generate_uuid() -> str:
    return str(uuid.uuid4())

class User(Base):
    __tablename__ = "users"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    role = Column(String(50), default="citizen", nullable=False)  # "citizen" or "admin"
    phone = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    reports = relationship("Report", back_populates="citizen", foreign_keys="Report.citizen_id")
    notifications = relationship("Notification", back_populates="user")

class Department(Base):
    __tablename__ = "departments"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(255), unique=True, nullable=False)
    code = Column(String(50), unique=True, nullable=False)
    contact_email = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    categories = relationship("Category", back_populates="default_department")
    staff_members = relationship("Staff", back_populates="department")
    assignments = relationship("Assignment", back_populates="department")

class Staff(Base):
    __tablename__ = "staff"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    department_id = Column(String(36), ForeignKey("departments.id"), nullable=False)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    designation = Column(String(100), nullable=False)
    phone = Column(String(50), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    department = relationship("Department", back_populates="staff_members")
    assignments = relationship("Assignment", back_populates="staff")

class Category(Base):
    __tablename__ = "categories"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    code = Column(String(50), unique=True, nullable=False)  # e.g. "pothole", "garbage"
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    default_department_id = Column(String(36), ForeignKey("departments.id"), nullable=True)
    icon = Column(String(50), default="alert-circle")
    safety_weight = Column(Float, default=0.5)  # 0.1 to 1.0 inherent safety impact
    
    default_department = relationship("Department", back_populates="categories")
    reports = relationship("Report", back_populates="category", foreign_keys="Report.category_id")

class Report(Base):
    __tablename__ = "reports"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    tracking_number = Column(String(50), unique=True, index=True, nullable=False)  # CP-2026-0001
    citizen_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    category_id = Column(String(36), ForeignKey("categories.id"), nullable=False)
    verified_category_id = Column(String(36), ForeignKey("categories.id"), nullable=True)
    
    latitude = Column(Float, nullable=False, index=True)
    longitude = Column(Float, nullable=False, index=True)
    address = Column(String(255), nullable=True)
    area = Column(String(100), nullable=True, index=True)  # Ward or Neighborhood (e.g. "Koramangala")
    
    status = Column(String(50), default="Submitted", index=True, nullable=False)
    # Status transitions: Submitted -> Under Review -> Verified -> Assigned -> In Progress -> Resolved / Rejected
    
    image_url = Column(String(500), nullable=True)
    resolution_image_url = Column(String(500), nullable=True)
    resolution_notes = Column(Text, nullable=True)
    
    ai_severity = Column(Integer, default=5)  # 1 to 10
    human_severity = Column(Integer, nullable=True)
    
    priority_score = Column(Float, default=50.0, index=True)  # 0 to 100
    priority_level = Column(String(20), default="Medium", index=True)  # Low, Medium, High, Critical
    
    is_duplicate = Column(Boolean, default=False, index=True)
    canonical_report_id = Column(String(36), ForeignKey("reports.id"), nullable=True)
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    resolved_at = Column(DateTime, nullable=True)
    
    citizen = relationship("User", back_populates="reports", foreign_keys=[citizen_id])
    category = relationship("Category", back_populates="reports", foreign_keys=[category_id])
    verified_category = relationship("Category", foreign_keys=[verified_category_id])
    
    ai_prediction = relationship("AIPrediction", back_populates="report", uselist=False, cascade="all, delete-orphan")
    priority_record = relationship("PriorityScore", back_populates="report", uselist=False, cascade="all, delete-orphan")
    assignments = relationship("Assignment", back_populates="report", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="report", cascade="all, delete-orphan")
    duplicate_links = relationship("DuplicateCandidate", back_populates="source_report", foreign_keys="DuplicateCandidate.source_report_id", cascade="all, delete-orphan")

class AIPrediction(Base):
    __tablename__ = "ai_predictions"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    report_id = Column(String(36), ForeignKey("reports.id"), nullable=False, unique=True)
    predicted_category_id = Column(String(36), ForeignKey("categories.id"), nullable=False)
    confidence = Column(Float, nullable=False)  # 0.0 to 1.0
    detected_features = Column(JSON, nullable=True)
    raw_predictions = Column(JSON, nullable=True)  # All category probabilities
    model_name = Column(String(100), default="CivicPulse-Vision-Ensemble-v1")
    model_version = Column(String(50), default="1.2.0")
    inference_time_ms = Column(Float, default=45.0)
    processing_status = Column(String(50), default="completed")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    report = relationship("Report", back_populates="ai_prediction")
    predicted_category = relationship("Category")

class PriorityScore(Base):
    __tablename__ = "priority_scores"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    report_id = Column(String(36), ForeignKey("reports.id"), nullable=False, unique=True)
    
    severity_component = Column(Float, nullable=False)
    safety_component = Column(Float, nullable=False)
    location_risk_component = Column(Float, nullable=False)
    community_impact_component = Column(Float, nullable=False)
    age_component = Column(Float, nullable=False)
    
    final_score = Column(Float, nullable=False)  # 0.0 - 100.0
    priority_level = Column(String(20), nullable=False)  # Low, Medium, High, Critical
    explanation_json = Column(JSON, nullable=False)
    scoring_version = Column(String(50), default="v1.0")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    report = relationship("Report", back_populates="priority_record")

class DuplicateCandidate(Base):
    __tablename__ = "duplicate_candidates"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    source_report_id = Column(String(36), ForeignKey("reports.id"), nullable=False)
    target_report_id = Column(String(36), ForeignKey("reports.id"), nullable=False)
    
    distance_meters = Column(Float, nullable=False)
    category_match = Column(Boolean, default=True)
    time_diff_hours = Column(Float, nullable=False)
    visual_similarity = Column(Float, nullable=True)
    composite_score = Column(Float, nullable=False)  # 0.0 to 1.0
    
    status = Column(String(50), default="suggested")  # "suggested", "confirmed", "rejected"
    resolved_by_user_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    source_report = relationship("Report", back_populates="duplicate_links", foreign_keys=[source_report_id])
    target_report = relationship("Report", foreign_keys=[target_report_id])

class Assignment(Base):
    __tablename__ = "assignments"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    report_id = Column(String(36), ForeignKey("reports.id"), nullable=False)
    department_id = Column(String(36), ForeignKey("departments.id"), nullable=False)
    staff_id = Column(String(36), ForeignKey("staff.id"), nullable=True)
    assigned_by_user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    notes = Column(Text, nullable=True)
    status = Column(String(50), default="active")  # active, completed, reassigned
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    report = relationship("Report", back_populates="assignments")
    department = relationship("Department", back_populates="assignments")
    staff = relationship("Staff", back_populates="assignments")

class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    report_id = Column(String(36), ForeignKey("reports.id"), nullable=False)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    action = Column(String(100), nullable=False)  # "status_change", "ai_override", "assignment", "duplicate_merge"
    previous_state = Column(JSON, nullable=True)
    new_state = Column(JSON, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    report = relationship("Report", back_populates="audit_logs")

class Notification(Base):
    __tablename__ = "notifications"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    report_id = Column(String(36), ForeignKey("reports.id"), nullable=True)
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False)
    notification_type = Column(String(50), default="info")  # status_update, critical_alert, assignment
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    user = relationship("User", back_populates="notifications")
