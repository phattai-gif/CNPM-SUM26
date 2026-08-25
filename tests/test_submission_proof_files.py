import os
import sys
import io
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock

import pytest
import jwt
from PIL import Image


# =========================================================
# PATH SETUP
# =========================================================

PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..")
)

SRC_ROOT = os.path.join(PROJECT_ROOT, "src")

if SRC_ROOT not in sys.path:
    sys.path.insert(0, SRC_ROOT)


# =========================================================
# DATABASE PATCH
# =========================================================

import src.infrastructure.databases.database_postgres as db_pg_module

# Không khởi tạo database thật khi chạy test
db_pg_module.DatabasePostgres.init_database = (
    lambda self, app: None
)


# =========================================================
# APPLICATION IMPORTS
# =========================================================

from app import create_app

import src.api.controllers.submission_controller as submission_controller_module

from services.submission_service import SubmissionService

from infrastructure.services.storage.local_storage_adapter import (
    LocalStorageAdapter,
)

from services.storage_service import StorageService


# =========================================================
# HELPERS
# =========================================================

def patch_controller_attr(attr_name, value):
    """
    Patch controller dependency cho cả 2 kiểu module import
    có thể xuất hiện trong project.
    """

    module_names = [
        "src.api.controllers.submission_controller",
        "api.controllers.submission_controller",
    ]

    patched = False

    for module_name in module_names:
        module = sys.modules.get(module_name)

        if module is None:
            continue

        setattr(module, attr_name, value)
        patched = True

        # Nếu patch repository thì tạo lại service
        # để service sử dụng repository mock.
        if attr_name == "submission_repo":
            module.submission_service = SubmissionService(
                submission_repo=value
            )

    # Fallback: module đã import trực tiếp ở đầu file
    if not patched:
        setattr(
            submission_controller_module,
            attr_name,
            value,
        )

        if attr_name == "submission_repo":
            submission_controller_module.submission_service = (
                SubmissionService(
                    submission_repo=value
                )
            )


def generate_token(
    secret_key,
    user_id=1,
    username="testuser",
    role="participant",
):
    """
    Tạo JWT token dùng cho test API.
    """

    payload = {
        "user_id": user_id,
        "username": username,
        "role": role,
        "exp": datetime.now(timezone.utc)
        + timedelta(hours=1),
    }

    token = jwt.encode(
        payload,
        secret_key,
        algorithm="HS256",
    )

    if isinstance(token, bytes):
        token = token.decode("utf-8")

    return token


def create_sample_image(
    width=200,
    height=150,
    color=(0, 255, 0),
    format_name="JPEG",
):
    """
    Tạo image bytes giả để upload trong test.
    """

    image = Image.new(
        "RGB",
        (width, height),
        color=color,
    )

    buffer = io.BytesIO()

    image.save(
        buffer,
        format=format_name,
    )

    return buffer.getvalue()


class MockObject:
    """
    Object đơn giản dùng để mock SQLAlchemy model.
    """

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


# =========================================================
# FIXTURES
# =========================================================

@pytest.fixture(autouse=True)
def mock_hash_calculation():
    """
    Không chạy image hash thật trong các test upload.

    Điều này giúp test nhanh và không phụ thuộc
    imagehash / duplicate detection.
    """

    with patch.object(
        SubmissionService,
        "_calculate_image_hashes",
        return_value=(
            "mock_phash",
            "mock_ahash",
        ),
    ):
        yield


@pytest.fixture
def app():
    """
    Flask application dùng chung cho test.
    """

    application = create_app()

    return application


@pytest.fixture
def client(app):
    """
    Flask test client.
    """

    return app.test_client()


@pytest.fixture
def participant_token(app):
    """
    JWT token của participant user_id = 10.
    """

    return generate_token(
        app.config.get(
            "SECRET_KEY",
            "a_default_secret_key",
        ),
        user_id=10,
        role="participant",
    )


