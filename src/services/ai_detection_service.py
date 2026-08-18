import os

try:
    import exifread
except ImportError:
    exifread = None


import os

try:
    import exifread
except ImportError:
    exifread = None


class AiDetectionService:

    def detect_ai(self, image_path: str) -> dict:
        """Analyze the image by EXIF metadata and return structured EXIF and risk level."""
        if not image_path:
            return {
                "ai_score": 0,
                "ai_message": "Error: image_path is empty",
                "risk_level": "safe",
                "exif_data": {},
                "raw_exif": {}
            }

        # Resolve path or URL
        local_path = image_path
        temp_downloaded_file = None
        
        # If it is a URL (http/https)
        if image_path.startswith("http://") or image_path.startswith("https://"):
            # Check if it points to local static uploads
            if "/static/uploads/" in image_path:
                filename = image_path.split("/static/uploads/")[-1]
                # Resolve relative to project root
                project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
                local_path = os.path.join(project_root, "frontend", "static", "uploads", filename)
            else:
                # Remote URL, download to a temporary file
                try:
                    import urllib.request
                    import tempfile
                    suffix = os.path.splitext(image_path.split("?")[0])[1].lower() or ".jpg"
                    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
                        urllib.request.urlretrieve(image_path, temp_file.name)
                        local_path = temp_file.name
                        temp_downloaded_file = temp_file.name
                except Exception as e:
                    # Fallback to whatever was passed
                    pass
        elif image_path.startswith("/static/uploads/"):
            filename = image_path.split("/static/uploads/")[-1]
            project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
            local_path = os.path.join(project_root, "frontend", "static", "uploads", filename)

        if not os.path.exists(local_path):
            return {
                "ai_score": 0,
                "ai_message": f"Error: File does not exist at path {local_path}",
                "risk_level": "safe",
                "exif_data": {},
                "raw_exif": {}
            }

        try:
            exif_data = self.extract_exif(local_path)

            ai_score = 0
            reasons = []
            raw_exif = {}

            if not exif_data:
                ai_score = 85
                reasons.append("Image is completely missing EXIF metadata.")
                risk_level = "high"
                exif_payload = {
                    "camera_model": "Unknown",
                    "lens": "Unknown",
                    "iso": "Unknown",
                    "aperture": "Unknown",
                    "shutter_speed": "Unknown",
                    "date_taken": "Unknown"
                }
            else:
                camera_model = exif_data.get("camera_model", "Unknown")
                lens = exif_data.get("lens", "Unknown")
                iso = exif_data.get("iso", "Unknown")
                aperture = exif_data.get("aperture", "Unknown")
                shutter_speed = exif_data.get("shutter_speed", "Unknown")
                date_taken = exif_data.get("date_taken", "Unknown")
                raw_exif = exif_data.get("raw_exif", {})

                exif_payload = {
                    "camera_model": camera_model,
                    "lens": lens,
                    "iso": iso,
                    "aperture": aperture,
                    "shutter_speed": shutter_speed,
                    "date_taken": date_taken
                }

                has_camera = camera_model != "Unknown"
                has_exposure = (aperture != "Unknown" or shutter_speed != "Unknown" or iso != "Unknown")

                missing_count = sum(1 for v in exif_payload.values() if v == "Unknown")

                if has_camera and has_exposure:
                    if missing_count == 0:
                        ai_score = 0
                        reasons.append(f"Verified real capture device: {camera_model} | Lens: {lens} (ISO: {iso}, Aperture: {aperture}, Shutter: {shutter_speed}). Date taken: {date_taken}. EXIF is fully intact.")
                    else:
                        ai_score = 10 if missing_count == 1 else 15
                        reasons.append(f"Verified real capture device: {camera_model} | Lens: {lens} (ISO: {iso}, Aperture: {aperture}, Shutter: {shutter_speed}). Some metadata is missing.")
                elif has_camera:
                    ai_score = 30
                    reasons.append(f"Device identified: {camera_model}, but lacking exposure settings (ISO: {iso}, Aperture: {aperture}, Shutter: {shutter_speed}).")
                elif has_exposure:
                    ai_score = 45
                    reasons.append(f"Image contains exposure settings (ISO: {iso}, Aperture: {aperture}, Shutter: {shutter_speed}) but capture device is missing.")
                else:
                    ai_score = 85
                    reasons.append("Image is completely missing capture device information and exposure settings.")

                if ai_score >= 70 or missing_count >= 5:
                    risk_level = "high"
                elif ai_score >= 30 or missing_count >= 3:
                    risk_level = "medium"
                else:
                    risk_level = "safe"

            final_score = min(100, max(0, ai_score))

            if risk_level == "high":
                status = "HIGH AI RISK"
            elif risk_level == "medium":
                status = "SUSPICIOUS AI"
            else:
                status = "SAFE"

            ai_message = f"[{status}] " + " ".join(reasons)

            return {
                "ai_score": final_score,
                "ai_message": ai_message,
                "risk_level": risk_level,
                "exif_data": exif_payload,
                "raw_exif": raw_exif
            }
        finally:
            if temp_downloaded_file and os.path.exists(temp_downloaded_file):
                try:
                    os.remove(temp_downloaded_file)
                except Exception:
                    pass

    @staticmethod
    def extract_exif(image_path: str):
        """Extract EXIF metadata from a specific image file."""
        if not exifread:
            return None
        try:
            with open(image_path, "rb") as file:
                tags = exifread.process_file(file, details=False)

            if not tags:
                return None

            # Date Taken fallback
            date_taken = "Unknown"
            for tag in ["EXIF DateTimeOriginal", "Image DateTime", "EXIF DateTimeDigitized"]:
                if tag in tags:
                    date_taken = str(tags[tag])
                    break

            raw_exif = {}
            for key, val in tags.items():
                if "JPEGThumbnail" not in key and "TIFFThumbnail" not in key:
                    raw_exif[str(key)] = str(val)

            return {
                "camera_model": str(tags.get("Image Model", "Unknown")),
                "lens": str(tags.get("EXIF LensModel", "Unknown")),
                "iso": str(tags.get("EXIF ISOSpeedRatings", "Unknown")),
                "aperture": str(tags.get("EXIF FNumber", "Unknown")),
                "shutter_speed": str(tags.get("EXIF ExposureTime", "Unknown")),
                "date_taken": date_taken,
                "raw_exif": raw_exif
            }
        except Exception:
            return None

    @staticmethod
    def compare_metadata_with_exif(declared_metadata: dict, exif_data: dict) -> dict:
        """
        Compare user declared metadata (camera_body, lens, film_iso) with extracted EXIF metadata.
        """
        def normalize_val(val):
            if val is None:
                return ""
            s = str(val).strip().lower()
            if s in ["", "none", "unknown", "n/a", "null", "undefined"]:
                return ""
            return s

        def extract_digits(s):
            return "".join(c for c in s if c.isdigit())

        declared_metadata = declared_metadata or {}
        exif_data = exif_data or {}

        # 1. Compare Camera
        user_cam = normalize_val(declared_metadata.get("camera_body"))
        exif_cam = normalize_val(exif_data.get("camera_model"))
        if not user_cam or not exif_cam:
            camera_status = "insufficient data"
        elif user_cam in exif_cam or exif_cam in user_cam:
            camera_status = "match"
        else:
            camera_status = "mismatch"

        # 2. Compare Lens
        user_lens = normalize_val(declared_metadata.get("lens"))
        exif_lens = normalize_val(exif_data.get("lens"))
        if not user_lens or not exif_lens:
            lens_status = "insufficient data"
        elif user_lens in exif_lens or exif_lens in user_lens:
            lens_status = "match"
        else:
            lens_status = "mismatch"

        # 3. Compare ISO
        user_iso = normalize_val(declared_metadata.get("film_iso"))
        exif_iso = normalize_val(exif_data.get("iso"))
        if not user_iso or not exif_iso:
            iso_status = "insufficient data"
        else:
            u_digits = extract_digits(user_iso)
            e_digits = extract_digits(exif_iso)
            if u_digits and e_digits and u_digits == e_digits:
                iso_status = "match"
            elif user_iso in exif_iso or exif_iso in user_iso:
                iso_status = "match"
            else:
                iso_status = "mismatch"

        mismatched_fields = []
        if camera_status == "mismatch":
            mismatched_fields.append("camera")
        if lens_status == "mismatch":
            mismatched_fields.append("lens")
        if iso_status == "mismatch":
            mismatched_fields.append("iso")

        # Determine risk level and confidence score
        if mismatched_fields:
            risk_level = "high"
            confidence_score = 80.0 + 10.0 * len(mismatched_fields)
        elif camera_status == "match" or lens_status == "match" or iso_status == "match":
            # No mismatch, at least one match
            risk_level = "safe"
            confidence_score = 0.0
        else:
            # No mismatch, but all are insufficient data
            risk_level = "medium"
            confidence_score = 30.0

        return {
            "comparison": {
                "camera": {
                    "user": declared_metadata.get("camera_body") or "",
                    "exif": exif_data.get("camera_model") or "Unknown",
                    "status": camera_status
                },
                "lens": {
                    "user": declared_metadata.get("lens") or "",
                    "exif": exif_data.get("lens") or "Unknown",
                    "status": lens_status
                },
                "iso": {
                    "user": declared_metadata.get("film_iso") or "",
                    "exif": exif_data.get("iso") or "Unknown",
                    "status": iso_status
                }
            },
            "mismatched_fields": mismatched_fields,
            "risk_level": risk_level,
            "confidence_score": confidence_score
        }
