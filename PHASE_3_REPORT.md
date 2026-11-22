# Phase 3 Completion Report: Duplicates & Geospatial Intelligence

**Release Tag**: `v0.3`  
**Branch**: `phase-3-geospatial-duplicates` -> merged into `main`  
**Execution Date**: November 22, 2026  
**Test Suite Status**: 46 Passed, 1 Skipped (PostGIS Docker only), 0 Failed  

---

## 1. Summary of Completed Work

Phase 3 transformed CivicPulse AI's spatial and duplicate capabilities from naive flat distance checks into an integrated geospatial intelligence suite covering vector image embeddings, OpenStreetMap road recurrence analysis, hierarchical HDBSCAN clustering, and municipal field crew route optimization.

### Key Deliverables:
1. **Duplicate Detection v2 (`backend/app/services/duplicate_service.py`)**:
   - **OpenCLIP Semantic Embeddings**: Extracts 512-dimensional $L_2$-normalized feature vectors using OpenCLIP `ViT-B-32` (`laion2b_s34b_b79k`) via `EmbeddingService`.
   - **Multi-Modal Visual Ranking**: Computes cosine similarity between image embeddings ($S_{\text{clip}} = u \cdot v$). Falls back to 64-bit perceptual hash (bitwise Hamming distance) if embeddings are absent.
   - **Spatial Gating with GPS Accuracy Margin**: Filters candidates using category-specific radii ($25\text{m}$ for potholes up to $80\text{m}$ for streetlights) plus a $10.0\text{m}$ urban GPS uncertainty buffer (`GPS_ACCURACY_MARGIN_METERS`).
   - **Smooth Temporal Decay**: Applies continuous exponential decay ($S_{\text{time}} = e^{-\Delta t / 48\text{h}}$) rather than arbitrary step tiers.
   - **Weight Renormalization**: If visual data is absent, weights automatically renormalize across distance ($0.50$), category ($0.3125$), and time ($0.1875$).
   - **Admin Feedback Loop**: Confirming or rejecting duplicate suggestions logs `resolution_feedback` with user ID, timestamp, decision notes, and candidate features at resolution to generate labeled pair training data for future fine-tuning.
2. **Database & Vector Schema (`backend/alembic/versions/004_add_embeddings_and_geospatial_v2.py`)**:
   - Added `report_embeddings` table storing 512-dimensional vectors (compatible with SQLite JSON storage and PostgreSQL `pgvector`).
   - Added `road_segments` table for OpenStreetMap network representation.
   - Added `road_segment_id` foreign key on `reports`.
   - Added `clip_similarity`, `phash_similarity`, and `resolution_feedback` columns on `duplicate_candidates`.
3. **OpenStreetMap Recurrence Detection (`backend/app/services/recurrence_service.py`)**:
   - Curated `data/osm/bengaluru_roads.json` covering 12 major Bengaluru arterial and collector corridors (Outer Ring Road, 80ft Road Koramangala, 100ft Road Indiranagar, Sampige Road Malleshwaram, Hosur Road, etc.) with OpenStreetMap ODbL attribution.
   - Point-to-segment perpendicular distance snapping automatically associates submitted citizen reports with specific OSM road segments.
   - Detects chronic defect corridors where $\ge 3$ incidents of the same category occur on a road segment within 90 days.
   - Generates actionable civil engineering root-cause advisory recommendations (e.g. sub-base water seepage, drainage silting, or heavy axle load diversion rather than repeated surface patching).
4. **Hotspots v2: Hierarchical HDBSCAN & Temporal Decay (`backend/app/services/geospatial_service.py`)**:
   - Implemented `sklearn.cluster.HDBSCAN(metric="haversine")` with input coordinates in spherical radians.
   - Adapts to variable urban density across dense commercial sectors (Indiranagar/Koramangala) and dispersed outer wards without requiring a single rigid $\epsilon$ radius.
   - Integrates continuous temporal decay weighting ($w_i = e^{-\lambda \Delta t_i}$ with configurable half-life $\tau_{1/2} = 14$ days) so recently escalating clusters rank higher than dormant historical clusters.
   - Reports cluster stability scores (`probabilities_`), radius, urgency, and dominant defect categories.
