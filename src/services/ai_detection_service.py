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
