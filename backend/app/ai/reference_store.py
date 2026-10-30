import os
import datetime
from typing import Optional
import cv2
import numpy as np
from app.config import settings


class ReferenceStore:
    """
    Stores one "empty bin" reference frame per dustbin on disk.
    The fill estimator compares live frames against it, which is far more accurate
    than object detection alone for crumpled paper, bags and mixed waste.
    """

    @staticmethod
    def path_for(bin_id_pk: int) -> str:
        return os.path.join(settings.REFERENCES_DIR, f"bin_{bin_id_pk}_empty.png")

    @classmethod
    def save(cls, bin_id_pk: int, frame: np.ndarray) -> None:
        os.makedirs(settings.REFERENCES_DIR, exist_ok=True)
        cv2.imwrite(cls.path_for(bin_id_pk), frame)

    @classmethod
    def load(cls, bin_id_pk: int) -> Optional[np.ndarray]:
        path = cls.path_for(bin_id_pk)
        if not os.path.exists(path):
            return None
        img = cv2.imread(path)
        return img if img is not None and img.size else None

    @classmethod
    def delete(cls, bin_id_pk: int) -> bool:
        path = cls.path_for(bin_id_pk)
        if os.path.exists(path):
            os.remove(path)
            return True
        return False

    @classmethod
    def mtime(cls, bin_id_pk: int) -> Optional[float]:
        path = cls.path_for(bin_id_pk)
        return os.path.getmtime(path) if os.path.exists(path) else None

    @classmethod
    def info(cls, bin_id_pk: int) -> dict:
        ts = cls.mtime(bin_id_pk)
        return {
            "has_reference": ts is not None,
            "captured_at": datetime.datetime.fromtimestamp(ts).isoformat() if ts else None
        }
