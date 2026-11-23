"""
scripts/sync_constants.py
=========================
Single source of truth generator for CivicPulse AI system constants.
Extracts configuration parameters directly from backend/app/core/config.py
and formats canonical Markdown tables for README.md, MODEL_CARD.md, and LIMITATIONS.md.
"""

import sys
from pathlib import Path
from typing import Dict, Any

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.core.config import settings


def generate_constants_markdown() -> str:
    lines = []
    lines.append("### System Configuration Constants (Source of Truth)")
    lines.append("")
    lines.append("#### 1. Spatial Gating & Duplicate Matching Radii")
    lines.append("| Category Code | Base Radius ($R_{\\text{base}}$) | GPS Uncertainty Margin | Effective Matching Radius ($R_{\\text{eff}}$) | Spatial Rationale |")
    lines.append("| :--- | :--- | :--- | :--- | :--- |")

    rationales = {
        "pothole": "Localized asphalt crater/depression",
        "road_damage": "Longitudinal/alligator cracking across road slab",
        "garbage_overflow": "Discrete municipal waste bin location",
        "illegal_dumping": "Uncontained roadside debris or construction dump",
        "water_leakage": "Underground pipe burst / surface runoff segment",
        "blocked_drain": "Stormwater drain silting / culvert blockage",
        "broken_streetlight": "Consecutive dark street pole fixtures",
        "damaged_infrastructure": "Footpath slab displacement / pedestrian railing defect"
    }

    gps_margin = settings.GPS_ACCURACY_MARGIN_METERS
    for cat, base_r in settings.DUPLICATE_CATEGORY_RADII.items():
        eff_r = base_r + gps_margin
        desc = rationales.get(cat, "Municipal asset defect")
        lines.append(f"| `{cat}` | {base_r:.1f} m | +{gps_margin:.1f} m | **{eff_r:.1f} m** | {desc} |")
    lines.append(f"| `default / fallback` | {settings.DUPLICATE_RADIUS_METERS:.1f} m | +{gps_margin:.1f} m | **{settings.DUPLICATE_RADIUS_METERS + gps_margin:.1f} m** | Uncategorized issue fallback |")
    lines.append("")
    lines.append(f"> **Database Candidate Retrieval**: SQL pre-filtering uses a geographic bounding box ($\Delta \\text{{lat}}=\pm 0.0025^\\circ, \Delta \\text{{lon}}=\pm 0.0025^\\circ$, ~275 m) to retrieve nearby active reports without pruning wide-radius categories (e.g. water leaks or streetlights). Fine-grained category spatial gating is then applied in memory using $R_{{\\text{{eff}}}}$.")
    lines.append("")

    lines.append("#### 2. Duplicate Composite Scoring Parameters")
    lines.append("| Parameter | Value | Description |")
    lines.append("| :--- | :--- | :--- |")
    lines.append(f"| `DUPLICATE_SCORE_THRESHOLD` | **{settings.DUPLICATE_SCORE_THRESHOLD:.2f}** ({int(settings.DUPLICATE_SCORE_THRESHOLD * 100)}%) | Minimum composite score to flag duplicate candidate |")
    lines.append(f"| `DUPLICATE_TIME_WINDOW_DAYS` | **{settings.DUPLICATE_TIME_WINDOW_DAYS} days** | Maximum temporal lookback window for duplicate matching |")
    lines.append("| `WEIGHT_DISTANCE` | 0.40 (40%) | Haversine distance score weight |")
    lines.append("| `WEIGHT_CATEGORY` | 0.25 (25%) | Exact category match weight |")
    lines.append("| `WEIGHT_TEMPORAL` | 0.15 (15%) | Exponential decay time proximity weight |")
    lines.append("| `WEIGHT_VISUAL` | 0.20 (20%) | CLIP embedding cosine similarity / pHash weight |")
    lines.append("")

    lines.append("#### 3. Priority Engine Weighting Formula")
    lines.append("| Component | Weight | Mathematical Formulation |")
    lines.append("| :--- | :--- | :--- |")
    lines.append(f"| Severity Score ($S$) | **{settings.WEIGHT_SEVERITY:.2f}** (35%) | Base category severity + defect bounding box area/confidence |")
    lines.append(f"| Public Safety Risk ($P$) | **{settings.WEIGHT_SAFETY:.2f}** (25%) | Traffic hazard modifier + night-time visibility factor |")
    lines.append(f"| Location Sensitivity ($L$) | **{settings.WEIGHT_LOCATION_RISK:.2f}** (15%) | Distance to schools, hospitals, transit hubs via OSM POI |")
    lines.append(f"| Community Impact ($C$) | **{settings.WEIGHT_COMMUNITY_IMPACT:.2f}** (15%) | Citizen upvotes and duplicate cluster confirmation count |")
    lines.append(f"| Issue Age ($A$) | **{settings.WEIGHT_AGE:.2f}** (10%) | Continuous saturating age growth: $A(t) = 1 - e^{{-t/\\tau}}$ |")
    lines.append(f"| **Composite Score** | **1.00** (100%) | $P_{{\\text{{composite}}}} = 0.35S + 0.25P + 0.15L + 0.15C + 0.10A$ |")
    lines.append("")

    lines.append("#### 4. Geospatial Hotspot Clustering (DBSCAN / HDBSCAN)")
    lines.append("| Parameter | Value | Purpose |")
    lines.append("| :--- | :--- | :--- |")
    lines.append(f"| `DBSCAN_EPS_METERS` | **{settings.DBSCAN_EPS_METERS:.1f} m** | Maximum neighborhood reachability radius |")
    lines.append(f"| `DBSCAN_MIN_SAMPLES` | **{settings.DBSCAN_MIN_SAMPLES}** | Minimum core points to form a persistent cluster |")
    lines.append(f"| `HDBSCAN_MIN_CLUSTER_SIZE` | **{settings.HDBSCAN_MIN_CLUSTER_SIZE}** | Minimum density cluster membership size |")
    lines.append(f"| `HDBSCAN_MIN_SAMPLES` | **{settings.HDBSCAN_MIN_SAMPLES}** | Density estimation conservative factor |")
    lines.append(f"| `HOTSPOT_TIME_DECAY_HALF_LIFE_DAYS` | **{settings.HOTSPOT_TIME_DECAY_HALF_LIFE_DAYS:.1f} days** | Temporal half-life decay for active civic hotspots |")
    lines.append("")

    return "\n".join(lines)


if __name__ == "__main__":
    md = generate_constants_markdown()
    print(md)
