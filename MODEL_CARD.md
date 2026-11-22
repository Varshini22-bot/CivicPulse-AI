# Model Card — CivicPulse Heuristic Baseline v1.0.0

## Model Details
- **Model Name**: CivicPulse-Heuristic-Baseline
- **Model Version**: 1.0.0
- **Model Type**: Classical Computer Vision Feature Extractor (Sobel, HSV, dark pixel depth) + Rule-Based Keyword Scoring
- **Developers**: CivicPulse AI Core Architecture Team
- **Release Date**: November 2026
- **License**: MIT

## Intended Use
- **Primary Use**: Baseline civic infrastructure defect triage from citizen-submitted photographs.
- **Intended Users**: Municipal public works engineers, dispatch coordinators, civic operations administrators.
- **Decision Support**: This model is explicitly designed as a *decision-support system* to triage, prioritize, and route municipal tickets. It provides explainable confidence scores and does not take irreversible autonomous municipal actions without human administrative confirmation.

## Supported Classes
1. **Pothole** (`pothole`): Deep road depressions, cavities, and asphalt surface ruptures.
2. **Road Damage** (`road_damage`): Alligator cracking, linear surface fissures, tarmac degradation.
3. **Garbage Overflow** (`garbage_overflow`): Municipal waste containment bins overflowing with solid refuse.
4. **Illegal Dumping** (`illegal_dumping`): Bulk commercial/industrial debris, uncontained roadside demolition rubble.
5. **Water Leakage** (`water_leakage`): Municipal water supply pipe ruptures, continuous localized pooling.
6. **Blocked Drain** (`blocked_drain`): Obstructed stormwater drains, silted culverts, stagnant urban runoff.
7. **Broken Streetlight** (`broken_streetlight`): Damaged luminaires, unlit municipal fixtures, exposed electrical cables.
8. **Damaged Public Infrastructure** (`damaged_infrastructure`): Broken pedestrian pavements, shattered bus stops, damaged crash barriers.

## Datasets & Feature Processing
- **Current Pipeline**: Spatial edge gradient normalization (Sobel difference profile), luminance standard deviation, HSV color saturation distribution, dark depression pixel ratio, and perceptual hash embedding.
- **Planned Phase 2 Training Benchmarks**:
  - Road Damage Dataset (RDD2022) for road defect classes.
  - TACO (Trash Annotations in Context) Dataset for litter/dumping.
  - Zero-shot CLIP fallback with abstain state for infrastructure classes lacking open datasets.

## Performance Metrics
- **Overall Accuracy**: Not yet evaluated on a labelled dataset.
- **Macro Precision**: Not yet evaluated on a labelled dataset.
- **Macro Recall**: Not yet evaluated on a labelled dataset.
- **Macro F1-Score**: Not yet evaluated on a labelled dataset.
- **Inference Latency**: Real-time measured wall-clock execution time (~5–20 ms per image on CPU).
- **Note**: The baseline heuristic engine has not been evaluated on a held-out labeled dataset. Genuine precision, recall, and confusion matrices will be established during Phase 2 training.

## Limitations & Edge Cases
- **Adverse Lighting**: Extremely dark nighttime photographs without supplementary flashlight illumination may lower classification confidence below the 0.25 threshold, triggering automatic `needs_human_verification` routing.
- **Heavy Rain / Reflections**: Flooded asphalt surfaces during torrential monsoon rainfall can occasionally exhibit overlapping visual characteristics between `water_leakage` and `blocked_drain`.
- **Low-Resolution / Blurry Images**: Images under 200x200 pixels or motion-blurred captures will be routed to manual municipal inspection.

## Ethical Considerations & Responsible AI
- **Explainability**: Every prediction returns raw probabilities across all 8 classes alongside detected feature diagnostics (edge density, saturation, dark pixel ratio).
- **Human In The Loop**: Municipal officers can override any AI classification or severity score with one click; original AI predictions are permanently preserved in the audit log for accountability.
- **Privacy**: No facial recognition or citizen demographic profiling is performed.
