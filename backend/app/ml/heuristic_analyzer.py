import os
import time
import math
import hashlib
from typing import Dict, Any, Tuple, Optional, List
from PIL import Image, ImageStat, ImageFilter
import numpy as np

from app.ml.base import BaseAnalyzer, AnalyzerResult, DetectionBox


class HeuristicAnalyzer(BaseAnalyzer):
    """
    Classical rule-based computer vision baseline analyzer.
    Extracts structural edge profiles, color variance, cavity dark pixel ratios,
    and semantic keywords to generate transparent, explainable civic defect suggestions.
    """

    ANALYZER_NAME = "rule_based_heuristic"
    MODEL_VERSION = "1.0.0"

    DEFAULT_CATEGORIES = {
        "pothole": {
            "name": "Pothole",
            "base_safety": 0.85,
            "base_severity": 6,
            "description": "Depression or crater in road asphalt surface",
            "keywords": ["pothole", "crater", "hole", "cavity", "asphalt", "bump", "tyre", "tire", "bike fell"]
        },
        "road_damage": {
            "name": "Road Damage",
            "base_safety": 0.70,
            "base_severity": 5,
            "description": "Longitudinal/alligator cracking or road surface degradation",
            "keywords": ["crack", "road damage", "tar", "uneven road", "broken road", "tarmac", "crumbling"]
        },
        "garbage_overflow": {
            "name": "Garbage Overflow",
            "base_safety": 0.50,
            "base_severity": 4,
            "description": "Excess solid municipal waste overflowing containment bins",
            "keywords": ["garbage", "trash", "waste", "bin", "overflowing", "rubbish", "litter", "smell", "rotting"]
        },
        "illegal_dumping": {
            "name": "Illegal Dumping",
            "base_safety": 0.65,
            "base_severity": 6,
            "description": "Unauthorized large-scale debris or industrial waste discarded on public land",
            "keywords": ["dumping", "debris", "construction waste", "rubble", "discarded", "lorry dumped", "pile"]
        },
        "water_leakage": {
            "name": "Water Leakage",
            "base_safety": 0.60,
            "base_severity": 5,
            "description": "Municipal pipeline leak or pooling fresh water",
            "keywords": ["water", "leak", "pipeline", "pipe burst", "drinking water", "flowing water", "puddle"]
        },
        "blocked_drain": {
            "name": "Blocked Drain",
            "base_safety": 0.75,
            "base_severity": 6,
            "description": "Stormwater drain or culvert obstructed by silt or refuse",
            "keywords": ["drain", "blocked", "gutter", "clogged", "sewage", "stormwater", "overflowing drain", "stagnant"]
        },
        "broken_streetlight": {
            "name": "Broken Streetlight",
            "base_safety": 0.65,
            "base_severity": 4,
            "description": "Non-functional luminaire, damaged pole or exposed electrical wiring",
            "keywords": ["streetlight", "lamp", "dark", "wire", "pole", "light not working", "bulb", "illumination"]
        },
        "damaged_infrastructure": {
            "name": "Damaged Public Infrastructure",
            "base_safety": 0.80,
            "base_severity": 6,
            "description": "Broken sidewalk, footpath railing, bus shelter or traffic signage",
            "keywords": ["footpath", "sidewalk", "railing", "bus stop", "manhole cover", "signboard", "divider", "pavement"]
        }
    }

    def __init__(self):
        pass

    @classmethod
    def get_categories_config(cls, db: Optional[Any] = None) -> Dict[str, Dict[str, Any]]:
        if db is not None:
            try:
                from app.models import Category
                db_cats = db.query(Category).all()
                if db_cats:
                    configs = {}
                    for c in db_cats:
                        fallback = cls.DEFAULT_CATEGORIES.get(c.code, {})
                        kws = getattr(c, "keywords", None) or fallback.get("keywords", [c.name.lower()])
                        configs[c.code] = {
                            "name": c.name,
                            "base_safety": c.safety_weight if c.safety_weight is not None else fallback.get("base_safety", 0.5),
                            "base_severity": getattr(c, "base_severity", None) or fallback.get("base_severity", 5),
                            "description": c.description or fallback.get("description", ""),
                            "keywords": kws
                        }
                    return configs
            except Exception:
                pass
        return cls.DEFAULT_CATEGORIES

    def compute_perceptual_hash(self, image: Image.Image, hash_size: int = 8) -> str:
        """Computes 64-bit difference hash (dHash)."""
        resized = image.convert("L").resize((hash_size + 1, hash_size), Image.Resampling.LANCZOS)
        pixels = list(resized.getdata())
        diff = []
        for row in range(hash_size):
            for col in range(hash_size):
                p_left = pixels[row * (hash_size + 1) + col]
                p_right = pixels[row * (hash_size + 1) + col + 1]
                diff.append(p_left > p_right)
        decimal_val = 0
        hex_str = []
        for idx, val in enumerate(diff):
            if val:
                decimal_val += 2 ** (idx % 4)
            if idx % 4 == 3:
                hex_str.append(hex(decimal_val)[2:])
                decimal_val = 0
        return "".join(hex_str)

    def extract_visual_features(self, image_path: str) -> Dict[str, Any]:
        """Extract quantitative features from an image."""
        if not os.path.exists(image_path):
            return {
                "edge_density": 0.0,
                "contrast": 0.0,
                "brightness": 0.0,
                "saturation": 0.0,
                "dark_pixel_ratio": 0.0,
                "color_variance": 0.0,
                "aspect_ratio": 1.0,
                "perceptual_hash": None,
                "hotspot_box": None
            }

        with Image.open(image_path) as img:
            rgb_img = img.convert("RGB")
            w, h = rgb_img.size
            p_hash = self.compute_perceptual_hash(rgb_img)

            # Fast downscale for analysis
            work_img = rgb_img.resize((256, 256), Image.Resampling.BILINEAR)
            gray = work_img.convert("L")
            gray_arr = np.array(gray, dtype=np.float32)

            # Sobel edge gradient computation
            edges = gray.filter(ImageFilter.FIND_EDGES)
            edge_arr = np.array(edges, dtype=np.float32)
            edge_density = float(np.mean(edge_arr > 40.0))

            # Contrast & Brightness
            stat = ImageStat.Stat(work_img)
            brightness = float(stat.mean[0] + stat.mean[1] + stat.mean[2]) / (3.0 * 255.0)
            contrast = float(stat.stddev[0] + stat.stddev[1] + stat.stddev[2]) / (3.0 * 128.0)

            # Dark pixel depression ratio (cavities/potholes)
            dark_pixel_ratio = float(np.mean(gray_arr < 60.0))

            # HSV Saturation & Color Variance
            hsv = work_img.convert("HSV")
            hsv_arr = np.array(hsv, dtype=np.float32)
            sat = float(np.mean(hsv_arr[:, :, 1]) / 255.0)
            color_variance = float(np.std(hsv_arr[:, :, 0]) / 180.0)

            # Locate highest edge concentration bounding box if edge density is notable
            hotspot_box = None
            if edge_density > 0.05:
                # Find quadrant with maximum edge response
                h_mid, w_mid = 128, 128
                quads = [
                    (0.15, 0.15, 0.55, 0.55, np.mean(edge_arr[:h_mid, :w_mid])),
                    (0.15, 0.45, 0.55, 0.85, np.mean(edge_arr[:h_mid, w_mid:])),
                    (0.45, 0.15, 0.85, 0.55, np.mean(edge_arr[h_mid:, :w_mid])),
                    (0.45, 0.45, 0.85, 0.85, np.mean(edge_arr[h_mid:, w_mid:]))
                ]
                best_quad = max(quads, key=lambda q: q[4])
                hotspot_box = [best_quad[0], best_quad[1], best_quad[2], best_quad[3]]

            return {
                "edge_density": round(edge_density, 4),
                "contrast": round(contrast, 4),
                "brightness": round(brightness, 4),
                "saturation": round(sat, 4),
                "dark_pixel_ratio": round(dark_pixel_ratio, 4),
                "color_variance": round(color_variance, 4),
                "aspect_ratio": round(w / float(h), 2),
                "perceptual_hash": p_hash,
                "hotspot_box": hotspot_box
            }

    def analyze(
        self,
        image_path: Optional[str],
        description: Optional[str] = "",
        user_hint: Optional[str] = None,
        db: Optional[Any] = None
    ) -> AnalyzerResult:
        """
        Analyze report via rule-based heuristics. Returns standardized AnalyzerResult.
        """
        t0 = time.perf_counter()
        features = {}
        if image_path and os.path.exists(image_path):
            features = self.extract_visual_features(image_path)

        categories = self.get_categories_config(db)
        desc_lower = (description or "").lower()

        # 1. Semantic keyword scoring
        keyword_scores: Dict[str, float] = {cat: 0.10 for cat in categories}
        matched_keywords: List[str] = []
        for cat, cat_info in categories.items():
            kws = cat_info.get("keywords", [])
            for kw in kws:
                if kw.lower() in desc_lower:
                    keyword_scores[cat] += 0.35
                    matched_keywords.append(kw)

        # 2. Visual heuristics matching
        visual_scores: Dict[str, float] = {cat: 0.15 for cat in categories}
        visual_reasons = []
        if features:
            ed = features.get("edge_density", 0.0)
            dp = features.get("dark_pixel_ratio", 0.0)
            sat = features.get("saturation", 0.0)
            cv = features.get("color_variance", 0.0)

            if dp > 0.20 and ed > 0.06:
                if "pothole" in visual_scores: visual_scores["pothole"] += 0.40
                if "road_damage" in visual_scores: visual_scores["road_damage"] += 0.25
                visual_reasons.append("Surface depression and cavity rim edges detected")

            if ed > 0.08 and sat < 0.25:
                if "road_damage" in visual_scores: visual_scores["road_damage"] += 0.45
                visual_reasons.append("High edge density on low-saturation pavement")

            if sat > 0.30 or cv > 0.35:
                if "garbage_overflow" in visual_scores: visual_scores["garbage_overflow"] += 0.40
                if "illegal_dumping" in visual_scores: visual_scores["illegal_dumping"] += 0.35
                visual_reasons.append("Color variance and high saturation debris profile")

            if dp > 0.25 and sat < 0.20:
                if "blocked_drain" in visual_scores: visual_scores["blocked_drain"] += 0.30
                if "water_leakage" in visual_scores: visual_scores["water_leakage"] += 0.25
                visual_reasons.append("Dark slurry or liquid pooling profile")

        # 3. User hint weight
        hint_scores: Dict[str, float] = {cat: 0.10 for cat in categories}
        if user_hint and user_hint in categories:
            hint_scores[user_hint] += 0.50

        # Weighted blend: 0.45 Text + 0.35 Visual + 0.20 User Hint
        total_scores: Dict[str, float] = {}
        for cat in categories:
            total_scores[cat] = (0.45 * keyword_scores[cat]) + (0.30 * visual_scores[cat]) + (0.25 * hint_scores[cat])

        # Softmax normalization
        exp_scores = {k: math.exp(v * 5.0) for k, v in total_scores.items()}
        sum_exp = sum(exp_scores.values()) or 1.0
        probabilities = {k: round(v / sum_exp, 4) for k, v in exp_scores.items()}

        sorted_cats = sorted(probabilities.items(), key=lambda x: x[1], reverse=True)
        top_cat, top_prob = sorted_cats[0]

        # Status determination
        if top_prob < 0.25:
            status = "abstain"
            evidence = "Inconclusive rule-based indicators; analyzer abstains to require human verification."
        elif top_prob < 0.50:
            status = "low_confidence"
            evidence = f"Weak heuristic indicators for '{top_cat}' ({top_prob:.1%}); human review advised."
        else:
            status = "ok"
            ev_parts = []
            if matched_keywords:
                ev_parts.append(f"Keywords: {', '.join(matched_keywords[:3])}")
            if visual_reasons:
                ev_parts.append("; ".join(visual_reasons))
            evidence = f"Rule-based match: {'; '.join(ev_parts)}" if ev_parts else f"Strong heuristic prior for {top_cat}"

        # Synthesize detection box if hotspot is detected
        detections: List[DetectionBox] = []
        if features.get("hotspot_box") and top_cat in ["pothole", "road_damage", "garbage_overflow"]:
            detections.append(DetectionBox(
                class_name=top_cat,
                bbox=features["hotspot_box"],
                score=round(top_prob, 2)
            ))

        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        return AnalyzerResult(
            analyzer_name=self.ANALYZER_NAME,
            model_version=self.MODEL_VERSION,
            category_suggestion=top_cat,
            confidence=round(top_prob, 2),
            status=status,
            evidence=evidence,
            detections=detections,
            raw_predictions=probabilities,
            inference_time_ms=elapsed_ms,
            detected_features=features
        )
