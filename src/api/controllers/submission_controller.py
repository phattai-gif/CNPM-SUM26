from flask import (
    Blueprint,
    jsonify,
    request,
    render_template,
)

import hashlib
import io
import json
import os

from PIL import Image

from api.role_required import (
    token_required,
    role_required,
)

from infrastructure.repositories.submission_repository import (
    SubmissionRepository,
)

from services.submission_service import (
    SubmissionService,
)

from services.score_service import ScoreService


# ============================================================
# BLUEPRINT
# ============================================================

submission_bp = Blueprint(
    "submission",
    __name__,
    url_prefix="/submissions",
)


# ============================================================
# FILE CONFIGURATION
# ============================================================

ALLOWED_IMAGE_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
}

ALLOWED_IMAGE_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
}

ALLOWED_PROOF_FILE_TYPES = {
    "main_image",
    "negative",
    "contact_sheet",
}


KEY_TO_FILE_TYPE = {
    "main_image": "main_image",
    "file": "main_image",
    "files": "main_image",
    "image": "main_image",
    "images": "main_image",
    "main": "main_image",
    "main_file": "main_image",
    "image_files": "main_image",

    "negative": "negative",
    "negative_film": "negative",
    "negatives": "negative",
    "negative[]": "negative",
    "negative_film[]": "negative",
    "negative_files": "negative",
    "negative_file": "negative",
    "negative_images": "negative",
    "negative_image": "negative",

    "contact_sheet": "contact_sheet",
    "contact_sheets": "contact_sheet",
    "contact_sheet[]": "contact_sheet",
    "contact_sheet_files": "contact_sheet",
    "contact_sheet_file": "contact_sheet",
    "contact_sheet_images": "contact_sheet",
}


# ============================================================
# SERVICES
# ============================================================

submission_repo = SubmissionRepository()

submission_service = SubmissionService(
    submission_repo=submission_repo,
)

score_service = ScoreService()


# ============================================================
# HELPERS
# ============================================================

def _get_user_id():
    return request.user.get("user_id")


def _get_user_role():
    return request.user.get("role")


# ============================================================
# SERIALIZATION
# ============================================================

def _serialize_submission(submission):
    return {
        "id": submission.id,
        "round_id": submission.round_id,
        "user_id": submission.user_id,
        "title": submission.title,
        "story_description": getattr(
            submission,
            "story_description",
            None,
        ),
        "status": submission.status,
        "final_score": (
            float(submission.final_score)
            if getattr(
                submission,
                "final_score",
                None,
            ) is not None
            else None
        ),
        "submitted_at": (
            submission.submitted_at.isoformat()
            if getattr(
                submission,
                "submitted_at",
                None,
            )
            else None
        ),
        "created_at": (
            submission.created_at.isoformat()
            if getattr(
                submission,
                "created_at",
                None,
            )
            else None
        ),
        "updated_at": (
            submission.updated_at.isoformat()
            if getattr(
                submission,
                "updated_at",
                None,
            )
            else None
        ),
    }


def _serialize_submission_file(file_obj):
    if file_obj is None:
        return None

    if isinstance(file_obj, dict):
        created_at = file_obj.get("created_at")

        if hasattr(created_at, "isoformat"):
            created_at = created_at.isoformat()

        file_type = file_obj.get("file_type")

        if file_type == "negative_film":
            file_type = "negative"

        if not file_type:
            file_type = "main_image"

        return {
            "id": file_obj.get("id"),
            "file_type": file_type,
            "image_hd_url": file_obj.get(
                "image_hd_url"
            ),
            "thumbnail_url": file_obj.get(
                "thumbnail_url"
            ),
            "width_px": file_obj.get(
                "width_px"
            ),
            "height_px": file_obj.get(
                "height_px"
            ),
            "file_size_bytes": file_obj.get(
                "file_size_bytes"
            ),
            "file_hash": file_obj.get(
                "file_hash"
            ),
            "ahash": file_obj.get(
                "ahash"
            ),
            "created_at": created_at,
        }

    created_at = getattr(
        file_obj,
        "created_at",
        None,
    )

    file_type = getattr(
        file_obj,
        "file_type",
        None,
    )

    if file_type == "negative_film":
        file_type = "negative"

    if not file_type:
        file_type = "main_image"

    return {
        "id": getattr(
            file_obj,
            "id",
            None,
        ),
        "file_type": file_type,
        "image_hd_url": getattr(
            file_obj,
            "image_hd_url",
            None,
        ),
        "thumbnail_url": getattr(
            file_obj,
            "thumbnail_url",
            None,
        ),
        "width_px": getattr(
            file_obj,
            "width_px",
            None,
        ),
        "height_px": getattr(
            file_obj,
            "height_px",
            None,
        ),
        "file_size_bytes": getattr(
            file_obj,
            "file_size_bytes",
            None,
        ),
        "file_hash": getattr(
            file_obj,
            "file_hash",
            None,
        ),
        "ahash": getattr(
            file_obj,
            "ahash",
            None,
        ),
        "created_at": (
            created_at.isoformat()
            if created_at
            else None
        ),
    }


