from typing import Dict, Any, Optional

class SeverityService:
    """
    Transparent, explainable civic severity estimator (1 to 10 scale).
    Combines visual damage intensity, obstruction risk, environmental safety threat,
    and user-described urgency signals.
    """

    CRITICAL_KEYWORDS = [
        "collapse", "accident", "danger", "burst", "electric", "live wire", "crater",
        "deep", "open manhole", "death", "severe", "major", "toxic", "injury", "bleeding"
    ]

    MODERATE_KEYWORDS = [
        "overflow", "leak", "stuck", "broken", "cracked", "smell", "dark", "traffic slow"
    ]

    BASE_CATEGORY_SEVERITY = {
        "pothole": 6,
        "road_damage": 5,
        "garbage_overflow": 4,
        "illegal_dumping": 6,
        "water_leakage": 5,
        "blocked_drain": 6,
        "broken_streetlight": 4,
        "damaged_infrastructure": 6,
        "needs_review": 3
    }

    @classmethod
    def estimate_severity(
        cls,
        category_code: str,
        confidence: float,
        visual_features: Dict[str, Any],
        description: str
    ) -> Dict[str, Any]:
        """
        Estimate severity (1-10) with explainable component breakdown.
        """
        desc_lower = (description or "").lower()
        base = cls.BASE_CATEGORY_SEVERITY.get(category_code, 4)
        
        # 1. Visual damage intensity (0 to +2)
        visual_intensity = 0
        ed = visual_features.get("edge_density", 0.0)
        dp = visual_features.get("dark_pixel_ratio", 0.0)
        
        if ed > 0.12 or dp > 0.35:
            visual_intensity = 2
        elif ed > 0.07 or dp > 0.20:
            visual_intensity = 1
            
        # 2. Obstruction & safety threat analysis from text (0 to +3)
        safety_threat = 0
        reasons = []
        
        if any(w in desc_lower for w in cls.CRITICAL_KEYWORDS):
            safety_threat += 3
            reasons.append("High-risk safety keywords detected in report description (danger/accident/rupture).")
        elif any(w in desc_lower for w in cls.MODERATE_KEYWORDS):
            safety_threat += 1
            reasons.append("Moderate civic obstruction keywords identified.")
            
        if visual_intensity > 0:
            reasons.append(f"Visual texture intensity index shows marked surface disruption (+{visual_intensity}).")
            
        # 3. Base severity adjustments
        raw_severity = base + visual_intensity + safety_threat
        
        # Adjust for confidence (if model is uncertain, dampen extreme values towards moderate)
        if confidence < 0.40:
            raw_severity = max(3, min(raw_severity, 5))
            reasons.append("Confidence below 40%; severity moderated pending municipal on-site verification.")
            
        # Clamp to 1 - 10
        severity_score = max(1, min(10, int(round(raw_severity))))
        
        # Determine classification label
        if severity_score <= 3:
            severity_label = "Minor"
        elif severity_score <= 6:
            severity_label = "Moderate"
        elif severity_score <= 8:
            severity_label = "Severe"
        else:
            severity_label = "Critical"
            
        reasons.append(f"Assigned base category default severity of {base}/10 for '{category_code}'.")
        
        return {
            "severity_score": severity_score,
            "severity_label": severity_label,
            "visual_intensity_component": visual_intensity,
            "safety_threat_component": safety_threat,
            "explanation": " ".join(reasons)
        }
