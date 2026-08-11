import os

from PIL import Image
import imagehash


class DuplicateDetectionService:
    """Service to detect duplicate images by comparing perceptual hashes (pHash)."""

    @staticmethod
    def calculate_phash(image_path: str):
        try:
            with Image.open(image_path) as img:
                return imagehash.phash(img)
        except Exception:
            return None

    def check_duplicate(self, new_image_path: str, existing_image_path: str) -> dict:
        if not os.path.exists(new_image_path) or not os.path.exists(existing_image_path):
            return {
                "similarity_score": 0.0,
                "is_duplicate": False,
                "error": "One or both image files do not exist at the provided paths.",
            }

        hash1 = self.calculate_phash(new_image_path)
        hash2 = self.calculate_phash(existing_image_path)

        if hash1 is None or hash2 is None:
            return {
                "similarity_score": 0.0,
                "is_duplicate": False,
                "error": "Failed to calculate hash. Image file might be corrupted.",
            }

        hamming_distance = hash1 - hash2
        max_bits = len(hash1.hash) ** 2
        similarity = (1.0 - (hamming_distance / max_bits)) * 100

        is_duplicate = bool(hamming_distance <= 10)

        return {
            "similarity_score": round(similarity, 2),
            "is_duplicate": is_duplicate,
        }