def _serialize_submission_detail(
    submission,
    files=None,
    film_metadata=None,
):
    response = {
        "id": submission.id,
        "round_id": submission.round_id,
        "user_id": submission.user_id,
        "title": submission.title,
        "story_description": getattr(
            submission,
            "story_description",
            None,
        ),
        "status": submission.status,
        "final_score": (
            float(submission.final_score)
            if getattr(
                submission,
                "final_score",
                None,
            ) is not None
            else None
        ),
        "submitted_at": (
            submission.submitted_at.isoformat()
            if getattr(
                submission,
                "submitted_at",
                None,
            )
            else None
        ),
        "created_at": (
            submission.created_at.isoformat()
            if getattr(
                submission,
                "created_at",
                None,
            )
            else None
        ),
        "updated_at": (
            submission.updated_at.isoformat()
            if getattr(
                submission,
                "updated_at",
                None,
            )
            else None
        ),
        "files": {
            "main_image": [],
            "negative": [],
            "contact_sheet": [],
        },
    }

    # --------------------------------------------------------
    # FILES
    # --------------------------------------------------------

    if files is not None:
        if isinstance(files, dict):
            grouped_files = files

            for file_type, file_items in grouped_files.items():
                if file_type not in response["files"]:
                    continue

                if not isinstance(file_items, (list, tuple)):
                    file_items = [file_items]

                for item in file_items:
                    serialized = _serialize_submission_file(item)

                    if serialized:
                        response["files"][file_type].append(
                            serialized
                        )

        else:
            if not isinstance(files, (list, tuple)):
                files = [files]

            serialized_files = [
                _serialize_submission_file(item)
                for item in files
                if item is not None
            ]

            for file_item in serialized_files:
                file_type = file_item.get("file_type")

                if file_type == "main_image":
                    response["files"]["main_image"].append(
                        file_item
                    )

                elif file_type in {
                    "negative",
                    "negative_film",
                }:
                    response["files"]["negative"].append(
                        file_item
                    )

                elif file_type == "contact_sheet":
                    response["files"]["contact_sheet"].append(
                        file_item
                    )

    # --------------------------------------------------------
    # BACKWARD COMPATIBILITY
    # --------------------------------------------------------

    main_files = response["files"].get(
        "main_image",
        [],
    )

    main_file = (
        main_files[0]
        if main_files
        else None
    )

    if main_file is None:
        negative_files = response["files"].get(
            "negative",
            [],
        )

        if negative_files:
            main_file = negative_files[0]

    if main_file is None:
        contact_sheet_files = response["files"].get(
            "contact_sheet",
            [],
        )

        if contact_sheet_files:
            main_file = contact_sheet_files[0]

    response["file"] = main_file

    # --------------------------------------------------------
    # FILM METADATA
    # --------------------------------------------------------

    if film_metadata:
        if isinstance(
            film_metadata,
            dict,
        ):
            response["film_metadata"] = film_metadata

        else:
            created_at = getattr(
                film_metadata,
                "created_at",
                None,
            )

            response["film_metadata"] = {
                "film_stock": getattr(
                    film_metadata,
                    "film_stock",
                    None,
                ),
                "film_iso": getattr(
                    film_metadata,
                    "film_iso",
                    None,
                ),
                "camera_body": getattr(
                    film_metadata,
                    "camera_body",
                    None,
                ),
                "lens": getattr(
                    film_metadata,
                    "lens",
                    None,
                ),
                "lab_name": getattr(
                    film_metadata,
                    "lab_name",
                    None,
                ),
                "scanner_info": getattr(
                    film_metadata,
                    "scanner_info",
                    None,
                ),
                "development_process": getattr(
                    film_metadata,
                    "development_process",
                    None,
                ),
                "taken_at_location": getattr(
                    film_metadata,
                    "taken_at_location",
                    None,
                ),
                "created_at": (
                    created_at.isoformat()
                    if created_at
                    else None
                ),
            }

    else:
        response["film_metadata"] = None

    return response


# ============================================================
# IMAGE VALIDATION
# ============================================================

def _validate_image_file(file_obj):
    if file_obj is None:
        raise ValueError("No image file provided")

    filename = (
        getattr(
            file_obj,
            "filename",
            None,
        )
        or ""
    ).strip()

    if not filename:
        raise ValueError("Filename is required")

    content_type = (
        getattr(
            file_obj,
            "content_type",
            None,
        )
        or ""
    ).lower().strip()

    extension = os.path.splitext(
        filename
    )[1].lower()

    # --------------------------------------------------------
    # MIME TYPE
    # --------------------------------------------------------

    if content_type not in ALLOWED_IMAGE_TYPES:
        raise ValueError("Invalid file type")

    # --------------------------------------------------------
    # EXTENSION
    # --------------------------------------------------------

    if extension not in ALLOWED_IMAGE_EXTENSIONS:
        raise ValueError("Invalid file extension")

    # --------------------------------------------------------
    # READ
    # --------------------------------------------------------

    try:
        file_bytes = file_obj.read()
    except Exception as error:
        raise ValueError(
            f"Failed to read file {filename}: {error}"
        )

    if not file_bytes:
        raise ValueError(
            f"File content is empty for {filename}"
        )

    # --------------------------------------------------------
    # VERIFY IMAGE
    # --------------------------------------------------------

    try:
        image = Image.open(
            io.BytesIO(file_bytes)
        )
        image.verify()

    except Exception:
        raise ValueError(
            f"Invalid image file for {filename}"
        )

    return (
        file_bytes,
        filename,
        content_type,
    )


# ============================================================
# FILE TYPE RESOLUTION
# ============================================================

def _normalize_file_type(file_type):
    if file_type is None:
        return None

    value = str(
        file_type
    ).strip().lower()

    aliases = {
        "main": "main_image",
        "main_image": "main_image",
        "main-file": "main_image",
        "main_file": "main_image",
        "image": "main_image",
        "file": "main_image",
        "files": "main_image",

        "negative": "negative",
        "negative_film": "negative",
        "negative-file": "negative",
        "negative_file": "negative",
        "negative_image": "negative",
        "negative_images": "negative",
        "negatives": "negative",

        "contact_sheet": "contact_sheet",
        "contact-sheet": "contact_sheet",
        "contact_sheet_file": "contact_sheet",
        "contact_sheet_files": "contact_sheet",
        "contact_sheet_image": "contact_sheet",
        "contact_sheet_images": "contact_sheet",
        "contact_sheets": "contact_sheet",
    }

    return aliases.get(value)


def _get_file_type_from_field_name(field_name):
    if not field_name:
        return None

    key = str(
        field_name
    ).strip().lower()

    # --------------------------------------------------------
    # MAIN IMAGE
    # --------------------------------------------------------

    if key in {
        "file",
        "image",
        "main_image",
        "main_file",
        "main",
        "files",
        "images",
        "image_files",
    }:
        return "main_image"

    # --------------------------------------------------------
    # NEGATIVE
    # --------------------------------------------------------

    if key in {
        "negative",
        "negative_files",
        "negative_file",
        "negative_film",
        "negative_images",
        "negative_image",
    }:
        return "negative"

    # --------------------------------------------------------
    # CONTACT SHEET
    # --------------------------------------------------------

    if key in {
        "contact_sheet_files",
        "contact_sheet_file",
        "contact_sheet",
        "contact_sheets",
        "contact_sheet_images",
    }:
        return "contact_sheet"

    return None


# ============================================================
# COLLECT UPLOADED FILES
# ============================================================

