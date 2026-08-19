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

    @staticmethod
    def calculate_phash_from_bytes(file_bytes: bytes):
        try:
            import io
            with Image.open(io.BytesIO(file_bytes)) as img:
                return imagehash.phash(img.convert('L'))
        except Exception:
            return None

    @staticmethod
    def calculate_ahash_from_bytes(file_bytes: bytes):
        try:
            import io
            with Image.open(io.BytesIO(file_bytes)) as img:
                return imagehash.average_hash(img.convert('L'))
        except Exception:
            return None

    def check_duplicate_against_database(
        self,
        new_image_bytes: bytes,
        exclude_submission_id: int = None,
        session = None
    ) -> dict:
        phash1 = self.calculate_phash_from_bytes(new_image_bytes)
        ahash1 = self.calculate_ahash_from_bytes(new_image_bytes)

        if phash1 is None or ahash1 is None:
            return {
                "similarity_score": 0.0,
                "is_duplicate": False,
                "error": "Failed to calculate hash of the uploaded image.",
            }

        if session is None:
            try:
                from infrastructure.databases.factory_database import FactoryDatabase
                session = FactoryDatabase.get_database("POSTGREE").session
            except Exception:
                pass

        if not session:
            return {
                "similarity_score": 0.0,
                "is_duplicate": False,
                "error": "Database session not available.",
            }

        from infrastructure.models.app.app_submission_file_model import SubmissionFileModel

        query = session.query(SubmissionFileModel)
        if exclude_submission_id is not None:
            query = query.filter(SubmissionFileModel.submission_id != exclude_submission_id)
        
        existing_files = query.all()

        highest_similarity = 0.0
        is_duplicate = False
        matched_file = None
        min_phash_distance = 999
        min_ahash_distance = 999

        for ext_file in existing_files:
            phash2_str = ext_file.phash
            ahash2_str = ext_file.ahash

            if not phash2_str or not ahash2_str:
                local_path = ext_file.image_hd_url
                if local_path.startswith("http://") or local_path.startswith("https://") or local_path.startswith("/static/uploads/"):
                    if "/static/uploads/" in local_path:
                        filename = local_path.split("/static/uploads/")[-1]
                        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
                        local_path = os.path.join(project_root, "frontend", "static", "uploads", filename)
                    else:
                        try:
                            import urllib.request
                            import tempfile
                            suffix = os.path.splitext(local_path.split("?")[0])[1].lower() or ".jpg"
                            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
                                urllib.request.urlretrieve(ext_file.image_hd_url, temp_file.name)
                                local_path = temp_file.name
                        except Exception:
                            pass
                
                if os.path.exists(local_path):
                    ph2 = self.calculate_phash(local_path)
                    ah2 = self.calculate_ahash(local_path)
                    if ph2 and ah2:
                        ext_file.phash = str(ph2)
                        ext_file.ahash = str(ah2)
                        try:
                            session.commit()
                        except Exception:
                            session.rollback()
                        phash2_str = ext_file.phash
                        ahash2_str = ext_file.ahash

            if not phash2_str or not ahash2_str:
                continue

            try:
                phash2 = imagehash.hex_to_hash(phash2_str)
                ahash2 = imagehash.hex_to_hash(ahash2_str)
            except Exception:
                continue

            phash_distance = phash1 - phash2
            ahash_distance = ahash1 - ahash2
            max_bits = len(phash1.hash) ** 2

            phash_similarity = (1.0 - (phash_distance / max_bits)) * 100
            ahash_similarity = (1.0 - (ahash_distance / max_bits)) * 100
            similarity = round((phash_similarity + ahash_similarity) / 2.0, 2)

            file_is_duplicate = bool(phash_distance <= 18 or ahash_distance <= 12)

            if similarity > highest_similarity:
                highest_similarity = similarity
                is_duplicate = is_duplicate or file_is_duplicate
                matched_file = ext_file
                min_phash_distance = int(phash_distance)
                min_ahash_distance = int(ahash_distance)

        result = {
            "similarity_score": highest_similarity,
            "is_duplicate": is_duplicate,
            "phash": str(phash1),
            "ahash": str(ahash1),
        }
        if matched_file:
            result.update({
                "matched_submission_id": matched_file.submission_id,
                "matched_image_hd_url": matched_file.image_hd_url,
                "phash_distance": min_phash_distance,
                "ahash_distance": min_ahash_distance,
            })
        return result

