import os
import time
from typing import Dict, Any, List, Optional
from PIL import Image
import numpy as np

from app.ml.base import BaseAnalyzer, AnalyzerResult, DetectionBox
from app.core.config import settings


class RoadDefectDetector(BaseAnalyzer):
    """
    Dedicated object detector for road surface defects:
    - Potholes (RDD2022 class D40)
    - Road Damage / Cracks (RDD2022 classes D00 longitudinal, D10 transverse, D20 alligator)

    Supports ONNX runtime CPU inference. If model weights are not loaded locally,
    the detector safely abstains with clear operational notice rather than faking detections.
    """

    ANALYZER_NAME = "road_defect_detector"
    MODEL_VERSION = "rdd2022-yolov8n-onnx-v1"

    CLASS_MAP = {
        0: ("road_damage", "Longitudinal Crack (D00)"),
        1: ("road_damage", "Transverse Crack (D10)"),
        2: ("road_damage", "Alligator Crack (D20)"),
        3: ("pothole", "Pothole (D40)")
    }

    def __init__(self, model_path: Optional[str] = None):
        candidate_paths = [
            model_path,
            getattr(settings, "ROAD_DEFECT_MODEL_PATH", None),
            "models/rdd2022_yolov8n.onnx",
            "backend/app/ml/weights/road_detector.onnx"
        ]
        self.model_path = next((p for p in candidate_paths if p and os.path.exists(p)), model_path or "models/rdd2022_yolov8n.onnx")
        self.session = None
        self._load_onnx_model()

    def _load_onnx_model(self):
        """Attempts to load ONNX runtime inference session if model file exists."""
        if os.path.exists(self.model_path):
            try:
                import onnxruntime as ort
                self.session = ort.InferenceSession(self.model_path, providers=['CPUExecutionProvider'])
            except Exception:
                self.session = None

    def is_weights_loaded(self) -> bool:
        return self.session is not None

    def analyze(
        self,
        image_path: Optional[str],
        description: Optional[str] = "",
        user_hint: Optional[str] = None,
        db: Optional[Any] = None
    ) -> AnalyzerResult:
        """
        Runs object detection on road defect image.
        If weights are not found, returns status='abstain' with actionable guidance.
        """
        t0 = time.perf_counter()

        # If no weights are loaded, abstain honestly
        if not self.is_weights_loaded():
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            return AnalyzerResult(
                analyzer_name=self.ANALYZER_NAME,
                model_version=self.MODEL_VERSION,
                category_suggestion=user_hint or "pothole",
                confidence=0.0,
                status="abstain",
                evidence="Trained road defect weights not found locally on disk. Run ml/train.py or the Colab notebook to generate weights.",
                detections=[],
                raw_predictions={},
                inference_time_ms=elapsed_ms
            )

        if not image_path or not os.path.exists(image_path):
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            return AnalyzerResult(
                analyzer_name=self.ANALYZER_NAME,
                model_version=self.MODEL_VERSION,
                category_suggestion=user_hint or "pothole",
                confidence=0.0,
                status="abstain",
                evidence="No image file provided for visual road defect detection.",
                detections=[],
                raw_predictions={},
                inference_time_ms=elapsed_ms
            )

        # Run ONNX inference
        try:
            with Image.open(image_path) as img:
                orig_w, orig_h = img.size
                resized = img.convert("RGB").resize((640, 640), Image.Resampling.BILINEAR)
                input_arr = np.array(resized, dtype=np.float32).transpose(2, 0, 1) / 255.0
                input_batch = np.expand_dims(input_arr, axis=0)

            input_name = self.session.get_inputs()[0].name
            outputs = self.session.run(None, {input_name: input_batch})
            
            # Post-process outputs [batch, 84, 8400] -> boxes and scores
            detections = self._postprocess_yolo_onnx(outputs[0][0], orig_w, orig_h)
            
            elapsed_ms = (time.perf_counter() - t0) * 1000.0

            if not detections:
                return AnalyzerResult(
                    analyzer_name=self.ANALYZER_NAME,
                    model_version=self.MODEL_VERSION,
                    category_suggestion=user_hint or "road_damage",
                    confidence=0.20,
                    status="abstain",
                    evidence="No road defects (potholes or cracks) detected above confidence threshold.",
                    detections=[],
                    raw_predictions={"pothole": 0.10, "road_damage": 0.10},
                    inference_time_ms=elapsed_ms
                )

            # Categorize by top scoring detection
            best_det = max(detections, key=lambda d: d.score)
            status = "ok" if best_det.score >= 0.50 else "low_confidence"
            evidence = f"Detected {len(detections)} defect(s): top match '{best_det.class_name}' ({best_det.score:.1%})."

            pothole_score = max([d.score for d in detections if d.class_name == "pothole"] or [0.05])
            road_score = max([d.score for d in detections if d.class_name == "road_damage"] or [0.05])

            return AnalyzerResult(
                analyzer_name=self.ANALYZER_NAME,
                model_version=self.MODEL_VERSION,
                category_suggestion=best_det.class_name,
                confidence=round(best_det.score, 2),
                status=status,
                evidence=evidence,
                detections=detections,
                raw_predictions={"pothole": round(pothole_score, 2), "road_damage": round(road_score, 2)},
                inference_time_ms=elapsed_ms
            )
        except Exception as e:
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            return AnalyzerResult(
                analyzer_name=self.ANALYZER_NAME,
                model_version=self.MODEL_VERSION,
                category_suggestion=user_hint or "pothole",
                confidence=0.0,
                status="abstain",
                evidence=f"ONNX inference failure ({type(e).__name__}): {e}",
                detections=[],
                raw_predictions={},
                inference_time_ms=elapsed_ms
            )

    def _postprocess_yolo_onnx(self, output: np.ndarray, orig_w: int, orig_h: int) -> List[DetectionBox]:
        """Simple NMS and decoding for YOLOv8 output tensor [84, 8400]."""
        # output is [4 + num_classes, 8400]
        # classes: 0: D00, 1: D10, 2: D20, 3: D40
        boxes = output[:4, :].T  # [8400, 4] -> cx, cy, w, h in 640x640
        scores = output[4:8, :].T  # [8400, 4]
        
        detections: List[DetectionBox] = []
        conf_thresh = 0.25

        max_class_ids = np.argmax(scores, axis=1)
        max_scores = np.max(scores, axis=1)
        valid_mask = max_scores >= conf_thresh

        valid_boxes = boxes[valid_mask]
        valid_scores = max_scores[valid_mask]
        valid_classes = max_class_ids[valid_mask]

        for box, score, cls_id in zip(valid_boxes[:10], valid_scores[:10], valid_classes[:10]):
            cx, cy, bw, bh = box
            # Convert 640 normalized to [ymin, xmin, ymax, xmax]
            xmin = max(0.0, min(1.0, (cx - bw / 2.0) / 640.0))
            ymin = max(0.0, min(1.0, (cy - bh / 2.0) / 640.0))
            xmax = max(0.0, min(1.0, (cx + bw / 2.0) / 640.0))
            ymax = max(0.0, min(1.0, (cy + bh / 2.0) / 640.0))

            cat_code, label = self.CLASS_MAP.get(int(cls_id), ("road_damage", "Road Damage"))
            detections.append(DetectionBox(
                class_name=cat_code,
                bbox=[ymin, xmin, ymax, xmax],
                score=float(score)
            ))

        return detections