def _collect_uploaded_files(strict=False):
    uploaded_files = []

    for key in request.files:
        file_objects = request.files.getlist(key)

        field_name = str(key).strip().lower()

        # ----------------------------------------------------
        # RESOLVE FILE TYPE
        # ----------------------------------------------------

        file_type = _get_file_type_from_field_name(
            field_name
        )

        if file_type is None:
            # Try file_type from request body.
            form_file_type = (
                request.form.get("file_type")
                or request.args.get("file_type")
            )

            file_type = _normalize_file_type(
                form_file_type
            )

        if file_type is None:
            if strict:
                raise ValueError(
                    "Invalid file type. "
                    "Allowed fields: "
                    "main_image, negative, negative_film, "
                    "contact_sheet"
                )

            continue

        # ----------------------------------------------------
        # COLLECT ALL FILES
        # ----------------------------------------------------

        for file_obj in file_objects:
            if (
                file_obj is None
                or not getattr(
                    file_obj,
                    "filename",
                    None,
                )
            ):
                continue

            uploaded_files.append(
                {
                    "file_obj": file_obj,
                    "file_type": file_type,
                }
            )

    return uploaded_files


# ============================================================
# BUILD FILE PAYLOAD
# ============================================================

def _build_file_payload(
    file_obj,
    file_type,
):
    normalized_type = _normalize_file_type(
        file_type
    )

    allowed_types = {
        "main_image",
        "negative",
        "negative_film",
        "contact_sheet",
    }

    if normalized_type not in allowed_types:
        raise ValueError(
            "Invalid file type. "
            "Allowed values: "
            "main_image, negative, negative_film, "
            "contact_sheet"
        )

    if normalized_type == "negative_film":
        normalized_type = "negative"

    (
        file_bytes,
        filename,
        content_type,
    ) = _validate_image_file(
        file_obj
    )

    return {
        "file_bytes": file_bytes,
        "filename": filename,
        "content_type": content_type,
        "file_type": normalized_type,
        "file_hash": hashlib.sha256(
            file_bytes
        ).hexdigest(),
    }


# ============================================================
# FILM METADATA
# ============================================================

def _parse_film_metadata(data):
    film_metadata = {}

    film_metadata_json = data.get(
        "film_metadata"
    )

    if film_metadata_json:
        try:
            parsed_metadata = (
                json.loads(film_metadata_json)
                if isinstance(
                    film_metadata_json,
                    str,
                )
                else film_metadata_json
            )

        except (
            ValueError,
            TypeError,
        ):
            raise ValueError(
                "film_metadata must be valid JSON"
            )

        if not isinstance(
            parsed_metadata,
            dict,
        ):
            raise ValueError(
                "film_metadata must be a JSON object"
            )

        film_metadata.update(
            parsed_metadata
        )

    metadata_fields = {
        "film_stock": data.get("film_stock"),
        "film_iso": data.get("film_iso"),
        "camera_body": data.get("camera_body"),
        "lens": data.get("lens"),
        "lab_name": data.get("lab_name"),
        "scanner_info": data.get("scanner_info"),
        "development_process": data.get(
            "development_process"
        ),
        "taken_at_location": data.get(
            "taken_at_location"
        ),
    }

    for key, value in metadata_fields.items():
        if value is not None:
            film_metadata[key] = value

    if (
        "film_iso" in film_metadata
        and film_metadata["film_iso"] is not None
    ):
        try:
            film_metadata["film_iso"] = int(
                film_metadata["film_iso"]
            )

        except (
            ValueError,
            TypeError,
        ):
            raise ValueError(
                "film_iso must be an integer"
            )

    return film_metadata


# ============================================================
# HEALTH
# ============================================================

@submission_bp.route(
    "/health",
    methods=["GET"],
)
def submission_health():
    return jsonify(
        {
            "message": "Submission router is working!"
        }
    ), 200


# ============================================================
# GENERIC IMAGE UPLOAD
# ============================================================

@submission_bp.route(
    "/upload",
    methods=["POST"],
)
@token_required
def upload_submission_image():
    image_file = request.files.get("file")

    if image_file is None:
        return jsonify(
            {
                "message": "No image file provided"
            }
        ), 400

    try:
        (
            file_bytes,
            filename,
            content_type,
        ) = _validate_image_file(
            image_file
        )

        storage_info = (
            submission_service.upload_submission_image(
                file_bytes=file_bytes,
                filename=filename,
                content_type=content_type,
            )
        )

        return jsonify(
            {
                "message": "File uploaded successfully",
                "storage": storage_info,
            }
        ), 200

    except ValueError as error:
        return jsonify(
            {
                "message": str(error)
            }
        ), 400

    except Exception as error:
        return jsonify(
            {
                "message": "Failed to upload image",
                "error": str(error),
            }
        ), 500


# ============================================================
# CREATE SUBMISSION
# ============================================================

@submission_bp.route(
    "",
    methods=["POST"],
)
@token_required
def create_submission():
    user_id = _get_user_id()

    if not user_id:
        return jsonify(
            {
                "message": (
                    "User information is missing "
                    "in token"
                )
            }
        ), 401

    data = request.form

    round_id = data.get("round_id")
    title = data.get("title")

    if not round_id:
        return jsonify(
            {
                "message": "round_id is required"
            }
        ), 400

    try:
        round_id = int(round_id)

    except (
        ValueError,
        TypeError,
    ):
        return jsonify(
            {
                "message": "round_id must be an integer"
            }
        ), 400

    status = data.get(
        "status",
        "draft",
    )

    allowed_statuses = {
        "draft",
        "submitted",
        "flagged",
        "evaluated",
    }

    if status not in allowed_statuses:
        return jsonify(
            {
                "message": "Invalid status"
            }
        ), 400

    if status in {
        "flagged",
        "evaluated",
    }:
        return jsonify(
            {
                "message": "Forbidden status transition"
            }
        ), 403

    # --------------------------------------------------------
    # TITLE
    # --------------------------------------------------------

    if status == "submitted":
        if not title or not title.strip():
            return jsonify(
                {
                    "message": "title is required"
                }
            ), 400

        title = title.strip()

    if title:
        title = title.strip()

    # --------------------------------------------------------
    # COLLECT FILES
    # --------------------------------------------------------

    try:
        uploaded_files = _collect_uploaded_files(
            strict=True
        )

    except ValueError as error:
        return jsonify(
            {
                "message": str(error)
            }
        ), 400

    if status == "submitted" and not uploaded_files:
        return jsonify(
            {
                "message": "No image file provided"
            }
        ), 400

    main_files = [
        item
        for item in uploaded_files
        if item["file_type"] == "main_image"
    ]

    if status == "submitted" and not main_files:
        return jsonify(
            {
                "message": "No main image file provided"
            }
        ), 400

    # --------------------------------------------------------
    # BUILD ALL FILE PAYLOADS
    # --------------------------------------------------------

    files_list = []

    for uploaded_file in uploaded_files:
        try:
            file_payload = _build_file_payload(
                file_obj=uploaded_file["file_obj"],
                file_type=uploaded_file["file_type"],
            )

            files_list.append(
                file_payload
            )

        except ValueError as error:
            return jsonify(
                {
                    "message": str(error)
                }
            ), 400

    # --------------------------------------------------------
    # FILM METADATA
    # --------------------------------------------------------

    try:
        film_metadata = _parse_film_metadata(
            data
        )

    except ValueError as error:
        return jsonify(
            {
                "message": str(error)
            }
        ), 400

    if (
        status == "submitted"
        and not film_metadata.get("film_stock")
    ):
        return jsonify(
            {
                "message": "Missing required field",
                "missing_fields": ["film_stock"],
            }
        ), 400

    if "development_process" not in film_metadata:
        film_metadata["development_process"] = "C-41"

    # --------------------------------------------------------
    # DESCRIPTION
    # --------------------------------------------------------

    description = (
        data.get("description")
        or data.get(
            "story_description",
            "",
        )
    )

    # --------------------------------------------------------
    # CREATE
    # --------------------------------------------------------

    try:
        submission = (
            submission_service.create_submission(
                round_id=round_id,
                user_id=user_id,
                title=title or "",
                files=files_list,
                film_metadata=film_metadata,
                story_description=description,
                status=status,
            )
        )

        return jsonify(
            {
                "message": (
                    "Submission created successfully"
                ),
                "submission": _serialize_submission(
                    submission
                ),
            }
        ), 201

    except ValueError as error:
        return jsonify(
            {
                "message": str(error)
            }
        ), 400

    except PermissionError as error:
        return jsonify(
            {
                "message": str(error)
            }
        ), 403

    except Exception as error:
        return jsonify(
            {
                "message": "Failed to create submission",
                "error": str(error),
            }
        ), 500


