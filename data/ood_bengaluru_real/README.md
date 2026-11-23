# Bengaluru Real-Photo Out-Of-Distribution (OOD) Dataset

This directory holds authentic smartphone photos of civic infrastructure defects collected across Bengaluru neighborhoods (e.g., Koramangala, Indiranagar, HSR Layout, Whitefield).

## Directory Structure
```
data/ood_bengaluru_real/
├── .gitkeep
├── README.md
├── labels.csv           # Ground truth single-image annotations
├── pairs.csv            # Same-defect & different-defect image pairs
└── images/              # Authentic user-captured photo files (.jpg/.png)
    ├── pothole_01.jpg
    ├── pothole_02.jpg
    └── ...
```

## Privacy & Safety
- **NO FACES**: Do not upload images with recognizable pedestrian or citizen faces.
- **NO VEHICLE PLATES**: Do not include readable vehicle registration/number plates.
- **PHYSICAL SAFETY**: Take photos only from pedestrian walkways; never enter active motor vehicular traffic.

## File Templates
See `labels.csv` and `pairs.csv` for column headers and annotation examples.
Once you add photos to `images/`, validate the folder using:
```bash
python scripts/validate_photo_folder.py --data-dir data/ood_bengaluru_real
```
