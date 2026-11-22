import os
import math
from typing import List, Optional
import numpy as np
from sqlalchemy.orm import Session
from app.models import Report, ReportEmbedding
from app.ml.zeroshot_analyzer import ZeroShotAnalyzer

class EmbeddingService:
    """
    Manages 512-dimensional CLIP feature embeddings for civic report photographs.
    Provides vector persistence, batch synchronization, and cosine similarity comparison.
    """
    _analyzer: Optional[ZeroShotAnalyzer] = None

    @classmethod
    def get_analyzer(cls) -> ZeroShotAnalyzer:
        if cls._analyzer is None:
            cls._analyzer = ZeroShotAnalyzer()
        return cls._analyzer

    @classmethod
    def cosine_similarity(cls, vec_a: Optional[List[float]], vec_b: Optional[List[float]]) -> Optional[float]:
        """
        Computes cosine similarity between two 512-dim L2-normalized vectors.
        Returns None if either vector is missing (never substitutes a fake default).
        """
        if not vec_a or not vec_b or len(vec_a) != len(vec_b):
            return None
        u = np.array(vec_a, dtype=np.float32)
        v = np.array(vec_b, dtype=np.float32)
        norm_u = np.linalg.norm(u)
        norm_v = np.linalg.norm(v)
        if norm_u == 0.0 or norm_v == 0.0:
            return None
        sim = float(np.dot(u, v) / (norm_u * norm_v))
        return round(float(max(0.0, min(1.0, sim))), 4)

    @classmethod
    def get_or_compute_report_embedding(cls, db: Session, report: Report) -> Optional[List[float]]:
        """
        Retrieves cached embedding or computes and persists a new one for a report image.
        """
        if report.embedding_record and report.embedding_record.embedding:
            return report.embedding_record.embedding

        if not report.image_url:
            return None

        # Resolve local disk path
        local_path = report.image_url
        if not os.path.exists(local_path):
            filename = os.path.basename(report.image_url)
            possible_path = os.path.join("uploads", filename)
            if os.path.exists(possible_path):
                local_path = possible_path
            else:
                possible_path_backend = os.path.join("backend", "uploads", filename)
                if os.path.exists(possible_path_backend):
                    local_path = possible_path_backend

        if not os.path.exists(local_path):
            return None

        analyzer = cls.get_analyzer()
        emb = analyzer.extract_image_embedding(local_path)
        if emb:
            record = ReportEmbedding(
                report_id=report.id,
                embedding=emb,
                model_name="openclip-vit-b-32",
                dimension=len(emb)
            )
            db.add(record)
            try:
                db.commit()
            except Exception:
                db.rollback()
            return emb

        return None