# ============================================================
# MY SUBMISSIONS
# ============================================================

@submission_bp.route(
    "/my",
    methods=["GET"],
)
@token_required
def get_my_submissions():
    user_id = _get_user_id()

    if not user_id:
        return jsonify(
            {
                "message": (
                    "User information is missing "
                    "in token"
                )
            }
        ), 401

    round_id_param = request.args.get(
        "round_id"
    )

    round_id = None

    if round_id_param is not None:
        try:
            round_id = int(
                round_id_param
            )

        except (
            ValueError,
            TypeError,
        ):
            return jsonify(
                {
                    "message": "Invalid round_id"
                }
            ), 400

    status = request.args.get(
        "status"
    )

    allowed_statuses = {
        "draft",
        "submitted",
        "flagged",
        "evaluated",
        "under_review",
        "graded",
        "approved",
        "rejected",
    }

    if status and status not in allowed_statuses:
        return jsonify(
            {
                "message": "Invalid status"
            }
        ), 400

    ai_flag = request.args.get(
        "ai_flag"
    )

    allowed_ai_flags = {
        "safe",
        "medium",
        "high",
    }

    if ai_flag and ai_flag not in allowed_ai_flags:
        return jsonify(
            {
                "message": "Invalid ai_flag"
            }
        ), 400

    try:
        data = submission_service.get_my_submissions(
            user_id=user_id,
            round_id=round_id,
            status=status,
            ai_flag=ai_flag,
        )

        if isinstance(data, dict):
            return jsonify(data), 200

        if isinstance(data, list):
            return jsonify(
                {
                    "message": (
                        "My submissions "
                        "retrieved successfully"
                    ),
                    "submissions": data,
                    "count": len(data),
                    "total": len(data),
                }
            ), 200

        return jsonify(data), 200

    except Exception as error:
        import traceback

        traceback.print_exc()

        return jsonify(
            {
                "message": "Failed to get my submissions",
                "error": str(error),
            }
        ), 500


# ============================================================
# ALIAS: /my-submissions
# ============================================================

@submission_bp.route(
    "/my-submissions",
    methods=["GET"],
)
@token_required
def get_my_submissions_alias():
    return get_my_submissions()


# ============================================================
# ALIAS: /me
# ============================================================

@submission_bp.route(
    "/me",
    methods=["GET"],
)
@token_required
def get_my_submissions_me():
    return get_my_submissions()


# ============================================================
# UI: MY SUBMISSIONS / PORTFOLIO
# ============================================================

@submission_bp.route(
    "/my-submissions-ui",
    methods=["GET"],
)
def my_submissions_ui():
    return render_template(
        "my_submissions.html"
    )


# ============================================================
# UI: SUBMISSION DETAIL
# ============================================================

@submission_bp.route(
    "/detail/<int:submission_id>",
    methods=["GET"],
)
def submission_detail_ui_detail(submission_id):
    return render_template(
        "submission_detail.html",
        submission_id=submission_id,
    )


# ============================================================
# UI: SUBMISSION DETAIL ALIAS
# ============================================================

@submission_bp.route(
    "/<int:submission_id>/ui",
    methods=["GET"],
)
def submission_detail_ui(submission_id):
    return render_template(
        "submission_detail.html",
        submission_id=submission_id,
    )


# ============================================================
# UPLOAD PROOF FILES
# ============================================================

@submission_bp.route(
    "/<int:submission_id>/proof-files",
    methods=["POST"],
)
@token_required
def upload_proof_files(submission_id):
    user_id = _get_user_id()

    if not user_id:
        return jsonify(
            {
                "message": (
                    "User information is missing "
                    "in token"
                )
            }
        ), 401

    requested_file_type = (
        request.form.get("file_type")
        or request.args.get("file_type")
    )

    file_type = _normalize_file_type(
        requested_file_type
    )

    if file_type not in ALLOWED_PROOF_FILE_TYPES:
        return jsonify(
            {
                "message": (
                    "Invalid file type. "
                    "Allowed values: "
                    "main_image, negative, contact_sheet"
                )
            }
        ), 400

    file_objects = []

    for key in request.files:
        file_objects.extend(
            request.files.getlist(key)
        )

    file_objects = [
        file_obj
        for file_obj in file_objects
        if (
            file_obj is not None
            and getattr(
                file_obj,
                "filename",
                None,
            )
        )
    ]

    if not file_objects:
        return jsonify(
            {
                "message": "No image file provided"
            }
        ), 400

    payloads = []

    for file_obj in file_objects:
        try:
            payload = _build_file_payload(
                file_obj=file_obj,
                file_type=file_type,
            )

            payloads.append(
                payload
            )

        except ValueError as error:
            return jsonify(
                {
                    "message": str(error)
                }
            ), 400

    try:
        result = None

        if hasattr(
            submission_service,
            "upload_submission_proof_files",
        ):
            result = (
                submission_service
                .upload_submission_proof_files(
                    submission_id=submission_id,
                    user_id=user_id,
                    files=payloads,
                )
            )

        elif hasattr(
            submission_service,
            "upload_proof_files",
        ):
            result = (
                submission_service
                .upload_proof_files(
                    submission_id=submission_id,
                    user_id=user_id,
                    files=payloads,
                )
            )

        elif hasattr(
            submission_repo,
            "upload_proof_files",
        ):
            result = (
                submission_repo.upload_proof_files(
                    submission_id=submission_id,
                    user_id=user_id,
                    files=payloads,
                )
            )

        else:
            raise AttributeError(
                "Proof file upload service is not available"
            )

        if result is None:
            result = []

        if not isinstance(
            result,
            (list, tuple),
        ):
            result = [result]

        serialized = [
            _serialize_submission_file(item)
            for item in result
            if item is not None
        ]

        return jsonify(
            {
                "message": (
                    "Proof files uploaded successfully"
                ),
                "files": serialized,
            }
        ), 201

    except PermissionError as error:
        return jsonify(
            {
                "message": str(error)
            }
        ), 403

    except ValueError as error:
        return jsonify(
            {
                "message": str(error)
            }
        ), 400

    except Exception as error:
        return jsonify(
            {
                "message": (
                    "Failed to upload proof files"
                ),
                "error": str(error),
            }
        ), 500


