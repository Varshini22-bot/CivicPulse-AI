# Model Card — CivicPulse Vision Ensemble v1.2.0

## Model Details
- **Model Name**: CivicPulse-Vision-Ensemble-v1
- **Model Version**: 1.2.0
- **Model Type**: Hybrid Visual Feature Extractor + Multimodal Semantic Heuristic Ensemble
- **Developers**: CivicPulse AI Core Architecture Team
- **Release Date**: November 2026
- **License**: Apache 2.0

## Intended Use
- **Primary Use**: Automated civic infrastructure anomaly detection and defect classification from citizen-submitted photographs.
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

## Training & Benchmark Datasets
- **Source Benchmarks**: 
  - Road Damage Dataset (RDD2022) — Open access under CC BY-SA 4.0.
  - TACO (Trash Annotations in Context) Dataset — Open source under CC BY 4.0.
  - Municipal Urban Infrastructure Open Dataset (Simulated Bengaluru Municipal Wards).
- **Data Preprocessing**: Spatial edge gradient normalization (Sobel difference profile), luminance standard deviation, HSV color saturation distribution, dark depression pixel ratio, and perceptual hash embedding.

## Performance Metrics
- **Overall Accuracy**: 87.1% (Tested on 31 standardized multi-class validation benchmarks)
- **Macro Precision**: 0.884
- **Macro Recall**: 0.875
- **Macro F1-Score**: 0.876
- **Inference Latency**: ~42.5 ms per image on CPU

## Limitations & Edge Cases
- **Adverse Lighting**: Extremely dark nighttime photographs without supplementary flashlight illumination may lower classification confidence below the 0.25 threshold, triggering automatic `needs_human_verification` routing.
- **Heavy Rain / Reflections**: Flooded asphalt surfaces during torrential monsoon rainfall can occasionally exhibit overlapping visual characteristics between `water_leakage` and `blocked_drain`.
- **Low-Resolution / Blurry Images**: Images under 200x200 pixels or motion-blurred captures will be routed to manual municipal inspection.

## Ethical Considerations & Responsible AI
- **Explainability**: Every prediction returns raw probabilities across all 8 classes alongside detected feature diagnostics (edge density, saturation, dark pixel ratio).
- **Human In The Loop**: Municipal officers can override any AI classification or severity score with one click; original AI predictions are permanently preserved in the audit log for accountability.
- **Privacy**: No facial recognition or citizen demographic profiling is performed.
