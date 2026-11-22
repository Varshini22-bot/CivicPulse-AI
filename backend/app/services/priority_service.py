import os
import json
import math
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple
from app.core.config import settings
from app.services.duplicate_service import DuplicateService


class PriorityService:
    """
    Priority Scoring Engine v2 (Continuous Aging & Spatial POI Proximity).
    Computes normalized component metrics (0 to 100) and weighted composite score:
    Priority = 0.35*Severity + 0.25*Safety + 0.15*Location + 0.15*Community + 0.10*Age

    ORTHOGONAL FACTOR SEPARATION & CONTINUOUS DYNAMICS:
    1. Physical Defect Severity (35%): Measures mechanical/structural magnitude of the defect (1-10 mapped to 10-100).
    2. Public Safety Threat (25%): Measures inherent category hazard and acute danger indicators (0-100).
    3. Location Vulnerability (15%): Spatial proximity to real OpenStreetMap POIs (hospitals, schools, transit interchanges).
    4. Community Impact (15%): Supporting duplicate reports and neighborhood escalation (0-100).
    5. Continuous Issue Age (10%): Saturating asymptotic escalation: P_age = 100 * (1 - e^(-age_hours / tau)).
    """

    SCORING_VERSION = "3.0.0"

    # Time constant tau for continuous saturating age: 72 hours (3 days)
    AGE_TAU_HOURS = 72.0

    HIGH_RISK_KEYWORDS = [
        "hospital", "school", "college", "metro", "bus terminal", "railway",
        "market", "pedestrian crossing", "junction", "arterial", "expressway"
    ]

    ACUTE_HAZARD_KEYWORDS = [
        "accident", "danger", "electric", "live wire", "open manhole", "death",
        "injury", "bleeding", "toxic", "burst", "collapse"
    ]

    _cached_pois: Optional[List[Dict[str, Any]]] = None

    @classmethod
    def _load_pois(cls) -> List[Dict[str, Any]]:
        if cls._cached_pois is not None:
            return cls._cached_pois

        poi_path = "data/osm/bengaluru_pois.json"
        if not os.path.exists(poi_path):
            alt_path = os.path.join("..", poi_path)
            if os.path.exists(alt_path):
                poi_path = alt_path
            else:
                cls._cached_pois = []
                return []

        try:
            with open(poi_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                cls._cached_pois = data.get("pois", [])
        except Exception:
            cls._cached_pois = []

        return cls._cached_pois

    @classmethod
    def compute_continuous_age_score(cls, created_at: Optional[datetime]) -> Tuple[float, float]:
        """
        Computes continuous saturating age score:
        P_age = 100 * (1 - exp(-age_hours / tau))
        Returns (age_hours, score_0_to_100).
        """
        now = datetime.now(timezone.utc)
        if created_at:
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=timezone.utc)
            age_hours = max(0.0, (now - created_at).total_seconds() / 3600.0)
        else:
            age_hours = 0.0

        score = 100.0 * (1.0 - math.exp(-age_hours / cls.AGE_TAU_HOURS))
        return age_hours, round(min(100.0, max(0.0, score)), 1)

    @classmethod
    def compute_location_risk(
        cls,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        location_text: Optional[str] = ""
    ) -> Tuple[float, List[str], List[Dict[str, Any]]]:
        """
        Computes location risk score (0 to 100) using real OpenStreetMap POIs when coordinates exist,
        falling back to text keywords.
        """
        reasons: List[str] = []
        matched_pois: List[Dict[str, Any]] = []
        base_risk = 35.0  # Urban sector baseline

        if latitude is not None and longitude is not None:
            pois = cls._load_pois()
            proximity_bonuses = 0.0

            for poi in pois:
                p_lat = poi.get("latitude")
                p_lon = poi.get("longitude")
                if p_lat is None or p_lon is None:
                    continue

                dist = DuplicateService.haversine_distance(latitude, longitude, p_lat, p_lon)
                category = poi.get("category", "")
                name = poi.get("name", "POI")
                buffer = poi.get("buffer_meters", 250.0)

                if dist <= buffer:
                    bonus = 0.0
                    if category == "hospital":
                        bonus = 35.0 if dist <= 100.0 else 25.0
                    elif category == "school":
                        bonus = 30.0 if dist <= 100.0 else 20.0
                    elif category == "transit_station":
                        bonus = 30.0 if dist <= 150.0 else 18.0
                    else:
                        bonus = 15.0

                    proximity_bonuses = max(proximity_bonuses, bonus)
                    matched_pois.append({
                        "name": name,
                        "category": category,
                        "distance_meters": round(dist, 1),
                        "bonus_applied": bonus
                    })

            if matched_pois:
                score = min(100.0, base_risk + proximity_bonuses)
                nearest = min(matched_pois, key=lambda x: x["distance_meters"])
                reasons.append(
                    f"OSM Proximity: Located {nearest['distance_meters']:.0f}m from {nearest['name']} "
                    f"({nearest['category'].replace('_', ' ')} zone, +{nearest['bonus_applied']:.0f}% risk)."
                )
                return round(score, 1), reasons, matched_pois

        # Fallback to address keywords if coordinates not near loaded POIs or missing
        loc_lower = (location_text or "").lower()
        matched_keyword = None
        for kw in cls.HIGH_RISK_KEYWORDS:
            if kw in loc_lower:
                matched_keyword = kw
                break

        if matched_keyword:
            score = 85.0
            reasons.append(f"Identified critical public transit / pedestrian zone near '{matched_keyword}'.")
        elif location_text:
            score = 45.0
            reasons.append("Standard municipal residential/commercial sector location risk.")
        else:
            score = 30.0
            reasons.append("Specific location context absent; default baseline risk applied.")

        return score, reasons, []

    @classmethod
    def calculate_priority(
        cls,
        severity_score: int,  # 1 to 10 (Physical Defect Severity)
        category_safety_weight: float,  # 0.1 to 1.0 (Public Safety Profile)
        location_text: Optional[str] = "",
        supporting_reports_count: int = 1,
        created_at: Optional[datetime] = None,
        description: Optional[str] = "",
        latitude: Optional[float] = None,
        longitude: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Calculate composite priority score (0 to 100) with explainable component weights.
        """
        reasons: List[str] = []

        # 1. Physical Defect Severity component (0 - 100)
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

        # 3. Location Risk component (0 - 100) with real POIs
        location_comp, loc_reasons, matched_pois = cls.compute_location_risk(
            latitude=latitude,
            longitude=longitude,
            location_text=location_text
        )
        reasons.extend(loc_reasons)

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

        # 5. Continuous Issue Age component (0 - 100): P_age = 100 * (1 - e^(-age_hours / 72))
        age_hours, age_comp = cls.compute_continuous_age_score(created_at)
        reasons.append(f"Continuous issue aging: active for {age_hours:.1f} hours (saturating escalation score: {age_comp:.1f}/100).")

        # Composite Score Calculation (Normalized Weights)
        # Weights: Severity=0.35, Safety=0.25, Location=0.15, Community=0.15, Age=0.10
        raw_final = (
            (settings.WEIGHT_SEVERITY * severity_comp) +
            (settings.WEIGHT_SAFETY * safety_comp) +
            (settings.WEIGHT_LOCATION_RISK * location_comp) +
            (settings.WEIGHT_COMMUNITY_IMPACT * community_comp) +
            (settings.WEIGHT_AGE * age_comp)
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
            "scoring_version": cls.SCORING_VERSION,
            "components": {
                "severity": round(severity_comp, 1),
                "safety": round(safety_comp, 1),
                "location_risk": round(location_comp, 1),
                "community_impact": round(community_comp, 1),
                "issue_age": round(age_comp, 1),
                "age_hours": round(age_hours, 1)
            },
            "weights": {
                "severity": settings.WEIGHT_SEVERITY,
                "safety": settings.WEIGHT_SAFETY,
                "location_risk": settings.WEIGHT_LOCATION_RISK,
                "community_impact": settings.WEIGHT_COMMUNITY_IMPACT,
                "age": settings.WEIGHT_AGE
            },
            "matched_pois": matched_pois,
            "reasons": reasons
        }
