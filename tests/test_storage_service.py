import os
import sys
import io
import hashlib
import jwt
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta, timezone
from PIL import Image

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from app import create_app
from services.storage_service import StorageService
from services.submission_service import SubmissionService
from infrastructure.services.storage.local_storage_adapter import LocalStorageAdapter
from infrastructure.services.storage.cloudinary_storage_adapter import CloudinaryStorageAdapter


def generate_token(secret_key, user_id=1, username="testuser", role="participant"):
    payload = {
        "user_id": user_id,
        "username": username,
        "role": role,
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),
    }
    return jwt.encode(payload, secret_key, algorithm="HS256")


def create_sample_image(width=400, height=300, color=(255, 0, 0), format_name="JPEG"):
    img = Image.new("RGB", (width, height), color=color)
    buf = io.BytesIO()
    img.save(buf, format=format_name)
    return buf.getvalue()


# Test 1: Upload local image success & verify metadata
def test_1_upload_local_image_success(tmp_path):
    upload_dir = str(tmp_path / "uploads")
    adapter = LocalStorageAdapter(upload_folder=upload_dir, base_url="/static/uploads")
    storage_svc = StorageService(adapter=adapter)

    img_bytes = create_sample_image(width=800, height=600)
    meta = storage_svc.upload_image(
        file_bytes=img_bytes,
        filename="photo.jpg",
        content_type="image/jpeg",
    )

    assert "hd_url" in meta
    assert "thumbnail_url" in meta
    assert meta["file_size"] == len(img_bytes)
    assert meta["width"] == 800
    assert meta["height"] == 600
    assert len(meta["sha256"]) == 64