# =========================================================
# TEST A
# Upload main image thành công
# =========================================================

def test_upload_main_image_success(
    client,
    app,
    participant_token,
    tmp_path,
):
    img_bytes = create_sample_image(
        width=300,
        height=200,
        color=(255, 0, 0),
    )

    mock_submission = MockObject(
        id=101,
        round_id=1,
        user_id=10,
        title="Main Image Test",
        story_description="Testing main image upload",
        status="submitted",
        submitted_at=datetime.now(timezone.utc),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    adapter = LocalStorageAdapter(
        upload_folder=str(tmp_path),
        base_url="/static/uploads",
    )

    storage_service = StorageService(
        adapter=adapter,
    )

    mock_repo = MagicMock()
    mock_repo.session = None

    mock_repo.create_submission.return_value = (
        mock_submission
    )

    custom_service = SubmissionService(
        submission_repo=mock_repo,
        storage_service=storage_service,
    )

    patch_controller_attr(
        "submission_service",
        custom_service,
    )

    data = {
        "round_id": "1",
        "title": "Main Image Test",
        "description": "Testing main image upload",
        "film_stock": "Kodak Gold 200",
        "status": "submitted",
        "main_image": (
            io.BytesIO(img_bytes),
            "main.jpg",
            "image/jpeg",
        ),
    }

    response = client.post(
        "/submissions",
        data=data,
        content_type="multipart/form-data",
        headers={
            "Authorization": (
                f"Bearer {participant_token}"
            )
        },
    )

    assert response.status_code == 201

    json_data = response.get_json()

    assert (
        json_data["message"]
        == "Submission created successfully"
    )

    assert mock_repo.create_submission.called

    created_args = (
        mock_repo
        .create_submission
        .call_args[1]
    )

    assert "files_data" in created_args

    assert (
        created_args["files_data"][0]["file_type"]
        == "main_image"
    )


# =========================================================
# TEST B
# Upload một negative film
# =========================================================

def test_upload_single_negative_film_success(
    client,
    participant_token,
    tmp_path,
):
    main_image = create_sample_image(
        color=(255, 0, 0),
    )

    negative_image = create_sample_image(
        color=(0, 255, 0),
    )

    mock_submission = MockObject(
        id=102,
        round_id=1,
        user_id=10,
        title="Negative Test",
        status="submitted",
        submitted_at=datetime.now(timezone.utc),
    )

    adapter = LocalStorageAdapter(
        upload_folder=str(tmp_path),
        base_url="/static/uploads",
    )

    storage_service = StorageService(
        adapter=adapter,
    )

    mock_repo = MagicMock()
    mock_repo.session = None

    mock_repo.create_submission.return_value = (
        mock_submission
    )

    custom_service = SubmissionService(
        submission_repo=mock_repo,
        storage_service=storage_service,
    )

    patch_controller_attr(
        "submission_service",
        custom_service,
    )

    data = {
        "round_id": "1",
        "title": "Negative Test",
        "film_stock": "Fuji Superia 400",
        "status": "submitted",
        "main_image": (
            io.BytesIO(main_image),
            "main.jpg",
            "image/jpeg",
        ),
        "negative": (
            io.BytesIO(negative_image),
            "negative_01.jpg",
            "image/jpeg",
        ),
    }

    response = client.post(
        "/submissions",
        data=data,
        content_type="multipart/form-data",
        headers={
            "Authorization": (
                f"Bearer {participant_token}"
            )
        },
    )

    assert response.status_code == 201

    created_args = (
        mock_repo
        .create_submission
        .call_args[1]
    )

    files_data = created_args["files_data"]

    assert len(files_data) == 2

    file_types = [
        item["file_type"]
        for item in files_data
    ]

    assert "main_image" in file_types
    assert "negative" in file_types


# =========================================================
# TEST C
# Upload một contact sheet
# =========================================================

def test_upload_single_contact_sheet_success(
    client,
    participant_token,
    tmp_path,
):
    main_image = create_sample_image(
        color=(255, 0, 0),
    )

    contact_sheet = create_sample_image(
        color=(0, 0, 255),
    )

    mock_submission = MockObject(
        id=103,
        round_id=1,
        user_id=10,
        title="Contact Sheet Test",
        status="submitted",
    )

    adapter = LocalStorageAdapter(
        upload_folder=str(tmp_path),
        base_url="/static/uploads",
    )

    storage_service = StorageService(
        adapter=adapter,
    )

    mock_repo = MagicMock()
    mock_repo.session = None

    mock_repo.create_submission.return_value = (
        mock_submission
    )

    custom_service = SubmissionService(
        submission_repo=mock_repo,
        storage_service=storage_service,
    )

    patch_controller_attr(
        "submission_service",
        custom_service,
    )

    data = {
        "round_id": "1",
        "title": "Contact Sheet Test",
        "film_stock": "Ilford HP5",
        "status": "submitted",
        "main_image": (
            io.BytesIO(main_image),
            "main.jpg",
            "image/jpeg",
        ),
        "contact_sheet": (
            io.BytesIO(contact_sheet),
            "cs_01.jpg",
            "image/jpeg",
        ),
    }

    response = client.post(
        "/submissions",
        data=data,
        content_type="multipart/form-data",
        headers={
            "Authorization": (
                f"Bearer {participant_token}"
            )
        },
    )

    assert response.status_code == 201

    created_args = (
        mock_repo
        .create_submission
        .call_args[1]
    )

    files_data = created_args["files_data"]

    assert len(files_data) == 2

    file_types = [
        item["file_type"]
        for item in files_data
    ]

    assert "main_image" in file_types
    assert "contact_sheet" in file_types


# =========================================================
# TEST D
# Upload nhiều negative files
# =========================================================

def test_upload_multiple_negative_files(
    client,
    participant_token,
    tmp_path,
):
    main_image = create_sample_image(
        color=(255, 0, 0),
    )

    negative_1 = create_sample_image(
        color=(0, 255, 0),
    )

    negative_2 = create_sample_image(
        color=(0, 200, 0),
    )

    mock_submission = MockObject(
        id=104,
        round_id=1,
        user_id=10,
        title="Multi Negative Test",
        status="submitted",
    )

    adapter = LocalStorageAdapter(
        upload_folder=str(tmp_path),
        base_url="/static/uploads",
    )

    storage_service = StorageService(
        adapter=adapter,
    )

    mock_repo = MagicMock()
    mock_repo.session = None

    mock_repo.create_submission.return_value = (
        mock_submission
    )

    custom_service = SubmissionService(
        submission_repo=mock_repo,
        storage_service=storage_service,
    )

    patch_controller_attr(
        "submission_service",
        custom_service,
    )

    data = {
        "round_id": "1",
        "title": "Multi Negative Test",
        "film_stock": "Kodak Tri-X",
        "status": "submitted",
        "main_image": (
            io.BytesIO(main_image),
            "main.jpg",
            "image/jpeg",
        ),
        "negative": [
            (
                io.BytesIO(negative_1),
                "neg_01.jpg",
                "image/jpeg",
            ),
            (
                io.BytesIO(negative_2),
                "neg_02.jpg",
                "image/jpeg",
            ),
        ],
    }

    response = client.post(
        "/submissions",
        data=data,
        content_type="multipart/form-data",
        headers={
            "Authorization": (
                f"Bearer {participant_token}"
            )
        },
    )

    assert response.status_code == 201

    created_args = (
        mock_repo
        .create_submission
        .call_args[1]
    )

    files_data = created_args["files_data"]

    assert len(files_data) == 3

    negative_files = [
        item
        for item in files_data
        if item["file_type"] == "negative"
    ]

    assert len(negative_files) == 2


# =========================================================
# TEST E
# Upload nhiều contact sheet files
# =========================================================

def test_upload_multiple_contact_sheet_files(
    client,
    participant_token,
    tmp_path,
):
    main_image = create_sample_image(
        color=(255, 0, 0),
    )

    contact_sheet_1 = create_sample_image(
        color=(0, 0, 255),
    )

    contact_sheet_2 = create_sample_image(
        color=(0, 0, 200),
    )

    mock_submission = MockObject(
        id=105,
        round_id=1,
        user_id=10,
        title="Multi CS Test",
        status="submitted",
    )

    adapter = LocalStorageAdapter(
        upload_folder=str(tmp_path),
        base_url="/static/uploads",
    )

    storage_service = StorageService(
        adapter=adapter,
    )

    mock_repo = MagicMock()
    mock_repo.session = None

    mock_repo.create_submission.return_value = (
        mock_submission
    )

    custom_service = SubmissionService(
        submission_repo=mock_repo,
        storage_service=storage_service,
    )

    patch_controller_attr(
        "submission_service",
        custom_service,
    )

    data = {
        "round_id": "1",
        "title": "Multi CS Test",
        "film_stock": "Kodak Portra 800",
        "status": "submitted",
        "main_image": (
            io.BytesIO(main_image),
            "main.jpg",
            "image/jpeg",
        ),
        "contact_sheet": [
            (
                io.BytesIO(contact_sheet_1),
                "cs_01.jpg",
                "image/jpeg",
            ),
            (
                io.BytesIO(contact_sheet_2),
                "cs_02.jpg",
                "image/jpeg",
            ),
        ],
    }

    response = client.post(
        "/submissions",
        data=data,
        content_type="multipart/form-data",
        headers={
            "Authorization": (
                f"Bearer {participant_token}"
            )
        },
    )

    assert response.status_code == 201

    created_args = (
        mock_repo
        .create_submission
        .call_args[1]
    )

    files_data = created_args["files_data"]

    assert len(files_data) == 3

    contact_sheet_files = [
        item
        for item in files_data
        if item["file_type"] == "contact_sheet"
    ]

    assert len(contact_sheet_files) == 2


# =========================================================
# TEST F
# Upload invalid file type
# =========================================================

def test_upload_invalid_file_type(
    client,
    participant_token,
):
    image_bytes = create_sample_image()

    data = {
        "round_id": "1",
        "title": "Invalid File Type Test",
        "film_stock": "Kodak Gold 200",
        "status": "submitted",
        "invalid_type_key": (
            io.BytesIO(image_bytes),
            "image.jpg",
            "image/jpeg",
        ),
    }

    response = client.post(
        "/submissions",
        data=data,
        content_type="multipart/form-data",
        headers={
            "Authorization": (
                f"Bearer {participant_token}"
            )
        },
    )

    assert response.status_code == 400

    json_data = response.get_json()

    assert json_data is not None

    assert "Invalid file type" in (
        json_data.get("message", "")
    )


# =========================================================
# TEST G
# Participant không được xem submission của user khác
# =========================================================

def test_view_submission_detail_forbidden_for_other_participant(
    client,
    app,
):
    token = generate_token(
        app.config.get(
            "SECRET_KEY",
            "a_default_secret_key",
        ),
        user_id=99,
        role="participant",
    )

    mock_submission = MockObject(
        id=200,
        round_id=1,
        user_id=10,
        title="User 10 Photo",
        story_description="Private photo",
        status="submitted",
        final_score=None,
        submitted_at=datetime.now(timezone.utc),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    mock_file = MockObject(
        id=1,
        image_hd_url="http://example.com/hd.jpg",
        thumbnail_url="http://example.com/thumb.jpg",
        width_px=800,
        height_px=600,
        file_size_bytes=1000,
        file_hash="hash123",
        file_type="main_image",
        created_at=datetime.now(timezone.utc),
        phash=None,
        ahash=None,
    )

    mock_repo = MagicMock()

    # get_submission_detail() chỉ cần repository method này.
    mock_repo.session = None

    mock_repo.get_by_id_with_details.return_value = (
        mock_submission,
        mock_file,
        None,
    )

    mock_repo.get_all_ai_flags.return_value = []

    patch_controller_attr(
        "submission_repo",
        mock_repo,
    )

    response = client.get(
        "/submissions/200",
        headers={
            "Authorization": f"Bearer {token}"
        },
    )

    assert response.status_code == 403

    json_data = response.get_json()

    message = json_data.get(
        "message",
        "",
    )

    assert (
        "Access forbidden" in message
        or "allowed" in message
        or "Forbidden" in message
    )


# =========================================================
# TEST H
# Submission detail trả về:
# - main image
# - negative files
# - contact sheet files
# =========================================================

def test_submission_detail_returns_proof_files(
    client,
    participant_token,
):
    mock_submission = MockObject(
        id=300,
        round_id=1,
        user_id=10,
        title="Detail Proof Files Test",
        story_description="Story",
        status="submitted",
        final_score=8.5,
        submitted_at=datetime.now(timezone.utc),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    main_file = MockObject(
        id=1,
        submission_id=300,
        image_hd_url="http://example.com/main.jpg",
        thumbnail_url="http://example.com/main_t.jpg",
        width_px=1000,
        height_px=800,
        file_size_bytes=5000,
        file_hash="hash_main",
        file_type="main_image",
        created_at=datetime.now(timezone.utc),
        phash="p1",
        ahash="a1",
    )

    negative_file = MockObject(
        id=2,
        submission_id=300,
        image_hd_url="http://example.com/neg1.jpg",
        thumbnail_url=None,
        width_px=1000,
        height_px=800,
        file_size_bytes=4000,
        file_hash="hash_neg1",
        file_type="negative",
        created_at=datetime.now(timezone.utc),
        phash=None,
        ahash=None,
    )

    contact_sheet_file = MockObject(
        id=3,
        submission_id=300,
        image_hd_url="http://example.com/cs1.jpg",
        thumbnail_url=None,
        width_px=2000,
        height_px=1600,
        file_size_bytes=8000,
        file_hash="hash_cs1",
        file_type="contact_sheet",
        created_at=datetime.now(timezone.utc),
        phash=None,
        ahash=None,
    )

    mock_submission.files = [
        main_file,
        negative_file,
        contact_sheet_file,
    ]

    mock_repo = MagicMock()

    mock_repo.session = None

    mock_repo.get_by_id_with_details.return_value = (
        mock_submission,
        main_file,
        None,
    )

    mock_repo.get_all_ai_flags.return_value = []

    patch_controller_attr(
        "submission_repo",
        mock_repo,
    )

    response = client.get(
        "/submissions/300",
        headers={
            "Authorization": (
                f"Bearer {participant_token}"
            )
        },
    )

    assert response.status_code == 200

    json_data = response.get_json()

    assert json_data["id"] == 300

    assert "files" in json_data

    files_group = json_data["files"]

    # -----------------------------------------------------
    # Main image
    # -----------------------------------------------------

    assert "main_image" in files_group

    assert len(
        files_group["main_image"]
    ) == 1

    assert (
        files_group["main_image"][0][
            "image_hd_url"
        ]
        == "http://example.com/main.jpg"
    )

    # -----------------------------------------------------
    # Negative
    # -----------------------------------------------------

    assert "negative" in files_group

    assert len(
        files_group["negative"]
    ) == 1

    assert (
        files_group["negative"][0][
            "image_hd_url"
        ]
        == "http://example.com/neg1.jpg"
    )

    # -----------------------------------------------------
    # Contact sheet
    # -----------------------------------------------------

    assert "contact_sheet" in files_group

    assert len(
        files_group["contact_sheet"]
    ) == 1

    assert (
        files_group["contact_sheet"][0][
            "image_hd_url"
        ]
        == "http://example.com/cs1.jpg"
    )