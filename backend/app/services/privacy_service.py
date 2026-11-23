"""
Privacy & PII Redaction Service.

Bundled Model License:
The bundled face detection model (haarcascade_frontalface_default.xml) is licensed under
the 3-Clause BSD License by Intel Corporation and OpenCV Foundation.
See app/ml/cascades/LICENSE.txt for full copyright and license terms.

SCOPE & LIMITATIONS:
1. Face Redaction: Applies best-effort Gaussian blurring to detected frontal human faces
   using the bundled OpenCV Haar Cascade.
2. Vehicle License Plates: NOT IMPLEMENTED.
   Standard OpenCV cascades only provide Russian GOST plate models, which completely fail
   on Indian vehicle registration plates (two-line motorcycle plates, yellow commercial
   boards, HSRP plates, oblique angles). Plate redaction is therefore not claimed or
   attempted in this version.
"""

import os
from typing import Dict, Any, Optional

try:
    import cv2
    import numpy as np
    CV2_AVAILABLE = True
except Exception:
    CV2_AVAILABLE = False


class PrivacyService:
    """
    Best-Effort Human Face Anonymization Service.
    Applies Gaussian blurring to detected human faces in citizen photos prior to storage.
    License plate redaction is explicitly NOT implemented.
    """

    _face_cascade = None

    @classmethod
    def _get_face_cascade(cls):
        if not CV2_AVAILABLE:
            return None

        if cls._face_cascade is None:
            # 1. Bundled repo path (primary source)
            bundle_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "ml", "cascades"))
            face_xml = os.path.join(bundle_dir, "haarcascade_frontalface_default.xml")

            if not os.path.exists(face_xml):
                # Fallback to cv2 data directory if available
                try:
                    face_xml = os.path.join(cv2.data.haarcascades, "haarcascade_frontalface_default.xml")
                except Exception:
                    pass

            if os.path.exists(face_xml):
                try:
                    cls._face_cascade = cv2.CascadeClassifier(face_xml)
                except Exception:
                    cls._face_cascade = None

        return cls._face_cascade

    @classmethod
    def _get_cascades(cls):
        """Legacy helper for testing cascade availability."""
        return cls._get_face_cascade(), None

    @classmethod
    def anonymize_image(cls, image_path: str, save_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Detects and blurs human faces in the specified image file.
        Overwrites the file or saves to save_path.

        Note: License plate redaction is NOT implemented.
        """
        if not os.path.exists(image_path) or not CV2_AVAILABLE:
            return {
                "anonymized": False,
                "faces_detected": 0,
                "plates_detected": 0,
                "plate_redaction_implemented": False,
                "note": "OpenCV not available or image path does not exist."
            }

        face_cascade = cls._get_face_cascade()
        if face_cascade is None:
            return {
                "anonymized": False,
                "faces_detected": 0,
                "plates_detected": 0,
                "plate_redaction_implemented": False,
                "note": "Bundled Haar cascade model file could not be loaded."
            }

        try:
            img = cv2.imread(image_path)
            if img is None:
                return {
                    "anonymized": False,
                    "faces_detected": 0,
                    "plates_detected": 0,
                    "plate_redaction_implemented": False,
                    "note": "Failed to decode image file."
                }

            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            faces_count = 0

            # Detect frontal human faces
            faces = face_cascade.detectMultiScale(
                gray,
                scaleFactor=1.1,
                minNeighbors=3,
                minSize=(30, 30)
            )

            for (x, y, w, h) in faces:
                roi = img[y:y+h, x:x+w]
                # Strong Gaussian blur for irreversible anonymization
                kw = max(15, (w // 3) * 2 + 1)
                kh = max(15, (h // 3) * 2 + 1)
                blurred_roi = cv2.GaussianBlur(roi, (kw, kh), 30)
                img[y:y+h, x:x+w] = blurred_roi
                faces_count += 1

            target_path = save_path or image_path
            if faces_count > 0:
                cv2.imwrite(target_path, img)
                return {
                    "anonymized": True,
                    "faces_detected": faces_count,
                    "plates_detected": 0,
                    "plate_redaction_implemented": False,
                    "saved_path": target_path,
                    "note": f"Privacy blur applied: {faces_count} face(s) redacted. Plate redaction not implemented."
                }

            return {
                "anonymized": False,
                "faces_detected": 0,
                "plates_detected": 0,
                "plate_redaction_implemented": False,
                "saved_path": target_path,
                "note": "No human faces detected in photograph. Plate redaction not implemented."
            }

        except Exception as e:
            return {
                "anonymized": False,
                "faces_detected": 0,
                "plates_detected": 0,
                "plate_redaction_implemented": False,
                "note": f"Privacy processing exception: {str(e)}"
            }
