from typing import Dict, Any, Optional

class SeverityService:
    """
    Explainable civic physical defect severity estimator (1 to 10 scale).
    Evaluates physical structural disruption, crater/depression depth indicators,
    and surface degradation.

    ORTHOGONAL FACTOR SEPARATION (Eliminates Double Counting):
    Physical defect severity measures the mechanical and structural magnitude of the defect.
    Public hazard and bodily safety threat are evaluated exclusively in PriorityService
    to prevent double counting category risk.
    """

    STRUCTURAL_DAMAGE_KEYWORDS = [
        "deep", "crater", "massive", "collapsed", "wide", "major", "large",
        "severe damage", "broken pieces", "sunken", "extensive", "cavernous"
    ]

    MODERATE_DAMAGE_KEYWORDS = [
        "crack", "uneven", "chipped", "minor hole", "surface damage", "rough"
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
        "other": 4,
        "needs_review": 3
    }

    @classmethod
    def estimate_severity(
        cls,
        category_code: str,
        confidence: float,
        visual_features: Dict[str, Any],
        description: str,
        base_severity: Optional[int] = None,
        db: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        Estimate physical defect severity (1-10) with explainable component breakdown.
        """
        desc_lower = (description or "").lower()

        # 1. Base physical defect magnitude (from category DB config, explicit arg, or fallback)
        if base_severity is not None:
            base = base_severity
        elif db is not None:
            try:
                from app.models import Category
                cat_row = db.query(Category).filter(Category.code == category_code).first()
                base = getattr(cat_row, "base_severity", None) or cls.BASE_CATEGORY_SEVERITY.get(category_code, 5)
            except Exception:
                base = cls.BASE_CATEGORY_SEVERITY.get(category_code, 5)
        else:
            base = cls.BASE_CATEGORY_SEVERITY.get(category_code, 5)

        # 2. Visual damage intensity (0 to +2)
        visual_intensity = 0
        ed = visual_features.get("edge_density", 0.0)
        dp = visual_features.get("dark_pixel_ratio", 0.0)

        if ed > 0.12 or dp > 0.35:
            visual_intensity = 2
        elif ed > 0.07 or dp > 0.20:
            visual_intensity = 1

        # 3. Structural defect extent from description (0 to +2)
        structural_damage = 0
        reasons = []

        if any(w in desc_lower for w in cls.STRUCTURAL_DAMAGE_KEYWORDS):
            structural_damage = 2
            reasons.append("Structural damage descriptors identified in report text (depth/crater/collapse).")
        elif any(w in desc_lower for w in cls.MODERATE_DAMAGE_KEYWORDS):
            structural_damage = 1
            reasons.append("Moderate surface degradation keywords identified.")

        if visual_intensity > 0:
            reasons.append(f"Visual texture intensity index shows marked surface disruption (+{visual_intensity}).")

        # 4. Base severity adjustments
        raw_severity = base + visual_intensity + structural_damage

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

        reasons.append(f"Assigned base physical severity of {base}/10 for category '{category_code}'.")

        return {
            "severity_score": severity_score,
            "severity_label": severity_label,
            "visual_intensity_component": visual_intensity,
            "safety_threat_component": structural_damage,
            "structural_damage_component": structural_damage,
            "explanation": " ".join(reasons)
        }
