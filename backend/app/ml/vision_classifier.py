import os
import time
import math
import hashlib
from typing import Dict, Any, Tuple, Optional
from PIL import Image, ImageStat, ImageFilter
import numpy as np

class CivicVisionClassifier:
    """
    Production-grade modular Computer Vision pipeline for civic infrastructure inspection.
    Extracts structural edge profiles, color distribution variance, spatial surface depression
    gradients, and texture irregularities to classify civic defects and calculate calibrated confidence.
    """
    
    CATEGORIES = {
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

    MODEL_NAME = "CivicPulse-Heuristic-Baseline"
    MODEL_VERSION = "1.0.0"

    def __init__(self):
        pass

    @classmethod
    def get_categories_config(cls, db: Optional[Any] = None) -> Dict[str, Dict[str, Any]]:
        """
        Dynamically load categories, keywords, and base severity from database.
        Falls back to default categories if DB is not provided or empty.
        """
        if db is not None:
            try:
                from app.models import Category
                db_cats = db.query(Category).all()
                if db_cats:
                    configs = {}
                    for c in db_cats:
                        fallback = cls.CATEGORIES.get(c.code, {})
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
        return cls.CATEGORIES

    def extract_visual_features(self, image_path: str) -> Dict[str, float]:
        """Extract quantitative computer vision features from an image."""
        if not os.path.exists(image_path):
            return {
                "edge_density": 0.0,
                "contrast": 0.0,
                "color_variance": 0.0,
                "dark_pixel_ratio": 0.0,
                "saturation": 0.0,
                "aspect_ratio": 1.0,
                "perceptual_hash": ""
            }

        with Image.open(image_path) as img:
            rgb_img = img.convert("RGB")
            w, h = rgb_img.size
            
            # Compute perceptual hash for visual similarity
            gray_small = rgb_img.convert("L").resize((16, 16), Image.Resampling.LANCZOS)
            pixels = np.array(gray_small).flatten()
            avg = pixels.mean()
            diff_bits = "".join(["1" if p > avg else "0" for p in pixels])
            p_hash = hex(int(diff_bits, 2))[2:].zfill(64)
            
            # Grayscale for edge and texture analysis
            gray = rgb_img.convert("L").resize((256, 256))
            gray_np = np.array(gray, dtype=np.float32)
            
            # Edge detection via Sobel-like spatial difference
            dx = np.abs(gray_np[:, 1:] - gray_np[:, :-1])
            dy = np.abs(gray_np[1:, :] - gray_np[:-1, :])
            edge_density = float(np.mean(dx) + np.mean(dy)) / 255.0
            
            # Contrast (Standard deviation of luminance)
            stat = ImageStat.Stat(rgb_img)
            contrast = float(np.mean(stat.stddev)) / 128.0
            
            # Color variance across RGB channels
            means = stat.mean
            color_variance = float(np.var(means[:3])) / 1000.0
            
            # Dark pixel ratio (common in craters, asphalt cavities, puddles)
            dark_pixels = np.sum(gray_np < 60) / float(gray_np.size)
            
            # HSV Saturation analysis (high in garbage / plastics, low in asphalt / concrete)
            hsv_img = rgb_img.convert("HSV")
            hsv_stat = ImageStat.Stat(hsv_img)
            saturation = float(hsv_stat.mean[1]) / 255.0
            
            return {
                "edge_density": round(edge_density, 4),
                "contrast": round(contrast, 4),
                "color_variance": round(color_variance, 4),
                "dark_pixel_ratio": round(dark_pixels, 4),
                "saturation": round(saturation, 4),
                "aspect_ratio": round(w / float(h), 2),
                "perceptual_hash": p_hash
            }

    def predict(
        self,
        image_path: Optional[str],
        user_category_hint: Optional[str] = None,
        description: Optional[str] = "",
        db: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        Run modular inference on civic report.
        Blends visual texture/color signatures with semantic text indicators.
        Categories and keyword profiles are dynamically resolved from DB if available.
        """
        t0 = time.perf_counter()
        features = {}
        if image_path and os.path.exists(image_path):
            features = self.extract_visual_features(image_path)
        
        categories = self.get_categories_config(db)

        # Analyze semantic keywords from description
        desc_lower = (description or "").lower()
        keyword_scores: Dict[str, float] = {cat: 0.10 for cat in categories}
        
        for cat, cat_info in categories.items():
            kws = cat_info.get("keywords", [])
            for kw in kws:
                if kw.lower() in desc_lower:
                    keyword_scores[cat] += 0.35

        # Visual heuristics matching
        visual_scores: Dict[str, float] = {cat: 0.15 for cat in categories}
        if features:
            ed = features.get("edge_density", 0.0)
            dp = features.get("dark_pixel_ratio", 0.0)
            sat = features.get("saturation", 0.0)
            cv = features.get("color_variance", 0.0)
            
            # Potholes exhibit dark depressions with distinct rim edges
            if dp > 0.20 and ed > 0.06:
                if "pothole" in visual_scores: visual_scores["pothole"] += 0.40
                if "road_damage" in visual_scores: visual_scores["road_damage"] += 0.25
            
            # Road damage/cracks exhibit high edge density on low-saturation surfaces
            if ed > 0.08 and sat < 0.25:
                if "road_damage" in visual_scores: visual_scores["road_damage"] += 0.45
            
            # Garbage has high color variance and high plastic saturation
            if sat > 0.30 or cv > 0.35:
                if "garbage_overflow" in visual_scores: visual_scores["garbage_overflow"] += 0.40
                if "illegal_dumping" in visual_scores: visual_scores["illegal_dumping"] += 0.35
            
            # Blocked drains combine dark slurry with surface debris
            if dp > 0.25 and sat < 0.20:
                if "blocked_drain" in visual_scores: visual_scores["blocked_drain"] += 0.30
                if "water_leakage" in visual_scores: visual_scores["water_leakage"] += 0.25

        # User hint influence
        hint_scores: Dict[str, float] = {cat: 0.10 for cat in categories}
        if user_category_hint and user_category_hint in categories:
            hint_scores[user_category_hint] += 0.50

        # Ensemble aggregation: 0.45 Text + 0.35 Visual + 0.20 User Hint
        total_scores: Dict[str, float] = {}
        for cat in categories:
            raw = (0.45 * keyword_scores[cat]) + (0.30 * visual_scores[cat]) + (0.25 * hint_scores[cat])
            total_scores[cat] = raw
            
        # Softmax normalization with scaling factor
        exp_scores = {k: math.exp(v * 5.0) for k, v in total_scores.items()}
        sum_exp = sum(exp_scores.values())
        probabilities = {k: round(v / sum_exp, 4) for k, v in exp_scores.items()}
        
        # Sort best category
        sorted_cats = sorted(probabilities.items(), key=lambda x: x[1], reverse=True)
        top_cat, top_prob = sorted_cats[0]
        
        # Guardrail: If confidence is very low (< 0.25), mark as "needs_review"
        if top_prob < 0.25:
            predicted_cat = "needs_review"
            confidence = round(top_prob, 2)
            status = "needs_human_verification"
        else:
            predicted_cat = top_cat
            confidence = round(top_prob, 2)
            status = "completed"

        elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 2)
        return {
            "predicted_category": predicted_cat,
            "category_name": categories.get(predicted_cat, {}).get("name", "Needs Review"),
            "confidence": confidence,
            "raw_predictions": probabilities,
            "detected_features": features,
            "model_name": self.MODEL_NAME,
            "model_version": self.MODEL_VERSION,
            "processing_status": status,
            "inference_time_ms": elapsed_ms
        }

classifier = CivicVisionClassifier()
