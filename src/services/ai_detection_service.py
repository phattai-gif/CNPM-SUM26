import os

try:
    import exifread
except ImportError:
    exifread = None


class AiDetectionService:


    def detect_ai(self, image_path: str) -> dict:
        """Analyze the image by EXIF metadata and return a score and message."""
        if not os.path.exists(image_path):
            return {
                "ai_score": 0,
                "ai_message": f"Error: File does not exist at path {image_path}",
            }

        exif_data = self.extract_exif(image_path)

        ai_score = 0
        reasons = []

        if not exif_data:
            ai_score = 80
            reasons.append("Cannot read or find EXIF metadata.")
        else:
            camera = exif_data.get("Camera", "Unknown")
            lens = exif_data.get("Lens", "Unknown")
            aperture = exif_data.get("Aperture", "Unknown")
            shutter = exif_data.get("Shutter Speed", "Unknown")
            iso = exif_data.get("ISO", "Unknown")

            has_camera = camera != "Unknown"
            has_exposure = (
                aperture != "Unknown" or shutter != "Unknown" or iso != "Unknown"
            )

            if has_camera and has_exposure:
                ai_score = 0
                lens_info = f" | Lens: {lens}" if lens != "Unknown" else ""
                reasons.append(
                    f"Verified real capture device: {camera}{lens_info} (ISO: {iso}, Aperture: {aperture}, Shutter: {shutter})."
                )
            elif has_camera:
                ai_score = 15
                reasons.append(
                    f"Device identified: {camera}, but lacking exposure details."
                )
            elif has_exposure:
                ai_score = 30
                reasons.append(
                    "Image contains exposure settings but the capture device name is missing or stripped."
                )
            else:
                ai_score = 85
                reasons.append(
                    "Image is completely missing capture device information and exposure settings."
                )

        final_score = min(100, max(0, ai_score))

        if final_score >= 70:
            status = "HIGH AI RISK"
        elif final_score >= 30:
            status = "SUSPICIOUS AI"
        else:
            status = "SAFE"

        ai_message = f"[{status}] " + " ".join(reasons)

        return {"ai_score": final_score, "ai_message": ai_message}

    @staticmethod
    def extract_exif(image_path: str):
        """Extract EXIF metadata from a specific image file."""
        if not exifread:
            return None
        try:
            with open(image_path, "rb") as file:
                tags = exifread.process_file(file)

            return {
                "File Name": os.path.basename(image_path),
                "Camera": str(tags.get("Image Model", "Unknown")),
                "Lens": str(tags.get("EXIF LensModel", "Unknown")),
                "Aperture": str(tags.get("EXIF FNumber", "Unknown")),
                "Shutter Speed": str(tags.get("EXIF ExposureTime", "Unknown")),
                "ISO": str(tags.get("EXIF ISOSpeedRatings", "Unknown")),
                "Film Stock": "N/A (Requires manual input during submission)",
            }
        except Exception:
            return None