5. **Municipal Crew Dispatch Route Optimization (`backend/app/services/routing_service.py`)**:
   - Integrates Google OR-Tools (`ortools.constraint_solver`) Traveling Salesperson Problem (TSP) solver (`PATH_CHEAPEST_ARC`).
   - Given open tickets in a ward, computes the minimum-distance transit sequence starting from a municipal operations hub, estimating transit time, service dwell time, and cumulative kilometers.
6. **API Endpoints**:
   - `GET /api/map/hotspots`: Supports `algorithm=hdbscan` or `dbscan`, category filtering, and temporal decay parameters.
   - `GET /api/map/recurring-failures`: Returns chronic failure corridors with engineering advisories.
   - `GET /api/map/dispatch-route`: Calculates optimized work-crew dispatch routes via Google OR-Tools.
   - `POST /api/admin/duplicates/{id}/resolve`: Records resolution decisions with feedback audit payloads.

---

## 2. Empirical Benchmark & Measured Experimental Results

Evaluated via `ml/eval/evaluate_duplicates.py` on $N=80$ balanced image pairs (40 positive augmentation duplicates, 40 negative non-duplicates) derived from Bengaluru fixture images.

> [!NOTE]
> **Methodology & Disclaimer**:
> This benchmark represents an *optimistic synthetic evaluation* using randomized image transformations (random crops 5%–12%, exposure shifts $\pm 15\%$, handheld rotations $\pm 4^\circ$) to simulate citizen photos of the same physical defect.
> Metrics report exact statistical measurements with 95% bootstrap confidence intervals (1,000 iterations).

| Method | Similarity Metric | Threshold ($\tau$) | Precision (95% CI) | Recall (95% CI) | Macro F1 (95% CI) | Mean Comparison Latency |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **Method A: Bitwise pHash** | 64-bit dHash Hamming Distance | $\tau \ge 0.75$ | 70.0% [47.4%, 88.9%] | 35.0% [20.0%, 51.1%] | 0.467 [0.292, 0.605] | **26.76 ms** |
| **Method B: OpenCLIP ViT-B/32** | 512-dim Cosine Similarity | $\tau \ge 0.82$ | **81.6%** [70.8%, 92.2%] | **100.0%** [100.0%, 100.0%] | **0.899** [0.829, 0.959] | **414.90 ms** |

### Benchmark Analysis:
- **Perceptual Hashing (pHash)**: While extremely lightweight ($26.76\text{ ms}$), perceptual hashing suffers from high sensitivity to handheld camera rotation and crop shifts, resulting in poor recall ($35.0\%$) and missing 65% of true positive duplicate pairs.
- **OpenCLIP Embeddings**: Semantic vector representations are significantly more robust to geometric perspective shifts, achieving $100.0\%$ recall and $0.899$ F1 on synthetic augmentation pairs.
- **Architectural Solution**: CivicPulse AI uses a tiered approach: candidate spatial gating and pHash pre-filtering for rapid screening, followed by OpenCLIP cosine similarity ranking for high-confidence duplicate matching.

---

## 3. Test Suite & Verification Output

