import os
from typing import Tuple, Dict, Any, Optional
from PIL import Image

try:
    import cv2
    import numpy as np
    CV2_AVAILABLE = True
except Exception:
    CV2_AVAILABLE = False


class PrivacyService:
    """
    Best-Effort Privacy Protection & PII Redaction Service.
    Applies best-effort Gaussian blurring to detected human faces and single-line vehicle license plates
    on citizen photo uploads prior to storage.
    
    LIMITATION NOTICE:
    Standard Haar cascades are trained on frontal human faces and single-line European/Russian plates.
    Indian-style vehicle plates (e.g. two-line motorcycle plates, yellow commercial boards) and oblique
    camera angles are NOT covered by these default weights and require domain-specific detectors.
    """

    _face_cascade = None
    _plate_cascade = None

    @classmethod
    def _get_cascades(cls):
        if not CV2_AVAILABLE:
            return None, None

        if cls._face_cascade is None:
            try:
                face_xml = os.path.join(cv2.data.haarcascades, "haarcascade_frontalface_default.xml")
                if os.path.exists(face_xml):
                    cls._face_cascade = cv2.CascadeClassifier(face_xml)
            except Exception:
                cls._face_cascade = None

        if cls._plate_cascade is None:
            try:
                plate_xml = os.path.join(cv2.data.haarcascades, "haarcascade_russian_plate_number.xml")
                if os.path.exists(plate_xml):
                    cls._plate_cascade = cv2.CascadeClassifier(plate_xml)
            except Exception:
                cls._plate_cascade = None

        return cls._face_cascade, cls._plate_cascade

    @classmethod
    def anonymize_image(cls, image_path: str, save_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Detects and blurs faces and license plates on the specified image file.
        Overwrites or saves to save_path.
        """
        if not os.path.exists(image_path) or not CV2_AVAILABLE:
            return {
                "anonymized": False,
                "faces_detected": 0,
                "plates_detected": 0,
                "note": "OpenCV not available or image path does not exist."
            }

        face_cascade, plate_cascade = cls._get_cascades()
        if face_cascade is None and plate_cascade is None:
            return {
                "anonymized": False,
                "faces_detected": 0,
                "plates_detected": 0,
                "note": "Haar cascade models not found in OpenCV data directory."
            }

        try:
            # Read image via OpenCV
            img = cv2.imread(image_path)
            if img is None:
                return {"anonymized": False, "faces_detected": 0, "plates_detected": 0, "note": "Failed to decode image."}

            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            faces_count = 0
            plates_count = 0

            # 1. Detect and blur faces
            if face_cascade is not None:
                faces = face_cascade.detectMultiScale(gray, scaleFactor=1.15, minNeighbors=4, minSize=(30, 30))
                for (x, y, w, h) in faces:
                    roi = img[y:y+h, x:x+w]
                    # Strong Gaussian blur for irreversible anonymization
                    ksize = (max(15, (w // 3) * 2 + 1), max(15, (h // 3) * 2 + 1))
                    blurred_roi = cv2.GaussianBlur(roi, ksize, 30)
                    img[y:y+h, x:x+w] = blurred_roi
                    faces_count += 1

            # 2. Detect and blur license plates
            if plate_cascade is not None:
                plates = plate_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=3, minSize=(40, 20))
                for (x, y, w, h) in plates:
                    roi = img[y:y+h, x:x+w]
                    ksize = (max(15, (w // 3) * 2 + 1), max(15, (h // 3) * 2 + 1))
                    blurred_roi = cv2.GaussianBlur(roi, ksize, 30)
                    img[y:y+h, x:x+w] = blurred_roi
                    plates_count += 1

            target_path = save_path or image_path
            if faces_count > 0 or plates_count > 0:
                cv2.imwrite(target_path, img)
                return {
                    "anonymized": True,
                    "faces_detected": faces_count,
                    "plates_detected": plates_count,
                    "saved_path": target_path,
                    "note": f"Privacy blur applied: {faces_count} faces and {plates_count} license plates redacted."
                }

            return {
                "anonymized": False,
                "faces_detected": 0,
                "plates_detected": 0,
                "saved_path": target_path,
                "note": "No human faces or license plates detected in photograph."
            }

        except Exception as e:
            return {
                "anonymized": False,
                "faces_detected": 0,
                "plates_detected": 0,
                "note": f"Privacy processing exception: {str(e)}"
            }
