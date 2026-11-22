from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field, asdict


@dataclass
class DetectionBox:
    """
    Standardized bounding box for localized defect detection.
    Coordinates are normalized in range [0.0, 1.0]: [ymin, xmin, ymax, xmax].
    """
    class_name: str
    bbox: List[float]  # [ymin, xmin, ymax, xmax]
    score: float

    @property
    def area(self) -> float:
        if len(self.bbox) == 4:
            ymin, xmin, ymax, xmax = self.bbox
            return max(0.0, ymax - ymin) * max(0.0, xmax - xmin)
        return 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "class_name": self.class_name,
            "bbox": [round(c, 4) for c in self.bbox],
            "score": round(self.score, 4),
            "area": round(self.area, 4)
        }


@dataclass
class AnalyzerResult:
    """
    Standardized result contract for all CivicPulse AI vision and classification analyzers.
    """
    analyzer_name: str
    model_version: str
    category_suggestion: str
    confidence: float
    status: str  # 'ok', 'low_confidence', 'abstain'
    evidence: str
    detections: List[DetectionBox] = field(default_factory=list)
    raw_predictions: Dict[str, float] = field(default_factory=dict)
    inference_time_ms: float = 0.0
    detected_features: Dict[str, Any] = field(default_factory=dict)

    @property
    def detection_count(self) -> int:
        return len(self.detections)

    @property
    def relative_box_area(self) -> float:
        """Sum of relative detection areas (0.0 to 1.0 capped)."""
        return min(1.0, sum(d.area for d in self.detections))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "analyzer_name": self.analyzer_name,
            "model_version": self.model_version,
            "category_suggestion": self.category_suggestion,
            "confidence": round(self.confidence, 4),
            "status": self.status,
            "evidence": self.evidence,
            "detections": [d.to_dict() for d in self.detections],
            "raw_predictions": self.raw_predictions,
            "inference_time_ms": round(self.inference_time_ms, 2),
            "detection_count": self.detection_count,
            "relative_box_area": round(self.relative_box_area, 4),
            "detected_features": self.detected_features
        }


class BaseAnalyzer(ABC):
    """
    Abstract interface for all CivicPulse computer vision analyzers.
    Implementations must be deterministic given identical inputs and provide explainable evidence.
    """

    @abstractmethod
    def analyze(
        self,
        image_path: Optional[str],
        description: Optional[str] = "",
        user_hint: Optional[str] = None,
        db: Optional[Any] = None
    ) -> AnalyzerResult:
        """
        Analyze an issue report. Returns standardized AnalyzerResult contract.
        Must never crash on missing, corrupt, or unsupported images.
        """
        pass