# ============================================================
# UPDATE DRAFT
# ============================================================

@submission_bp.route(
    "/<int:submission_id>",
    methods=["PUT", "PATCH"],
)
@token_required
def update_submission(submission_id):
    user_id = _get_user_id()

    if not user_id:
        return jsonify(
            {
                "message": (
                    "User information is missing "
                    "in token"
                )
            }
        ), 401

    if request.is_json:
        data = request.get_json(
            silent=True
        ) or {}
    else:
        data = request.form

    title = data.get("title")

    if title is not None:
        title = title.strip()

        if not title:
            return jsonify(
                {
                    "message": "title is required"
                }
            ), 400

    description = (
        data.get("description")
        if data.get("description") is not None
        else data.get("story_description")
    )

    # --------------------------------------------------------
    # COLLECT FILES
    # --------------------------------------------------------

    try:
        uploaded_files = _collect_uploaded_files(
            strict=True
        )

    except ValueError as error:
        return jsonify(
            {
                "message": str(error)
            }
        ), 400

    files_list = []

    for uploaded_file in uploaded_files:
        try:
            file_payload = _build_file_payload(
                file_obj=uploaded_file["file_obj"],
                file_type=uploaded_file["file_type"],
            )

            files_list.append(
                file_payload
            )

        except ValueError as error:
            return jsonify(
                {
                    "message": str(error)
                }
            ), 400

    # --------------------------------------------------------
    # FILM METADATA
    # --------------------------------------------------------

    try:
        film_metadata = _parse_film_metadata(
            data
        )

    except ValueError as error:
        return jsonify(
            {
                "message": str(error)
            }
        ), 400

    # --------------------------------------------------------
    # UPDATE
    # --------------------------------------------------------

    try:
        update_method = getattr(
            submission_service,
            "update_draft_submission",
            None,
        )

        if update_method is not None:
            try:
                updated_sub = update_method(
                    submission_id=submission_id,
                    user_id=user_id,
                    title=title,
                    story_description=description,
                    round_id=data.get("round_id"),
                    status=data.get("status"),
                    film_metadata=(
                        film_metadata
                        or None
                    ),
                    files=files_list,
                )

            except TypeError:
                updated_sub = update_method(
                    submission_id=submission_id,
                    user_id=user_id,
                    title=title,
                    story_description=description,
                    round_id=data.get("round_id"),
                    status=data.get("status"),
                    film_metadata=(
                        film_metadata
                        or None
                    ),
                )

        else:
            updated_sub = submission_service.update_draft(
                submission_id=submission_id,
                user_id=user_id,
                title=title,
                story_description=description,
                files=files_list,
                film_metadata=(
                    film_metadata
                    or None
                ),
            )

        if updated_sub is None:
            return jsonify(
                {
                    "message": "Submission not found"
                }
            ), 404

        return jsonify(
            {
                "message": (
                    "Submission updated successfully"
                ),
                "submission": _serialize_submission(
                    updated_sub
                ),
            }
        ), 200

    except PermissionError as error:
        return jsonify(
            {
                "message": str(error)
            }
        ), 403

    except ValueError as error:
        err_msg = str(error)

        if "not found" in err_msg.lower():
            return jsonify(
                {
                    "message": err_msg
                }
            ), 404

        return jsonify(
            {
                "message": err_msg
            }
        ), 400

    except Exception as error:
        import traceback

        traceback.print_exc()

        return jsonify(
            {
                "message": (
                    "Failed to update submission draft"
                ),
                "error": str(error),
            }
        ), 500


# ============================================================
# SUBMIT DRAFT
# ============================================================

@submission_bp.route(
    "/<int:submission_id>/submit",
    methods=["POST"],
)
@token_required
def submit_submission(submission_id):
    user_id = _get_user_id()

    if not user_id:
        return jsonify(
            {
                "message": (
                    "User information is missing "
                    "in token"
                )
            }
        ), 401

    try:
        submitted_sub = (
            submission_service.submit_draft(
                submission_id=submission_id,
                user_id=user_id,
            )
        )

        return jsonify(
            {
                "message": (
                    "Submission submitted successfully"
                ),
                "submission": {
                    "id": submitted_sub.id,
                    "status": submitted_sub.status,
                },
            }
        ), 200

    except PermissionError as error:
        return jsonify(
            {
                "message": str(error)
            }
        ), 403

    except ValueError as error:
        err_msg = str(error)

        if "not found" in err_msg.lower():
            return jsonify(
                {
                    "message": err_msg
                }
            ), 404

        return jsonify(
            {
                "message": err_msg
            }
        ), 400

    except Exception as error:
        return jsonify(
            {
                "message": (
                    "Failed to submit submission"
                ),
                "error": str(error),
            }
        ), 500


# ============================================================
# GET SUBMISSION DETAIL
# ============================================================