# Test 2: Missing file validation
def test_2_missing_file_api():
    app = create_app()
    client = app.test_client()
    token = generate_token(app.config.get("SECRET_KEY", "a_default_secret_key"))

    res = client.post(
        "/submissions/upload",
        data={},
        content_type="multipart/form-data",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 400
    assert "No image file provided" in res.get_json()["message"]


# Test 3: Empty file validation
def test_3_empty_file_rejected():
    storage_svc = StorageService(provider="local")
    try:
        storage_svc.validate_file(b"", "empty.jpg")
        assert False, "Should raise ValueError for empty file"
    except ValueError as e:
        assert "empty" in str(e).lower()


# Test 4: Non-image file validation
def test_4_non_image_rejected():
    storage_svc = StorageService(provider="local")
    try:
        storage_svc.validate_file(b"test pdf content", "document.pdf", content_type="application/pdf")
        assert False, "Should raise ValueError for non-image file"
    except ValueError as e:
        assert "extension" in str(e).lower() or "mime" in str(e).lower()


# Test 5: Corrupt image file validation
def test_5_corrupted_image_rejected():
    storage_svc = StorageService(provider="local")
    corrupt_bytes = b"not a real image content fake header"
    try:
        storage_svc.upload_image(file_bytes=corrupt_bytes, filename="corrupt.jpg", content_type="image/jpeg")
        assert False, "Should raise ValueError for corrupted image file"
    except ValueError as e:
        assert "corrupted" in str(e).lower() or "invalid" in str(e).lower()


# Test 6: SHA-256 hash precision
def test_6_sha256_hash_precision():
    img_bytes = create_sample_image(width=100, height=100)
    expected_hash = hashlib.sha256(img_bytes).hexdigest()

    storage_svc = StorageService(provider="local")
    meta = storage_svc.upload_image(img_bytes, "test_hash.jpg", "image/jpeg")

    assert meta["sha256"] == expected_hash


# Test 7: Width and Height precision
def test_7_width_height_precision():
    img_bytes = create_sample_image(width=1024, height=768)
    storage_svc = StorageService(provider="local")
    meta = storage_svc.upload_image(img_bytes, "test_dim.jpg", "image/jpeg")

    assert meta["width"] == 1024
    assert meta["height"] == 768


# Test 8: Thumbnail creation & URL generation
def test_8_thumbnail_generated(tmp_path):
    adapter = LocalStorageAdapter(upload_folder=str(tmp_path), base_url="/static/uploads")
    storage_svc = StorageService(adapter=adapter)
    img_bytes = create_sample_image(width=1200, height=800)

    meta = storage_svc.upload_image(img_bytes, "landscape.jpg", "image/jpeg")

    assert meta["thumbnail_url"] != ""
    assert "thumb_" in meta["thumbnail_url"]


# Test 9: Upload API receives multipart/form-data
def test_9_api_multipart_upload_success():
    app = create_app()
    client = app.test_client()
    token = generate_token(app.config.get("SECRET_KEY", "a_default_secret_key"))

    img_bytes = create_sample_image(width=500, height=400)
    data = {"file": (io.BytesIO(img_bytes), "photo_entry.jpg", "image/jpeg")}

    res = client.post(
        "/submissions/upload",
        data=data,
        content_type="multipart/form-data",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert res.status_code == 200
    json_data = res.get_json()
    assert json_data["message"] == "File uploaded successfully"
    storage = json_data["storage"]
    assert storage["width"] == 500
    assert storage["height"] == 400
    assert storage["file_size"] == len(img_bytes)


# Test 10: API no longer requires base64
def test_10_api_no_base64_required():
    app = create_app()
    client = app.test_client()
    token = generate_token(app.config.get("SECRET_KEY", "a_default_secret_key"))

    img_bytes = create_sample_image()
    data = {
        "file": (io.BytesIO(img_bytes), "entry.png", "image/png"),
        "round_id": "1",
        "title": "My Entry",
        "film_stock": "Kodak Portra 400",
    }

    # Verify endpoint works without any base64 string
    res = client.post(
        "/submissions/upload",
        data={"file": (io.BytesIO(img_bytes), "entry.png", "image/png")},
        content_type="multipart/form-data",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    assert "base64" not in res.get_data(as_text=True).lower()


# Test 11: Mock Cloudinary Adapter in unit test
def test_11_mock_cloudinary_adapter():
    mock_cloudinary = MagicMock()
    mock_uploader = MagicMock()
    mock_uploader.upload.return_value = {
        "secure_url": "https://res.cloudinary.com/demo/image/upload/v1234/hd_sample.jpg",
        "public_id": "submissions/hd/sample_id",
    }
    mock_cloudinary.uploader = mock_uploader
    mock_cloudinary.utils = MagicMock()
    mock_cloudinary.utils.cloudinary_url.return_value = (
        "https://res.cloudinary.com/demo/image/upload/c_thumb/sample_id.jpg",
        None,
    )

    with patch.dict(sys.modules, {"cloudinary": mock_cloudinary, "cloudinary.uploader": mock_uploader}):
        adapter = CloudinaryStorageAdapter(
            cloud_name="demo_cloud",
            api_key="123456",
            api_secret="secret_key",
        )
        storage_svc = StorageService(adapter=adapter)

        img_bytes = create_sample_image()
        meta = storage_svc.upload_image(img_bytes, "cloud_photo.jpg", "image/jpeg")

        assert meta["hd_url"] == "https://res.cloudinary.com/demo/image/upload/v1234/hd_sample.jpg"
        assert mock_uploader.upload.called


# Test 12: Local provider works when no Cloudinary credentials exist
def test_12_local_provider_without_cloudinary_credentials():
    with patch.dict(os.environ, {"STORAGE_PROVIDER": "local"}, clear=True):
        svc = StorageService()
        assert svc.provider_name == "local"
        assert svc.adapter.__class__.__name__ == "LocalStorageAdapter"

        img_bytes = create_sample_image()
        meta = svc.upload_image(img_bytes, "offline.jpg", "image/jpeg")
        assert "/static/uploads/" in meta["hd_url"]



# Test 13: SubmissionService workflow integration
def test_13_submission_service_create_with_file_upload(tmp_path):
    mock_repo = MagicMock()
    mock_repo.create_submission.return_value = MagicMock(
        id=99,
        round_id=1,
        user_id=5,
        title="Photo Submission",
        story_description="A test story",
        status="submitted",
        submitted_at=datetime.now(timezone.utc),
    )

    adapter = LocalStorageAdapter(upload_folder=str(tmp_path), base_url="/static/uploads")
    storage_svc = StorageService(adapter=adapter)
    sub_service = SubmissionService(submission_repo=mock_repo, storage_service=storage_svc)

    img_bytes = create_sample_image(width=640, height=480)
    result = sub_service.create_submission(
        round_id=1,
        user_id=5,
        title="Photo Submission",
        file_bytes=img_bytes,
        filename="entry.jpg",
        content_type="image/jpeg",
        film_metadata={"film_stock": "Fuji C200"},
    )

    assert result.id == 99
    assert mock_repo.create_submission.called