```
============================= test session starts =============================
platform win32 -- Python 3.11.9, pytest-9.2.0, pluggy-1.7.0
rootdir: C:\Users\varsh\Downloads\CivicPulse AI
configfile: pytest.ini
collected 47 items

backend/tests/test_admin_workflows.py::test_admin_list_reports PASSED    [  2%]
backend/tests/test_admin_workflows.py::test_admin_status_transitions PASSED [  4%]
backend/tests/test_admin_workflows.py::test_admin_ai_override PASSED     [  6%]
backend/tests/test_admin_workflows.py::test_geospatial_hotspots_and_markers PASSED [  8%]
backend/tests/test_admin_workflows.py::test_analytics_and_export PASSED  [ 10%]
backend/tests/test_ai_pipeline.py::test_vision_classifier_text_heuristics PASSED [ 12%]
backend/tests/test_ai_pipeline.py::test_severity_estimator_critical_keywords PASSED [ 14%]
backend/tests/test_ai_pipeline.py::test_priority_service_scoring PASSED  [ 17%]
backend/tests/test_ai_pipeline.py::test_duplicate_service_haversine PASSED [ 19%]
backend/tests/test_ai_pipeline.py::test_duplicate_service_bitwise_hamming PASSED [ 21%]
backend/tests/test_ai_pipeline.py::test_model_evaluation_pipeline PASSED [ 23%]
backend/tests/test_auth.py::test_login_success PASSED                    [ 25%]
backend/tests/test_auth.py::test_login_invalid_credentials PASSED        [ 27%]
backend/tests/test_auth.py::test_citizen_registration PASSED             [ 29%]
backend/tests/test_auth.py::test_auth_me PASSED                          [ 31%]
backend/tests/test_duplicates_v2.py::test_clip_cosine_similarity_exact PASSED [ 34%]
backend/tests/test_duplicates_v2.py::test_spatial_gate_with_gps_margin PASSED [ 36%]
backend/tests/test_duplicates_v2.py::test_weight_renormalization_missing_visual_v2 PASSED [ 38%]
backend/tests/test_duplicates_v2.py::test_duplicate_resolution_logs_feedback PASSED [ 40%]
backend/tests/test_geospatial_v2.py::test_hdbscan_hotspots_detection PASSED [ 42%]
backend/tests/test_geospatial_v2.py::test_osm_road_network_seeding_and_snapping PASSED [ 44%]
backend/tests/test_geospatial_v2.py::test_recurring_failure_detection_and_advisory PASSED [ 46%]
backend/tests/test_geospatial_v2.py::test_google_ortools_dispatch_route_optimization PASSED [ 48%]
backend/tests/test_geospatial_v2.py::test_map_api_v2_endpoints PASSED    [ 51%]
backend/tests/test_ml_pipeline.py::test_base_analyzer_contract PASSED    [ 53%]
backend/tests/test_ml_pipeline.py::test_road_defect_detector_honest_abstention_without_weights PASSED [ 55%]
backend/tests/test_ml_pipeline.py::test_zeroshot_analyzer_abstention_on_missing_image PASSED [ 57%]
backend/tests/test_ml_pipeline.py::test_authoritative_citizen_selection_policy PASSED [ 59%]
backend/tests/test_ml_pipeline.py::test_severity_estimation_with_detection_box_metrics PASSED [ 61%]
backend/tests/test_ml_pipeline.py::test_ai_prediction_persistence_and_admin_feedback_loop PASSED [ 63%]
backend/tests/test_ml_pipeline.py::test_ml_evaluation_scripts_execute_cleanly PASSED [ 65%]
backend/tests/test_phase1_fixes.py::test_negative_rbac_citizen_forbidden PASSED [ 68%]
backend/tests/test_phase1_fixes.py::test_negative_rbac_unauthenticated_rejected PASSED [ 70%]
backend/tests/test_phase1_fixes.py::test_cors_headers_strict_origin PASSED [ 72%]
backend/tests/test_phase1_fixes.py::test_exif_gps_stripping_on_upload PASSED [ 74%]
backend/tests/test_phase1_fixes.py::test_exif_orientation_preserved_and_phash_aligned PASSED [ 76%]
backend/tests/test_phase1_fixes.py::test_bitwise_hamming_distance_exact PASSED [ 78%]
backend/tests/test_phase1_fixes.py::test_duplicate_weight_renormalization_missing_photo PASSED [ 80%]
backend/tests/test_phase1_fixes.py::test_category_specific_duplicate_radii PASSED [ 82%]
backend/tests/test_phase1_fixes.py::test_priority_orthogonality_no_double_counting PASSED [ 85%]
backend/tests/test_phase1_fixes.py::test_dynamic_data_driven_category_classification PASSED [ 87%]
backend/tests/test_phase1_fixes.py::test_data_provenance_is_synthetic PASSED [ 89%]
backend/tests/test_phase1_fixes.py::test_alembic_migrations_execute_cleanly PASSED [ 91%]
backend/tests/test_postgis_integration.py::test_postgis_migration_and_spatial_queries SKIPPED [ 93%]
backend/tests/test_reports.py::test_get_categories PASSED                [ 95%]
backend/tests/test_reports.py::test_submit_report_and_ai_processing PASSED [ 97%]
backend/tests/test_reports.py::test_get_my_reports PASSED                [100%]

================== 46 passed, 1 skipped in 101.16s (0:01:41) ==================
```

Frontend build:
```
✓ built in 1.57s
```

---

## 4. Deferred Items (Needs User Action)
1. **Real Field Duplicate Pair Collection**:
   - Collect and label actual field duplicate reports from Bengaluru citizens to supplement the synthetic augmentation benchmark with real-world pair evaluations.
2. **Full Bengaluru OSM Graph Expansion**:
   - For complete municipal coverage, download and cache the full OSM city graph (`bengaluru_complete.graphml`) via OSMnx for all 198 BBMP wards.