@submission_bp.route(
    "/<int:submission_id>",
    methods=["GET"],
)
@role_required(
    "organizer",
    "judge",
    "participant",
)
def get_submission(submission_id):
    user_id = _get_user_id()
    role = _get_user_role() or "participant"

    # --------------------------------------------------------
    # PRIMARY SERVICE
    # --------------------------------------------------------

    try:
        detail = (
            submission_service
            .get_submission_detail(
                submission_id=submission_id,
                user_id=user_id,
                role=role,
            )
        )

        if detail:
            if isinstance(detail, dict):
                detail = dict(detail)

                # --------------------------------------------
                # NORMALIZE FILES
                # --------------------------------------------

                source_files = detail.get(
                    "files"
                )

                if source_files is None:
                    source_files = []

                # If service returns grouped files.
                if isinstance(
                    source_files,
                    dict,
                ):
                    grouped_files = {
                        "main_image": [],
                        "negative": [],
                        "contact_sheet": [],
                    }

                    for file_type, file_items in source_files.items():
                        normalized_type = (
                            _normalize_file_type(
                                file_type
                            )
                        )

                        if normalized_type not in grouped_files:
                            continue

                        if not isinstance(
                            file_items,
                            (list, tuple),
                        ):
                            file_items = [
                                file_items
                            ]

                        for item in file_items:
                            serialized = (
                                _serialize_submission_file(
                                    item
                                )
                            )

                            if serialized:
                                grouped_files[
                                    normalized_type
                                ].append(
                                    serialized
                                )

                    detail["files"] = grouped_files

                else:
                    if not isinstance(
                        source_files,
                        (list, tuple),
                    ):
                        source_files = [
                            source_files
                        ]

                    normalized_files = []

                    for item in source_files:
                        if item is None:
                            continue

                        serialized = (
                            _serialize_submission_file(
                                item
                            )
                        )

                        if serialized:
                            normalized_files.append(
                                serialized
                            )

                    files_group = {
                        "main_image": [],
                        "negative": [],
                        "contact_sheet": [],
                    }

                    for item in normalized_files:
                        file_type = item.get(
                            "file_type"
                        )

                        if file_type == "main_image":
                            files_group[
                                "main_image"
                            ].append(item)

                        elif file_type in {
                            "negative",
                            "negative_film",
                        }:
                            files_group[
                                "negative"
                            ].append(item)

                        elif file_type == "contact_sheet":
                            files_group[
                                "contact_sheet"
                            ].append(item)

                    detail["files"] = files_group

                # --------------------------------------------
                # BACKWARD COMPATIBILITY
                # --------------------------------------------

                main_files = detail[
                    "files"
                ]["main_image"]

                main_file = (
                    main_files[0]
                    if main_files
                    else None
                )

                if main_file is None:
                    negative_files = detail[
                        "files"
                    ]["negative"]

                    if negative_files:
                        main_file = negative_files[0]

                if main_file is None:
                    contact_sheet_files = detail[
                        "files"
                    ]["contact_sheet"]

                    if contact_sheet_files:
                        main_file = contact_sheet_files[0]

                detail["file"] = main_file

                return jsonify(
                    detail
                ), 200

            if hasattr(
                detail,
                "id",
            ):
                files = getattr(
                    detail,
                    "files",
                    None,
                )

                if files is None:
                    files = getattr(
                        detail,
                        "submission_files",
                        None,
                    )

                return jsonify(
                    _serialize_submission_detail(
                        submission=detail,
                        files=files,
                    )
                ), 200

    except PermissionError as error:
        return jsonify(
            {
                "message": str(error)
            }
        ), 403

    except Exception:
        # Fall through to repository/service fallback.
        pass

    # --------------------------------------------------------
    # FALLBACK
    # --------------------------------------------------------

    try:
        result = submission_service.get_submission_by_id(
            submission_id
        )

    except Exception as error:
        return jsonify(
            {
                "message": "Failed to get submission",
                "error": str(error),
            }
        ), 500

    if not result:
        return jsonify(
            {
                "message": "Submission not found"
            }
        ), 404

    try:
        if isinstance(result, dict):
            submission = result.get(
                "submission"
            )
            files = result.get(
                "files",
                [],
            )
            film_metadata = result.get(
                "film_metadata"
            )

        else:
            if isinstance(
                result,
                (list, tuple),
            ):
                if len(result) >= 3:
                    (
                        submission,
                        submission_file,
                        film_metadata,
                    ) = result

                    if isinstance(
                        submission_file,
                        (list, tuple),
                    ):
                        files = list(
                            submission_file
                        )

                    elif submission_file:
                        files = [
                            submission_file
                        ]

                    else:
                        files = []

                elif len(result) >= 1:
                    submission = result[0]
                    files = []
                    film_metadata = None

                else:
                    submission = None
                    files = []
                    film_metadata = None

            else:
                submission = result
                files = []
                film_metadata = None

        if not submission:
            return jsonify(
                {
                    "message": "Submission not found"
                }
            ), 404

        # ----------------------------------------------------
        # PARTICIPANT ACCESS CONTROL
        # ----------------------------------------------------

        if role == "participant":
            if submission.user_id != user_id:
                return jsonify(
                    {
                        "message": (
                            "You are not allowed "
                            "to view this submission"
                        )
                    }
                ), 403

        # ----------------------------------------------------
        # SERIALIZE
        # ----------------------------------------------------

        response = _serialize_submission_detail(
            submission=submission,
            files=files,
            film_metadata=film_metadata,
        )

    except Exception as error:
        return jsonify(
            {
                "message": (
                    "Failed to serialize "
                    "submission details"
                ),
                "error": str(error),
            }
        ), 500

    # --------------------------------------------------------
    # AI FLAG
    # --------------------------------------------------------

    ai_flag_data = None

    try:
        existing_flag = submission_repo.get_ai_flag(
            submission_id
        )

        if existing_flag:
            ai_flag_data = {
                "ai_score": float(
                    existing_flag.confidence_score
                ),
                "risk_level": existing_flag.risk_level,
                "status": existing_flag.status,
            }

    except Exception:
        ai_flag_data = None

    response["ai_flag"] = ai_flag_data

    return jsonify(
        response
    ), 200


# ============================================================
# SUBMIT SCORE
# ============================================================

