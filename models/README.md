# Trained Model Weights Directory

This directory stores compiled machine learning model weights for the CivicPulse AI runtime.

## Files
- `rdd2022_yolov8n.onnx`: ONNX format YOLOv8n object detector trained on the RDD2022 dataset for localized road defect detection (potholes and road cracks).

## Instructions
1. Follow `ml/README_TRAINING.md` to train the model on Google Colab using `scripts/train_road_defect_detector.ipynb` or `ml/notebooks/CivicPulse_Model_Training_Colab.ipynb`.
2. Download the exported `rdd2022_yolov8n.onnx` file from Colab.
3. Place `rdd2022_yolov8n.onnx` directly into this directory (`models/rdd2022_yolov8n.onnx`).
4. Once placed, CivicPulse AI's backend automatically loads the ONNX runtime session and transitions from `status="abstain"` to active bounding box inference.
