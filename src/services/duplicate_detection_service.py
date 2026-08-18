import os

from PIL import Image
import imagehash


class DuplicateDetectionService:
    """Service to detect duplicate images by comparing perceptual hashes (pHash and aHash)."""

    @staticmethod
    def calculate_phash(image_path: str):
        try:
            with Image.open(image_path) as img:
                return imagehash.phash(img.convert('L'))
        except Exception:
            return None

    @staticmethod
    def calculate_ahash(image_path: str):
        try:
            with Image.open(image_path) as img:
                return imagehash.average_hash(img.convert('L'))
        except Exception:
            return None

    def check_duplicate(self, new_image_path: str, existing_image_path: str) -> dict:
        if not os.path.exists(new_image_path) or not os.path.exists(existing_image_path):
            return {
                "similarity_score": 0.0,
                "is_duplicate": False,
                "error": "One or both image files do not exist at the provided paths.",
            }

        phash1 = self.calculate_phash(new_image_path)
        phash2 = self.calculate_phash(existing_image_path)
        ahash1 = self.calculate_ahash(new_image_path)
        ahash2 = self.calculate_ahash(existing_image_path)

        if None in (phash1, phash2, ahash1, ahash2):
            return {
                "similarity_score": 0.0,
                "is_duplicate": False,
                "error": "Failed to calculate hash. Image file might be corrupted.",
            }

        phash_distance = phash1 - phash2
        ahash_distance = ahash1 - ahash2
        max_bits = len(phash1.hash) ** 2

        phash_similarity = (1.0 - (phash_distance / max_bits)) * 100
        ahash_similarity = (1.0 - (ahash_distance / max_bits)) * 100
        similarity = round((phash_similarity + ahash_similarity) / 2.0, 2)

        is_duplicate = bool(phash_distance <= 18 or ahash_distance <= 12)

        return {
            "similarity_score": similarity,
            "is_duplicate": is_duplicate,
            "phash_distance": int(phash_distance),
            "ahash_distance": int(ahash_distance),
        }