@submission_bp.route(
    "/<int:submission_id>/scores",
    methods=["POST"],
)
@role_required("judge")
def submit_score(submission_id):
    data = (
        request.get_json(
            silent=True
        )
        or {}
    )

    judge_id = request.user.get(
        "user_id"
    )

    criteria_id = data.get(
        "criteria_id"
    )

    score_value = data.get(
        "score_value"
    )

    comment = data.get(
        "comment"
    )

    if not criteria_id:
        return jsonify(
            {
                "message": "criteria_id is required"
            }
        ), 400

    if score_value is None:
        return jsonify(
            {
                "message": "score_value is required"
            }
        ), 400

    if not judge_id:
        return jsonify(
            {
                "message": (
                    "Judge information is missing"
                )
            }
        ), 401

    user_role = request.user.get(
        "role",
        "judge",
    )

    if (
        hasattr(
            score_service,
            "is_judge_assigned",
        )
        and not score_service.is_judge_assigned(
            submission_id=submission_id,
            judge_id=judge_id,
            user_role=user_role,
        )
    ):
        return jsonify(
            {
                "message": (
                    "Judge is not assigned "
                    "to this submission"
                )
            }
        ), 403

    model, error = (
        score_service.submit_score(
            submission_id=submission_id,
            judge_id=judge_id,
            criteria_id=criteria_id,
            score_value=score_value,
            comment=comment,
        )
    )

    if error == "submission_not_found":
        return jsonify(
            {
                "message": "Submission not found"
            }
        ), 404

    if error == "criteria_not_found":
        return jsonify(
            {
                "message": "Criteria not found"
            }
        ), 404

    if error == "invalid_score":
        return jsonify(
            {
                "message": "Invalid score value"
            }
        ), 400

    return jsonify(
        {
            "message": "Score saved successfully",
            "score": {
                "id": model.id,
                "submission_id": model.submission_id,
                "judge_id": model.judge_id,
                "criteria_id": model.criteria_id,
                "score_value": float(
                    model.score_value
                ),
                "comment": model.comment,
            },
        }
    ), 200


# ============================================================
# SUBMIT FEEDBACK
# ============================================================

@submission_bp.route(
    "/<int:submission_id>/feedback",
    methods=["POST"],
)
@role_required("judge")
def submit_feedback(submission_id):
    data = (
        request.get_json(
            silent=True
        )
        or {}
    )

    judge_id = request.user.get(
        "user_id"
    )

    summary_feedback = data.get(
        "summary_feedback"
    )

    final_recommendation = data.get(
        "final_recommendation"
    )

    if not judge_id:
        return jsonify(
            {
                "message": (
                    "Judge information is missing"
                )
            }
        ), 401

    if not summary_feedback:
        return jsonify(
            {
                "message": (
                    "summary_feedback is required"
                )
            }
        ), 400

    user_role = request.user.get(
        "role",
        "judge",
    )

    if (
        hasattr(
            score_service,
            "is_judge_assigned",
        )
        and not score_service.is_judge_assigned(
            submission_id=submission_id,
            judge_id=judge_id,
            user_role=user_role,
        )
    ):
        return jsonify(
            {
                "message": (
                    "Judge is not assigned "
                    "to this submission"
                )
            }
        ), 403

    model, error = (
        score_service.submit_feedback(
            submission_id=submission_id,
            judge_id=judge_id,
            summary_feedback=summary_feedback,
            final_recommendation=final_recommendation,
        )
    )

    if error == "submission_not_found":
        return jsonify(
            {
                "message": "Submission not found"
            }
        ), 404

    return jsonify(
        {
            "message": "Feedback saved successfully",
            "feedback": {
                "id": model.id,
                "submission_id": model.submission_id,
                "judge_id": model.judge_id,
                "summary_feedback": (
                    model.summary_feedback
                ),
                "final_recommendation": (
                    model.final_recommendation
                ),
            },
        }
    ), 200


# ============================================================
# CALCULATE SCORE
# ============================================================

@submission_bp.route(
    "/<int:submission_id>/calculate-score",
    methods=["POST"],
)
@token_required
def calculate_submission_score(submission_id):
    user_role = request.user.get(
        "role"
    )

    if user_role not in {
        "organizer",
        "admin",
        "judge",
    }:
        return jsonify(
            {
                "message": "Forbidden access"
            }
        ), 403

    submission, error = (
        score_service.calculate_submission_score(
            submission_id
        )
    )

    if error == "submission_not_found":
        return jsonify(
            {
                "message": "Submission not found"
            }
        ), 404

    return jsonify(
        {
            "message": (
                "Submission score calculated successfully"
            ),
            "submission": {
                "id": submission.id,
                "final_score": (
                    float(
                        submission.final_score
                    )
                    if submission.final_score is not None
                    else None
                ),
            },
        }
    ), 200


# ============================================================
# NEXT SUBMISSION
# ============================================================

@submission_bp.route(
    "/<int:submission_id>/next",
    methods=["GET"],
)
@role_required("judge")
def get_next_submission(submission_id):
    result, error = (
        score_service.get_next_previous(
            submission_id
        )
    )

    if error == "submission_not_found":
        return jsonify(
            {
                "message": "Submission not found"
            }
        ), 404

    if error == "db_error":
        return jsonify(
            {
                "message": "Database error"
            }
        ), 500

    if (
        result is None
        or result.get("next") is None
    ):
        return jsonify(
            {
                "message": "No next submission"
            }
        ), 404

    return jsonify(
        result
    ), 200


# ============================================================
# PREVIOUS SUBMISSION
# ============================================================

@submission_bp.route(
    "/<int:submission_id>/previous",
    methods=["GET"],
)
@role_required("judge")
def get_previous_submission(submission_id):
    result, error = (
        score_service.get_previous_submission(
            submission_id
        )
    )

    if error == "submission_not_found":
        return jsonify(
            {
                "message": "Submission not found"
            }
        ), 404

    if error == "db_error":
        return jsonify(
            {
                "message": "Database error"
            }
        ), 500

    if result is None:
        return jsonify(
            {
                "message": "No previous submission"
            }
        ), 404

    return jsonify(
        {
            "submission": result
        }
    ), 200


# ============================================================
# LIST SUBMISSIONS
# ============================================================

@submission_bp.route(
    "",
    methods=["GET"],
)
@token_required
def list_submissions():
    try:
        submissions = (
            submission_service
            .list_submissions()
        )

        return jsonify(
            [
                {
                    "id": item.id,
                    "round_id": item.round_id,
                    "user_id": item.user_id,
                    "title": item.title,
                    "story_description": (
                        getattr(
                            item,
                            "story_description",
                            None,
                        )
                    ),
                    "status": item.status,
                    "final_score": (
                        float(
                            item.final_score
                        )
                        if item.final_score is not None
                        else None
                    ),
                    "submitted_at": (
                        item.submitted_at.isoformat()
                        if item.submitted_at
                        else None
                    ),
                }
                for item in submissions
            ]
        ), 200

    except Exception as error:
        return jsonify(
            {
                "message": (
                    "Failed to list submissions"
                ),
                "error": str(error),
            }
        ), 500

