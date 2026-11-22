from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from app.core.config import settings

class PriorityService:
    """
    Configurable, explainable issue-priority scoring engine.
    Computes normalized component metrics (0 to 100) and weighted composite score:
    Priority = 0.35*Severity + 0.25*Safety + 0.15*Location + 0.15*Community + 0.10*Age
    """

    SCORING_VERSION = "2.1.0"

    # Known high-risk civic corridors/infrastructure in Bengaluru (simulated municipal zones)
    HIGH_RISK_ZONES = [
        "hospital", "school", "college", "metro", "bus terminal", "railway",
        "market", "pedestrian crossing", "junction", "arterial", "expressway",
        "mg road", "indiranagar 100ft", "koramangala 80ft", "outer ring road"
    ]

    @classmethod
    def calculate_priority(
        cls,
        severity_score: int,  # 1 to 10
        category_safety_weight: float,  # 0.1 to 1.0
        location_text: Optional[str] = "",
        supporting_reports_count: int = 1,
        created_at: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Calculate composite priority score (0 to 100) with explainable component weights.
        """
        reasons: List[str] = []
        
        # 1. Severity component (0 - 100)
        # Severity 1-10 mapped to 10-100
        severity_comp = float(min(10, max(1, severity_score))) * 10.0
        reasons.append(f"Damage severity evaluated at {severity_score}/10 (normalized score: {severity_comp:.1f}).")
        
        # 2. Safety Impact component (0 - 100)
        safety_comp = float(category_safety_weight) * 100.0
        if safety_comp >= 75.0:
            reasons.append(f"Category carries high inherent public hazard risk ({safety_comp:.0f}%).")
        else:
            reasons.append(f"Category standard safety profile applied ({safety_comp:.0f}%).")
            
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
        # 1 report = 20, 2 = 50, 3 = 75, 4+ = 95
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
        # Unresolved issues escalate priority over time
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
            reasons.append(f"SLA breach warning: Unresolved for over a week ({age_hours/24.0:.1f} days active).")

        # Weighted calculation
        final_score = (
            (settings.WEIGHT_SEVERITY * severity_comp) +
            (settings.WEIGHT_SAFETY * safety_comp) +
            (settings.WEIGHT_LOCATION_RISK * location_comp) +
            (settings.WEIGHT_COMMUNITY_IMPACT * community_comp) +
            (settings.WEIGHT_AGE * age_comp)
        )
        
        final_score = round(max(0.0, min(100.0, final_score)), 1)
        
        # Priority Tier mapping
        if final_score < 40.0:
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
                "severity": round(severity_comp, 1),
                "safety": round(safety_comp, 1),
                "location_risk": round(location_comp, 1),
                "community_impact": round(community_comp, 1),
                "issue_age": round(age_comp, 1)
            },
            "weights": {
                "severity": settings.WEIGHT_SEVERITY,
                "safety": settings.WEIGHT_SAFETY,
                "location_risk": settings.WEIGHT_LOCATION_RISK,
                "community_impact": settings.WEIGHT_COMMUNITY_IMPACT,
                "issue_age": settings.WEIGHT_AGE
            },
            "reasons": reasons,
            "scoring_version": cls.SCORING_VERSION,
            "calculated_at": datetime.now(timezone.utc).isoformat()
        }
