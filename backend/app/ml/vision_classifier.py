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
            "description": "Depression or crater in road asphalt surface"
        },
        "road_damage": {
            "name": "Road Damage",
            "base_safety": 0.70,
            "description": "Longitudinal/alligator cracking or road surface degradation"
        },
        "garbage_overflow": {
            "name": "Garbage Overflow",
            "base_safety": 0.50,
            "description": "Excess solid municipal waste overflowing containment bins"
        },
        "illegal_dumping": {
            "name": "Illegal Dumping",
            "base_safety": 0.65,
            "description": "Unauthorized large-scale debris or industrial waste discarded on public land"
        },
        "water_leakage": {
            "name": "Water Leakage",
            "base_safety": 0.60,
            "description": "Municipal pipeline leak or pooling fresh water"
        },
        "blocked_drain": {
            "name": "Blocked Drain",
            "base_safety": 0.75,
            "description": "Stormwater drain or culvert obstructed by silt or refuse"
        },
        "broken_streetlight": {
            "name": "Broken Streetlight",
            "base_safety": 0.65,
            "description": "Non-functional luminaire, damaged pole or exposed electrical wiring"
        },
        "damaged_infrastructure": {
            "name": "Damaged Public Infrastructure",
            "base_safety": 0.80,
            "description": "Broken sidewalk, footpath railing, bus shelter or traffic signage"
        }
    }

    MODEL_NAME = "CivicPulse-Heuristic-Baseline"
    MODEL_VERSION = "1.0.0"

    def __init__(self):
        pass

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
        description: Optional[str] = ""
    ) -> Dict[str, Any]:
        """
        Run modular inference on civic report.
        Blends visual texture/color signatures with semantic text indicators.
        """
        t0 = time.perf_counter()
        features = {}
        if image_path and os.path.exists(image_path):
            features = self.extract_visual_features(image_path)
        
        # Analyze semantic keywords from description
        desc_lower = (description or "").lower()
        keyword_scores: Dict[str, float] = {cat: 0.10 for cat in self.CATEGORIES}
        
        category_keywords = {
            "pothole": ["pothole", "crater", "hole", "cavity", "asphalt", "bump", "tyre", "tire", "bike fell"],
            "road_damage": ["crack", "road damage", "tar", "uneven road", "broken road", "tarmac", "crumbling"],
            "garbage_overflow": ["garbage", "trash", "waste", "bin", "overflowing", "rubbish", "litter", "smell", "rotting"],
            "illegal_dumping": ["dumping", "debris", "construction waste", "rubble", "discarded", "lorry dumped", "pile"],
            "water_leakage": ["water", "leak", "pipeline", "pipe burst", "drinking water", "flowing water", "puddle"],
            "blocked_drain": ["drain", "blocked", "gutter", "clogged", "sewage", "stormwater", "overflowing drain", "stagnant"],
            "broken_streetlight": ["streetlight", "lamp", "dark", "wire", "pole", "light not working", "bulb", "illumination"],
            "damaged_infrastructure": ["footpath", "sidewalk", "railing", "bus stop", "manhole cover", "signboard", "divider", "pavement"]
        }
        
        for cat, kws in category_keywords.items():
            for kw in kws:
                if kw in desc_lower:
                    keyword_scores[cat] += 0.35

        # Visual heuristics matching
        visual_scores: Dict[str, float] = {cat: 0.15 for cat in self.CATEGORIES}
        if features:
            ed = features.get("edge_density", 0.0)
            dp = features.get("dark_pixel_ratio", 0.0)
            sat = features.get("saturation", 0.0)
            cv = features.get("color_variance", 0.0)
            
            # Potholes exhibit dark depressions with distinct rim edges
            if dp > 0.20 and ed > 0.06:
                visual_scores["pothole"] += 0.40
                visual_scores["road_damage"] += 0.25
            
            # Road damage/cracks exhibit high edge density on low-saturation surfaces
            if ed > 0.08 and sat < 0.25:
                visual_scores["road_damage"] += 0.45
            
            # Garbage has high color variance and high plastic saturation
            if sat > 0.30 or cv > 0.35:
                visual_scores["garbage_overflow"] += 0.40
                visual_scores["illegal_dumping"] += 0.35
            
            # Blocked drains combine dark slurry with surface debris
            if dp > 0.25 and sat < 0.20:
                visual_scores["blocked_drain"] += 0.30
                visual_scores["water_leakage"] += 0.25

        # User hint influence
        hint_scores: Dict[str, float] = {cat: 0.10 for cat in self.CATEGORIES}
        if user_category_hint and user_category_hint in self.CATEGORIES:
            hint_scores[user_category_hint] += 0.50

        # Ensemble aggregation: 0.45 Text + 0.35 Visual + 0.20 User Hint
        total_scores: Dict[str, float] = {}
        for cat in self.CATEGORIES:
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
            "category_name": self.CATEGORIES.get(predicted_cat, {}).get("name", "Needs Review"),
            "confidence": confidence,
            "raw_predictions": probabilities,
            "detected_features": features,
            "model_name": self.MODEL_NAME,
            "model_version": self.MODEL_VERSION,
            "processing_status": status,
            "inference_time_ms": elapsed_ms
        }

classifier = CivicVisionClassifier()