# ============================================================
# ORGANIZER CONTEST SUBMISSIONS
# ============================================================

@submission_bp.route(
    "/contest/<int:contest_id>",
    methods=["GET"],
)
@role_required(
    "organizer",
    "admin",
)
def get_organizer_contest_submissions(
    contest_id,
):
    user_id = _get_user_id()
    user_role = _get_user_role()

    if not user_id:
        return jsonify(
            {
                "message": (
                    "User information is missing "
                    "in token"
                )
            }
        ), 401

    round_id_param = request.args.get(
        "round_id"
    )

    round_id = None

    if round_id_param is not None:
        try:
            round_id = int(
                round_id_param
            )

        except (
            ValueError,
            TypeError,
        ):
            return jsonify(
                {
                    "message": "Invalid round_id"
                }
            ), 400

    status = request.args.get(
        "status"
    )

    if status and status not in {
        "draft",
        "submitted",
        "flagged",
        "evaluated",
    }:
        return jsonify(
            {
                "message": "Invalid status"
            }
        ), 400

    ai_flag = request.args.get(
        "ai_flag"
    )

    if (
        ai_flag
        and ai_flag not in {
            "safe",
            "medium",
            "high",
        }
    ):
        return jsonify(
            {
                "message": "Invalid ai_flag"
            }
        ), 400

    try:
        data = (
            submission_service
            .get_organizer_submissions(
                contest_id=contest_id,
                user_id=user_id,
                user_role=user_role,
                round_id=round_id,
                status=status,
                ai_flag=ai_flag,
            )
        )

        return jsonify(
            data
        ), 200

    except ValueError as error:
        return jsonify(
            {
                "message": str(error)
            }
        ), 404

    except PermissionError as error:
        return jsonify(
            {
                "message": str(error)
            }
        ), 403

    except Exception as error:
        return jsonify(
            {
                "message": (
                    "Failed to get organizer "
                    "contest submissions"
                ),
                "error": str(error),
            }
        ), 500


# ============================================================
# JUDGE ASSIGNMENT SUBMISSIONS
# ============================================================

@submission_bp.route(
    "/assignments/<int:assignment_id>",
    methods=["GET"],
)
@role_required(
    "judge",
    "admin",
)
def get_judge_assignment_submissions(
    assignment_id,
):
    user_id = _get_user_id()
    user_role = _get_user_role()

    if not user_id:
        return jsonify(
            {
                "message": (
                    "User information is missing "
                    "in token"
                )
            }
        ), 401

    round_id_param = request.args.get(
        "round_id"
    )

    round_id = None

    if round_id_param is not None:
        try:
            round_id = int(
                round_id_param
            )

        except (
            ValueError,
            TypeError,
        ):
            return jsonify(
                {
                    "message": "Invalid round_id"
                }
            ), 400

    status = request.args.get(
        "status"
    )

    if status and status not in {
        "draft",
        "submitted",
        "flagged",
        "evaluated",
    }:
        return jsonify(
            {
                "message": "Invalid status"
            }
        ), 400

    ai_flag = request.args.get(
        "ai_flag"
    )

    if (
        ai_flag
        and ai_flag not in {
            "safe",
            "medium",
            "high",
        }
    ):
        return jsonify(
            {
                "message": "Invalid ai_flag"
            }
        ), 400

    try:
        data = (
            submission_service
            .get_judge_assignment_submissions(
                assignment_id=assignment_id,
                user_id=user_id,
                user_role=user_role,
                round_id=round_id,
                status=status,
                ai_flag=ai_flag,
            )
        )

        return jsonify(
            data
        ), 200

    except ValueError as error:
        return jsonify(
            {
                "message": str(error)
            }
        ), 404

    except PermissionError as error:
        return jsonify(
            {
                "message": str(error)
            }
        ), 403

    except Exception as error:
        return jsonify(
            {
                "message": (
                    "Failed to get judge "
                    "assignment submissions"
                ),
                "error": str(error),
            }
        ), 500


# ============================================================
# FLAGGED SUBMISSIONS
# ============================================================

@submission_bp.route(
    "/flagged",
    methods=["GET"],
)
@role_required(
    "organizer",
    "admin",
)
def get_flagged_submissions():
    status = request.args.get(
        "status"
    )

    allowed_flag_statuses = {
        "pending",
        "confirmed violation",
        "dismissed",
    }

    if (
        status
        and status not in allowed_flag_statuses
    ):
        return jsonify(
            {
                "message": "Invalid status"
            }
        ), 400

    try:
        data = (
            submission_service
            .get_flagged_submissions(
                status=status
            )
        )

        return jsonify(
            data
        ), 200

    except Exception as error:
        return jsonify(
            {
                "message": (
                    "Failed to get flagged submissions"
                ),
                "error": str(error),
            }
        ), 500


# ============================================================
# UPDATE FLAG STATUS
# ============================================================

@submission_bp.route(
    "/flags/<int:flag_id>/status",
    methods=["PUT", "PATCH"],
)
@role_required(
    "organizer",
    "admin",
)
def update_flag_status(flag_id):
    if request.is_json:
        data = (
            request.get_json(
                silent=True
            )
            or {}
        )

    else:
        data = request.form

    status = data.get(
        "status"
    )

    if not status:
        return jsonify(
            {
                "message": "status is required"
            }
        ), 400

    if status not in {
        "pending",
        "confirmed violation",
        "dismissed",
    }:
        return jsonify(
            {
                "message": "Invalid status"
            }
        ), 400

    try:
        flag = (
            submission_service
            .update_flag_status(
                flag_id,
                status,
            )
        )

        if not flag:
            return jsonify(
                {
                    "message": "Flag not found"
                }
            ), 404

        return jsonify(
            {
                "message": (
                    "Flag status updated successfully"
                ),
                "flag": flag,
            }
        ), 200

    except Exception as error:
        return jsonify(
            {
                "message": (
                    "Failed to update flag status"
                ),
                "error": str(error),
            }
        ), 500


# ============================================================
# GET AI REPORT
# ============================================================

@submission_bp.route(
    "/<int:submission_id>/ai-report",
    methods=["GET"],
)
@role_required(
    "organizer",
    "admin",
    "moderator",
    "judge",
)
def get_submission_ai_report_api(submission_id):
    try:
        report = (
            submission_service
            .get_submission_ai_report(
                submission_id
            )
        )

        return jsonify(
            report
        ), 200

    except Exception as error:
        return jsonify(
            {
                "message": "Failed to get AI report",
                "error": str(error),
            }
        ), 500