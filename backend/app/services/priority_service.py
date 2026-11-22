from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from app.core.config import settings

class PriorityService:
    """
    Configurable, explainable issue-priority scoring engine.
    Computes normalized component metrics (0 to 100) and weighted composite score:
    Priority = 0.35*Severity + 0.25*Safety + 0.15*Location + 0.15*Community + 0.10*Age

    ORTHOGONAL FACTOR SEPARATION (Eliminates Double Counting):
    1. Physical Defect Severity (35%): Measures mechanical/structural magnitude of the defect (1-10 mapped to 10-100).
       Evaluated independently of hazard/safety risk.
    2. Public Safety Threat (25%): Measures inherent category hazard and acute danger to human life / bodily harm (0-100).
       Category safety hazard profile is evaluated exclusively here.
    3. Location Vulnerability (15%): Proximity to schools, hospitals, transit hubs, and arterial corridors (0-100).
    4. Community Impact (15%): Citizen escalations and verified duplicate clusters (0-100).
    5. Issue Age (10%): SLA turnaround urgency escalation over time (0-100).
    """

    SCORING_VERSION = "2.2.0"

    # Known high-risk civic corridors/infrastructure in Bengaluru (simulated municipal zones)
    HIGH_RISK_ZONES = [
        "hospital", "school", "college", "metro", "bus terminal", "railway",
        "market", "pedestrian crossing", "junction", "arterial", "expressway",
        "mg road", "indiranagar 100ft", "koramangala 80ft", "outer ring road"
    ]

    ACUTE_HAZARD_KEYWORDS = [
        "accident", "danger", "electric", "live wire", "open manhole", "death",
        "injury", "bleeding", "toxic", "burst", "collapse"
    ]

    @classmethod
    def calculate_priority(
        cls,
        severity_score: int,  # 1 to 10 (Physical Defect Severity)
        category_safety_weight: float,  # 0.1 to 1.0 (Public Safety Profile)
        location_text: Optional[str] = "",
        supporting_reports_count: int = 1,
        created_at: Optional[datetime] = None,
        description: Optional[str] = ""
    ) -> Dict[str, Any]:
        """
        Calculate composite priority score (0 to 100) with explainable component weights.
        """
        reasons: List[str] = []

        # 1. Physical Defect Severity component (0 - 100)
        # Severity 1-10 mapped to 10-100
        severity_comp = float(min(10, max(1, severity_score))) * 10.0
        reasons.append(f"Physical defect severity evaluated at {severity_score}/10 (normalized score: {severity_comp:.1f}).")

        # 2. Public Safety Threat component (0 - 100)
        base_safety = float(category_safety_weight) * 100.0
        desc_lower = (description or "").lower()
        has_acute_hazard = any(w in desc_lower for w in cls.ACUTE_HAZARD_KEYWORDS)

        if has_acute_hazard:
            safety_comp = min(100.0, base_safety + 15.0)
            reasons.append(f"Public safety threat: Category hazard ({base_safety:.0f}%) elevated by acute danger indicators in report (+15% -> {safety_comp:.0f}%).")
        elif base_safety >= 75.0:
            safety_comp = base_safety
            reasons.append(f"Public safety threat: High inherent category public hazard profile applied ({safety_comp:.0f}%).")
        else:
            safety_comp = base_safety
            reasons.append(f"Public safety threat: Standard category safety profile applied ({safety_comp:.0f}%).")

        # 3. Location Risk component (0 - 100)
        loc_lower = (location_text or "").lower()
        has_location_risk = False
        location_comp = 40.0  # Default neutral urban baseline

        for zone in cls.HIGH_RISK_ZONES:
            if zone in loc_lower:
                location_comp = 85.0
                has_location_risk = True
                reasons.append(f"Identified critical public transit / pedestrian zone near '{zone}'.")
                break

        if not has_location_risk:
            if location_text:
                location_comp = 45.0
                reasons.append("Standard municipal residential/commercial sector location risk.")
            else:
                location_comp = 30.0
                reasons.append("Specific location context absent; default baseline risk applied.")

        # 4. Community Impact (duplicate / recurring report count) (0 - 100)
        if supporting_reports_count <= 1:
            community_comp = 25.0
            reasons.append("Single citizen report filed (community impact baseline: 25).")
        elif supporting_reports_count == 2:
            community_comp = 55.0
            reasons.append("Confirmed 2 independent citizen reports regarding this issue.")
        elif supporting_reports_count == 3:
            community_comp = 80.0
            reasons.append("Multiple citizens (3 reports) flagged this cluster.")
        else:
            community_comp = 98.0
            reasons.append(f"Significant community escalation ({supporting_reports_count} reports filed in vicinity).")

        # 5. Issue Age component (0 - 100)
        now = datetime.now(timezone.utc)
        if created_at:
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=timezone.utc)
            age_hours = (now - created_at).total_seconds() / 3600.0
        else:
            age_hours = 0.0

        if age_hours < 24.0:
            age_comp = 20.0
            reasons.append(f"Reported recently ({age_hours:.1f} hours ago).")
        elif age_hours < 72.0:
            age_comp = 50.0
            reasons.append(f"Pending resolution for {age_hours/24.0:.1f} days.")
        elif age_hours < 168.0:
            age_comp = 75.0
            reasons.append(f"Exceeding standard 3-day turnaround ({age_hours/24.0:.1f} days active).")
        else:
            age_comp = 95.0
            reasons.append(f"Critical turnaround delay ({age_hours/24.0:.1f} days unresolved).")

        # Composite Score Calculation (Normalized Weights)
        # Weights: Severity=0.35, Safety=0.25, Location=0.15, Community=0.15, Age=0.10
        raw_final = (
            (0.35 * severity_comp) +
            (0.25 * safety_comp) +
            (0.15 * location_comp) +
            (0.15 * community_comp) +
            (0.10 * age_comp)
        )
        final_score = round(max(0.0, min(100.0, raw_final)), 1)

        # Priority Level Thresholds
        if final_score < 35.0:
            priority_level = "Low"
        elif final_score < 60.0:
            priority_level = "Medium"
        elif final_score < 80.0:
            priority_level = "High"
        else:
            priority_level = "Critical"

        return {
            "final_score": final_score,
            "priority_level": priority_level,
            "components": {
                "severity": severity_comp,
                "safety": safety_comp,
                "location_risk": location_comp,
                "community_impact": community_comp,
                "issue_age": age_comp
            },
            "weights": {
                "severity": 0.35,
                "safety": 0.25,
                "location_risk": 0.15,
                "community_impact": 0.15,
                "issue_age": 0.10
            },
            "reasons": reasons,
            "scoring_version": cls.SCORING_VERSION
        }
