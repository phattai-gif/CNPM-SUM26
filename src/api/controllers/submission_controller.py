from flask import (
    Blueprint,
    jsonify,
    request,
    render_template,
)

import io
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


submission_bp = Blueprint(
    "submission",
    __name__,
    url_prefix="/submissions",
)


# ============================================================
# FILE VALIDATION
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


# ============================================================
# SERVICES
# ============================================================

submission_repo = SubmissionRepository()

submission_service = SubmissionService(
    submission_repo=submission_repo,
)

score_service = ScoreService()


# ============================================================
# HEALTH CHECK
# ============================================================

@submission_bp.route(
    "/health",
    methods=["GET"],
)
def submission_health():

    return jsonify({
        "message": "Submission router is working!"
    }), 200


# ============================================================
# UPLOAD IMAGE
# ============================================================

@submission_bp.route(
    "/upload",
    methods=["POST"],
)
@token_required
def upload_submission_image():

    image_file = request.files.get("file")

    if image_file is None:
        return jsonify({
            "message": "No image file provided"
        }), 400

    if not image_file.filename:
        return jsonify({
            "message": "Filename is required"
        }), 400

    filename = image_file.filename

    # --------------------------------------------------------
    # Validate MIME type
    # --------------------------------------------------------

    content_type = (
        image_file.content_type or ""
    ).lower()

    if content_type not in ALLOWED_IMAGE_TYPES:
        return jsonify({
            "message": "Invalid file type",
            "allowed_types": [
                "image/jpeg",
                "image/png",
                "image/webp",
            ],
        }), 400

    # --------------------------------------------------------
    # Validate extension
    # --------------------------------------------------------

    extension = os.path.splitext(
        filename
    )[1].lower()

    if extension not in ALLOWED_IMAGE_EXTENSIONS:
        return jsonify({
            "message": "Invalid file extension",
            "allowed_extensions": [
                ".jpg",
                ".jpeg",
                ".png",
                ".webp",
            ],
        }), 400

    try:

        file_bytes = image_file.read()

        if not file_bytes:
            return jsonify({
                "message": "File content is empty"
            }), 400

        # ----------------------------------------------------
        # Validate actual image
        # ----------------------------------------------------

        try:

            image = Image.open(
                io.BytesIO(file_bytes)
            )

            image.verify()

        except Exception:

            return jsonify({
                "message": (
                    f"Invalid image file "
                    f"for {filename}"
                ),
            }), 400

        # ----------------------------------------------------
        # Upload
        # ----------------------------------------------------

        storage_info = (
            submission_service
            .upload_submission_image(
                file_bytes=file_bytes,
                filename=filename,
                content_type=content_type,
            )
        )

        return jsonify({
            "message": "File uploaded successfully",
            "storage": storage_info,
        }), 200

    except ValueError as error:

        return jsonify({
            "message": str(error)
        }), 400

    except Exception as error:

        return jsonify({
            "message": "Failed to upload image",
            "error": str(error),
        }), 500


# ============================================================
# CREATE SUBMISSION
# MULTIPART/FORM-DATA
# ============================================================

@submission_bp.route(
    "",
    methods=["POST"],
)
@token_required
def create_submission():

    # --------------------------------------------------------
    # Get user from token
    # --------------------------------------------------------

    user_id = request.user.get("user_id")

    if not user_id:
        return jsonify({
            "message": (
                "User information is missing "
                "in token"
            )
        }), 401

    # --------------------------------------------------------
    # Form data
    # --------------------------------------------------------

    data = request.form

    round_id = data.get("round_id")
    title = data.get("title")

    # --------------------------------------------------------
    # Validate round_id
    # --------------------------------------------------------

    if not round_id:
        return jsonify({
            "message": "round_id is required"
        }), 400

    try:

        round_id = int(round_id)

    except (ValueError, TypeError):

        return jsonify({
            "message": "round_id must be an integer"
        }), 400

    # --------------------------------------------------------
    # Status
    # --------------------------------------------------------

    status = data.get(
        "status",
        "draft",
    )

    if status not in [
        "draft",
        "submitted",
        "flagged",
        "evaluated",
    ]:
        return jsonify({
            "message": "Invalid status"
        }), 400

    if status in [
        "flagged",
        "evaluated",
    ]:
        return jsonify({
            "message": "Forbidden status transition"
        }), 403

    # --------------------------------------------------------
    # Validate title
    # --------------------------------------------------------

    if status == "submitted":

        if not title or not title.strip():

            return jsonify({
                "message": "title is required"
            }), 400

        title = title.strip()

    elif title:
        title = title.strip()

    # ========================================================
    # GET FILES
    # ========================================================

    uploaded_files = []

    for key in request.files:

        file_objects = request.files.getlist(key)

        for file_obj in file_objects:

            if (
                file_obj
                and file_obj.filename
            ):
                uploaded_files.append(file_obj)

    # --------------------------------------------------------
    # At least one image for official submit
    # --------------------------------------------------------

    if (
        status == "submitted"
        and not uploaded_files
    ):
        return jsonify({
            "message": "No image file provided"
        }), 400

    # ========================================================
    # FILM METADATA
    # ========================================================

    film_metadata = {}

    # --------------------------------------------------------
    # JSON metadata
    # --------------------------------------------------------

    film_metadata_json = data.get(
        "film_metadata"
    )

    if film_metadata_json:

        try:

            import json

            parsed_metadata = json.loads(
                film_metadata_json
            )

            if isinstance(
                parsed_metadata,
                dict,
            ):
                film_metadata.update(
                    parsed_metadata
                )

        except (
            ValueError,
            TypeError,
        ):

            return jsonify({
                "message": (
                    "film_metadata must be valid JSON"
                )
            }), 400

    # --------------------------------------------------------
    # Individual metadata fields
    # --------------------------------------------------------

    metadata_fields = {
        "film_stock": data.get("film_stock"),
        "film_iso": data.get("film_iso"),
        "camera_body": data.get("camera_body"),
        "lens": data.get("lens"),
        "lab_name": data.get("lab_name"),
        "scanner_info": data.get("scanner_info"),
        "development_process": (
            data.get("development_process")
            or "C-41"
        ),
        "taken_at_location": (
            data.get("taken_at_location")
        ),
    }

    for key, value in metadata_fields.items():

        if value is not None:
            film_metadata[key] = value

    # --------------------------------------------------------
    # film_stock required for official submit
    # --------------------------------------------------------

    if (
        status == "submitted"
        and not film_metadata.get("film_stock")
    ):

        return jsonify({
            "message": "Missing required field",
            "missing_fields": [
                "film_stock"
            ],
        }), 400

    # --------------------------------------------------------
    # film_iso
    # --------------------------------------------------------

    film_iso = film_metadata.get("film_iso")

    if film_iso is not None:

        try:

            film_metadata["film_iso"] = int(
                film_iso
            )

        except (
            ValueError,
            TypeError,
        ):

            return jsonify({
                "message": (
                    "film_iso must be an integer"
                )
            }), 400

    # ========================================================
    # READ FILES + VALIDATE FILE TYPE
    # ========================================================

    files_list = []

    for file_obj in uploaded_files:

        # ----------------------------------------------------
        # Validate filename
        # ----------------------------------------------------

        filename = file_obj.filename or ""

        if not filename:
            return jsonify({
                "message": "Filename is required"
            }), 400

        # ----------------------------------------------------
        # Validate MIME type
        # ----------------------------------------------------

        content_type = (
            file_obj.content_type or ""
        ).lower()

        if content_type not in ALLOWED_IMAGE_TYPES:

            return jsonify({
                "message": "Invalid file type",
                "allowed_types": [
                    "image/jpeg",
                    "image/png",
                    "image/webp",
                ],
            }), 400

        # ----------------------------------------------------
        # Validate extension
        # ----------------------------------------------------

        extension = os.path.splitext(
            filename
        )[1].lower()

        if extension not in ALLOWED_IMAGE_EXTENSIONS:

            return jsonify({
                "message": "Invalid file extension",
                "allowed_extensions": [
                    ".jpg",
                    ".jpeg",
                    ".png",
                    ".webp",
                ],
            }), 400

        # ----------------------------------------------------
        # Read file
        # ----------------------------------------------------

        try:

            file_bytes = file_obj.read()

        except Exception as error:

            return jsonify({
                "message": (
                    f"Failed to read file "
                    f"{filename}"
                ),
                "error": str(error),
            }), 400

        # ----------------------------------------------------
        # Check empty file
        # ----------------------------------------------------

        if not file_bytes:

            return jsonify({
                "message": (
                    f"File content is empty "
                    f"for {filename}"
                ),
            }), 400

        # ----------------------------------------------------
        # Validate actual image
        # ----------------------------------------------------

        try:

            image = Image.open(
                io.BytesIO(file_bytes)
            )

            image.verify()

        except Exception:

            return jsonify({
                "message": (
                    f"Invalid image file "
                    f"for {filename}"
                ),
            }), 400

        # ----------------------------------------------------
        # Add validated file
        # ----------------------------------------------------

        files_list.append({
            "file_bytes": file_bytes,
            "filename": filename,
            "content_type": content_type,
        })

    # ========================================================
    # OTHER FIELDS
    # ========================================================

    description = (
        data.get("description")
        or data.get(
            "story_description",
            "",
        )
    )

    # ========================================================
    # CREATE SUBMISSION
    # ========================================================

    try:

        submission = (
            submission_service
            .create_submission(
                round_id=round_id,
                user_id=user_id,
                title=title or "",
                files=files_list,
                film_metadata=film_metadata,
                story_description=description,
                status=status,
            )
        )

        return jsonify({
            "message": (
                "Submission created successfully"
            ),
            "submission": {
                "id": submission.id,
                "round_id": submission.round_id,
                "user_id": submission.user_id,
                "title": submission.title,
                "story_description": (
                    submission.story_description
                ),
                "status": submission.status,
                "submitted_at": (
                    submission.submitted_at.isoformat()
                    if submission.submitted_at
                    else None
                ),
            },
        }), 201

    except ValueError as error:

        return jsonify({
            "message": str(error)
        }), 400

    except Exception as error:

        return jsonify({
            "message": (
                "Failed to create submission"
            ),
            "error": str(error),
        }), 500



# -------------------------------------------------------------------------
# Participant Portfolio & Submission Detail Routes
# -------------------------------------------------------------------------

@submission_bp.route("/my-submissions", methods=["GET"])
@submission_bp.route("/me", methods=["GET"])
@token_required
def get_my_submissions():
    """Retrieve all submissions belonging to the currently logged in participant."""
    user_id = request.user.get("user_id")
    if not user_id:
        return jsonify({"message": "User information is missing in token"}), 401

    submissions_list = submission_service.get_my_submissions(user_id=user_id)
    return jsonify({
        "message": "My submissions retrieved successfully",
        "submissions": submissions_list,
        "count": len(submissions_list),
    }), 200


@submission_bp.route("/my", methods=["GET"])
@submission_bp.route("/my-submissions-ui", methods=["GET"])
def my_submissions_ui():
    """Render the My Submissions / Portfolio page."""
    return render_template("my_submissions.html")


@submission_bp.route("/detail/<int:submission_id>", methods=["GET"])
@submission_bp.route("/<int:submission_id>/ui", methods=["GET"])
def submission_detail_ui(submission_id):
    """Render the Submission Details page."""
    return render_template("submission_detail.html", submission_id=submission_id)


# ============================================================
# UPDATE DRAFT SUBMISSION
# MULTIPART/FORM-DATA or JSON
# ============================================================

@submission_bp.route(
    "/<int:submission_id>",
    methods=["PUT", "PATCH"],
)
@token_required
def update_submission(submission_id):

    user_id = request.user.get("user_id")

    if not user_id:
        return jsonify({
            "message": (
                "User information is missing "
                "in token"
            )
        }), 401

    if request.is_json:
        data = request.get_json() or {}
    else:
        data = request.form

    # --------------------------------------------------------
    # Title
    # --------------------------------------------------------

    title = data.get("title")

    if title is not None:

        title = title.strip()

        if not title:

            return jsonify({
                "message": "title is required"
            }), 400

    description = (
        data.get("description")
        or data.get("story_description")
    )

    # ========================================================
    # FILES
    # ========================================================

    uploaded_files = []

    for key in request.files:

        file_objects = request.files.getlist(key)

        for file_obj in file_objects:

            if (
                file_obj
                and file_obj.filename
            ):
                uploaded_files.append(file_obj)

    files_list = []

    for file_obj in uploaded_files:

        # ----------------------------------------------------
        # Validate filename
        # ----------------------------------------------------

        filename = file_obj.filename or ""

        if not filename:
            return jsonify({
                "message": "Filename is required"
            }), 400

        # ----------------------------------------------------
        # Validate MIME type
        # ----------------------------------------------------

        content_type = (
            file_obj.content_type or ""
        ).lower()

        if content_type not in ALLOWED_IMAGE_TYPES:

            return jsonify({
                "message": "Invalid file type",
                "allowed_types": [
                    "image/jpeg",
                    "image/png",
                    "image/webp",
                ],
            }), 400

        # ----------------------------------------------------
        # Validate extension
        # ----------------------------------------------------

        extension = os.path.splitext(
            filename
        )[1].lower()

        if extension not in ALLOWED_IMAGE_EXTENSIONS:

            return jsonify({
                "message": "Invalid file extension",
                "allowed_extensions": [
                    ".jpg",
                    ".jpeg",
                    ".png",
                    ".webp",
                ],
            }), 400

        # ----------------------------------------------------
        # Read file
        # ----------------------------------------------------

        try:

            file_bytes = file_obj.read()

        except Exception as error:

            return jsonify({
                "message": (
                    f"Failed to read file "
                    f"{filename}"
                ),
                "error": str(error),
            }), 400

        # ----------------------------------------------------
        # Empty file
        # ----------------------------------------------------

        if not file_bytes:

            return jsonify({
                "message": (
                    f"File content is empty "
                    f"for {filename}"
                ),
            }), 400

        # ----------------------------------------------------
        # Validate actual image
        # ----------------------------------------------------

        try:

            image = Image.open(
                io.BytesIO(file_bytes)
            )

            image.verify()

        except Exception:

            return jsonify({
                "message": (
                    f"Invalid image file "
                    f"for {filename}"
                ),
            }), 400

        # ----------------------------------------------------
        # Add validated file
        # ----------------------------------------------------

        files_list.append({
            "file_bytes": file_bytes,
            "filename": filename,
            "content_type": content_type,
        })

    # ========================================================
    # FILM METADATA
    # ========================================================

    film_metadata = {}

    film_metadata_json = data.get(
        "film_metadata"
    )

    if film_metadata_json:

        try:

            import json

            parsed_metadata = (
                json.loads(
                    film_metadata_json
                )
                if isinstance(
                    film_metadata_json,
                    str,
                )
                else film_metadata_json
            )

            if isinstance(
                parsed_metadata,
                dict,
            ):
                film_metadata.update(
                    parsed_metadata
                )

        except (
            ValueError,
            TypeError,
        ):

            return jsonify({
                "message": (
                    "film_metadata must be valid JSON"
                )
            }), 400

    metadata_fields = {
        "film_stock": data.get("film_stock"),
        "film_iso": data.get("film_iso"),
        "camera_body": data.get("camera_body"),
        "lens": data.get("lens"),
        "lab_name": data.get("lab_name"),
        "scanner_info": data.get("scanner_info"),
        "development_process": (
            data.get("development_process")
        ),
        "taken_at_location": (
            data.get("taken_at_location")
        ),
    }

    for key, value in metadata_fields.items():

        if value is not None:
            film_metadata[key] = value

    # --------------------------------------------------------
    # film_iso
    # --------------------------------------------------------

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

            return jsonify({
                "message": (
                    "film_iso must be an integer"
                )
            }), 400

    # ========================================================
    # UPDATE
    # ========================================================

    try:

        updated_sub = (
            submission_service
            .update_draft(
                submission_id=submission_id,
                user_id=user_id,
                title=title,
                story_description=description,
                files=(
                    files_list
                    if files_list
                    else None
                ),
                film_metadata=(
                    film_metadata
                    if film_metadata
                    else None
                ),
            )
        )

        return jsonify({
            "message": (
                "Submission draft updated successfully"
            ),
            "submission": {
                "id": updated_sub.id,
                "round_id": updated_sub.round_id,
                "user_id": updated_sub.user_id,
                "title": updated_sub.title,
                "story_description": (
                    updated_sub.story_description
                ),
                "status": updated_sub.status,
            },
        }), 200

    except PermissionError as error:

        return jsonify({
            "message": str(error)
        }), 403

    except ValueError as error:

        err_msg = str(error)

        if "not found" in err_msg.lower():

            return jsonify({
                "message": err_msg
            }), 404

        return jsonify({
            "message": err_msg
        }), 400

    except Exception as error:

        return jsonify({
            "message": (
                "Failed to update submission draft"
            ),
            "error": str(error),
        }), 500


# ============================================================
# OFFICIAL SUBMIT DRAFT
# ============================================================

@submission_bp.route(
    "/<int:submission_id>/submit",
    methods=["POST"],
)
@token_required
def submit_submission(submission_id):

    user_id = request.user.get("user_id")

    if not user_id:
        return jsonify({
            "message": (
                "User information is missing "
                "in token"
            )
        }), 401

    try:

        submitted_sub = (
            submission_service
            .submit_draft(
                submission_id=submission_id,
                user_id=user_id,
            )
        )

        return jsonify({
            "message": (
                "Submission submitted successfully"
            ),
            "submission": {
                "id": submitted_sub.id,
                "status": submitted_sub.status,
            },
        }), 200

    except PermissionError as error:

        return jsonify({
            "message": str(error)
        }), 403

    except ValueError as error:

        err_msg = str(error)

        if "not found" in err_msg.lower():

            return jsonify({
                "message": err_msg
            }), 404

        return jsonify({
            "message": err_msg
        }), 400

    except Exception as error:

        return jsonify({
            "message": (
                "Failed to submit submission"
            ),
            "error": str(error),
        }), 500


# ============================================================
# GET SUBMISSION DETAIL
# ============================================================


@submission_bp.route(
    "/<int:submission_id>",
    methods=["GET"],
)

@token_required
def get_submission(
    submission_id,
):
    """
    Retrieve submission details.
    Accessible by: Owner participant, judges, organizers, and admins.
    """
    user_id = request.user.get("user_id")
    user_role = request.user.get("role", "participant")

    try:
        # First try rich details
        detail = submission_service.get_submission_detail(
            submission_id=submission_id,
            user_id=user_id,
            role=user_role,
        )
    except PermissionError as pe:
        return jsonify({"message": str(pe)}), 403

    if not detail:
        # Fallback to basic get_submission_by_id if full details not found or mocked
        result = submission_service.get_submission_by_id(submission_id)
        if not result:
            return jsonify({"message": "Submission not found"}), 404

        submission, submission_file, film_metadata = result

        # Check access permission
        if user_role == "participant" and submission.user_id != user_id:
            return jsonify({"message": "Access forbidden: You can only view your own submission details."}), 403

        # Check / save AI flag
        ai_flag_data = None
        try:
            image_path = submission_file.image_hd_url if submission_file else None
            if image_path:
                existing_flag = submission_repo.get_ai_flag(submission_id)
                if existing_flag:
                    ai_flag_data = {
                        "ai_score": float(existing_flag.confidence_score),
                        "risk_level": existing_flag.risk_level,
                        "status": existing_flag.status,
                    }
                else:
                    ai_result = ai_detection_service.detect_ai(image_path)
                    ai_score = ai_result.get("ai_score", 0)
                    ai_message = ai_result.get("ai_message", "")
                    risk_level = ai_result.get("risk_level", "safe")

                    saved_flag = submission_repo.save_ai_flag(
                        submission_id=submission_id,
                        confidence_score=ai_score,
                        risk_level=risk_level,
                        flag_type="AI_METADATA",
                        status="pending",
                    )
                    ai_flag_data = {
                        "ai_score": float(saved_flag.confidence_score),
                        "ai_message": ai_message,
                        "risk_level": saved_flag.risk_level,
                        "status": saved_flag.status,
                    }
        except Exception:
            ai_flag_data = None

        response = {
            "id": submission.id,
            "round_id": submission.round_id,
            "user_id": submission.user_id,
            "title": submission.title,
            "story_description": submission.story_description,
            "status": submission.status,
            "final_score": float(submission.final_score) if submission.final_score is not None else None,
            "submitted_at": submission.submitted_at.isoformat() if submission.submitted_at else None,
            "created_at": submission.created_at.isoformat() if submission.created_at else None,
            "updated_at": submission.updated_at.isoformat() if submission.updated_at else None,
            "file": {
                "id": submission_file.id,
                "image_hd_url": submission_file.image_hd_url,
                "thumbnail_url": submission_file.thumbnail_url or submission_file.image_hd_url,
                "width_px": submission_file.width_px,
                "height_px": submission_file.height_px,
                "file_size_bytes": submission_file.file_size_bytes,
                "file_hash": submission_file.file_hash,
                "created_at": submission_file.created_at.isoformat() if submission_file.created_at else None,
            } if submission_file else None,
            "film_metadata": {
                "film_stock": film_metadata.film_stock,
                "film_iso": film_metadata.film_iso,
                "camera_body": film_metadata.camera_body,
                "lens": film_metadata.lens,
                "lab_name": film_metadata.lab_name,
                "scanner_info": film_metadata.scanner_info,
                "development_process": film_metadata.development_process,
                "taken_at_location": film_metadata.taken_at_location,
                "created_at": film_metadata.created_at.isoformat() if film_metadata.created_at else None,
            } if film_metadata else None,
            "ai_flag": ai_flag_data,
        }
        return jsonify(response), 200

    return jsonify(detail), 200


@submission_bp.route(
    "/<int:submission_id>",
    methods=["PUT", "PATCH"],
)
@token_required
def update_submission(submission_id):
    """
    Update a draft submission.
    Allows editing title, story description, film metadata, competition round,
    and optionally uploading a replacement image file.
    """
    user_id = request.user.get("user_id")
    if not user_id:
        return jsonify({"message": "User information is missing in token"}), 401

    image_file = request.files.get("file") if request.files else None
    data = request.form if request.form else (request.get_json(silent=True) or {})

    # Extract film metadata fields
    film_metadata = {}
    if "film_metadata" in data and isinstance(data["film_metadata"], dict):
        film_metadata = data["film_metadata"]
    else:
        for field in [
            "film_stock",
            "film_iso",
            "camera_body",
            "lens",
            "lab_name",
            "scanner_info",
            "development_process",
            "taken_at_location",
        ]:
            if field in data and data[field] is not None:
                film_metadata[field] = data[field]

    try:
        file_bytes = image_file.read() if image_file else None
        filename = image_file.filename if image_file else None
        content_type = image_file.content_type if image_file else "image/jpeg"

        updated = submission_service.update_draft_submission(
            submission_id=submission_id,
            user_id=user_id,
            title=data.get("title"),
            story_description=data.get("story_description"),
            round_id=int(data["round_id"]) if data.get("round_id") else None,
            status=data.get("status"),
            film_metadata=film_metadata if film_metadata else None,
            file_bytes=file_bytes,
            filename=filename,
            content_type=content_type,
            image_hd_url=data.get("image_hd_url"),
            file_hash=data.get("file_hash"),
            thumbnail_url=data.get("thumbnail_url"),
            width_px=data.get("width_px"),
            height_px=data.get("height_px"),
            file_size_bytes=data.get("file_size_bytes"),
        )

        return jsonify({
            "message": "Submission updated successfully",
            "submission": {
                "id": updated.id,
                "title": updated.title,
                "status": updated.status,
                "round_id": updated.round_id,
                "story_description": updated.story_description,
                "submitted_at": (
                    updated.submitted_at.isoformat()
                    if updated.submitted_at
                    else None
                ),
                "updated_at": (
                    updated.updated_at.isoformat()
                    if updated.updated_at
                    else None
                ),
            },
        }), 200

    except Exception as e:
        return jsonify({
            "error": str(e)
        }), 500

@role_required(
    "organizer",
    "judge",
)
def get_submission(submission_id):

    try:

        result = (
            submission_service
            .get_submission_by_id(
                submission_id
            )
        )

    except Exception as error:

        return jsonify({
            "message": "Failed to get submission",
            "error": str(error),
        }), 500

    # --------------------------------------------------------
    # Not found
    # --------------------------------------------------------

    if not result:

        return jsonify({
            "message": "Submission not found"
        }), 404

    try:

        (
            submission,
            submission_file,
            film_metadata,
        ) = result

        # ====================================================
        # BASIC SUBMISSION DATA
        # ====================================================

        response = {
            "id": submission.id,
            "round_id": submission.round_id,
            "user_id": submission.user_id,
            "title": submission.title,
            "story_description": (
                submission.story_description
            ),
            "status": submission.status,
            "final_score": (
                float(
                    submission.final_score
                )
                if submission.final_score is not None
                else None
            ),
            "submitted_at": (
                submission.submitted_at.isoformat()
                if submission.submitted_at
                else None
            ),
            "created_at": (
                submission.created_at.isoformat()
                if submission.created_at
                else None
            ),
            "updated_at": (
                submission.updated_at.isoformat()
                if submission.updated_at
                else None
            ),
        }

        # ====================================================
        # FILE
        # ====================================================

        if submission_file:

            response["file"] = {
                "id": submission_file.id,
                "image_hd_url": (
                    submission_file.image_hd_url
                ),
                "thumbnail_url": (
                    submission_file.thumbnail_url
                ),
                "width_px": (
                    submission_file.width_px
                ),
                "height_px": (
                    submission_file.height_px
                ),
                "file_size_bytes": (
                    submission_file.file_size_bytes
                ),
                "file_hash": (
                    submission_file.file_hash
                ),
                "created_at": (
                    submission_file.created_at.isoformat()
                    if submission_file.created_at
                    else None
                ),
            }

        else:

            response["file"] = None

        # ====================================================
        # FILM METADATA
        # ====================================================

        if film_metadata:

            response["film_metadata"] = {
                "film_stock": (
                    film_metadata.film_stock
                ),
                "film_iso": (
                    film_metadata.film_iso
                ),
                "camera_body": (
                    film_metadata.camera_body
                ),
                "lens": (
                    film_metadata.lens
                ),
                "lab_name": (
                    film_metadata.lab_name
                ),
                "scanner_info": (
                    film_metadata.scanner_info
                ),
                "development_process": (
                    film_metadata.development_process
                ),
                "taken_at_location": (
                    film_metadata.taken_at_location
                ),
                "created_at": (
                    film_metadata.created_at.isoformat()
                    if film_metadata.created_at
                    else None
                ),
            }

        else:

            response["film_metadata"] = None

    except Exception as error:

        return jsonify({
            "message": (
                "Failed to serialize "
                "submission details"
            ),
            "error": str(error),
        }), 500

    # ========================================================
    # AI FLAG
    #
    # AI IS OPTIONAL.
    # AI FAILURE MUST NOT BREAK
    # SUBMISSION DETAIL API.
    # ========================================================

    ai_flag_data = None

    try:

        existing_flag = (
            submission_repo
            .get_ai_flag(
                submission_id
            )
        )

        if existing_flag:

            ai_flag_data = {
                "ai_score": float(
                    existing_flag.confidence_score
                ),
                "risk_level": (
                    existing_flag.risk_level
                ),
                "status": (
                    existing_flag.status
                ),
            }

    except Exception:

        # AI failure is ignored.
        # Submission detail must still work.

        ai_flag_data = None

    except PermissionError as pe:
        return jsonify({"message": str(pe)}), 403
    except ValueError as ve:
        return jsonify({"message": str(ve)}), 400
    except Exception as e:
        return jsonify({"message": f"Failed to update submission: {str(e)}"}), 500


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

        return jsonify({
            "message": (
                "criteria_id is required"
            )
        }), 400

    if score_value is None:

        return jsonify({
            "message": (
                "score_value is required"
            )
        }), 400

    if not judge_id:

        return jsonify({
            "message": (
                "Judge information is missing"
            )
        }), 401

    model, error = (
        score_service
        .submit_score(
            submission_id=submission_id,
            judge_id=judge_id,
            criteria_id=criteria_id,
            score_value=score_value,
            comment=comment,
        )
    )

    if error == "submission_not_found":

        return jsonify({
            "message": "Submission not found"
        }), 404

    if error == "criteria_not_found":

        return jsonify({
            "message": "Criteria not found"
        }), 404

    if error == "invalid_score":

        return jsonify({
            "message": "Invalid score value"
        }), 400

    return jsonify({
        "message": "Score saved successfully",
        "score": {
            "id": model.id,
            "submission_id": (
                model.submission_id
            ),
            "judge_id": model.judge_id,
            "criteria_id": (
                model.criteria_id
            ),
            "score_value": float(
                model.score_value
            ),
            "comment": model.comment,
        },
    }), 200


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

        return jsonify({
            "message": (
                "Judge information is missing"
            )
        }), 401

    if not summary_feedback:

        return jsonify({
            "message": (
                "summary_feedback is required"
            )
        }), 400

    model, error = (
        score_service
        .submit_feedback(
            submission_id=submission_id,
            judge_id=judge_id,
            summary_feedback=summary_feedback,
            final_recommendation=final_recommendation,
        )
    )

    if error == "submission_not_found":

        return jsonify({
            "message": "Submission not found"
        }), 404

    return jsonify({
        "message": (
            "Feedback saved successfully"
        ),
        "feedback": {
            "id": model.id,
            "submission_id": (
                model.submission_id
            ),
            "judge_id": model.judge_id,
            "summary_feedback": (
                model.summary_feedback
            ),
            "final_recommendation": (
                model.final_recommendation
            ),
        },
    }), 200


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
        score_service
        .get_next_previous(
            submission_id
        )
    )

    if error == "submission_not_found":

        return jsonify({
            "message": "Submission not found"
        }), 404

    if error == "db_error":

        return jsonify({
            "message": "Database error"
        }), 500

    if result is None or result.get("next") is None:

        return jsonify({
            "message": "No next submission"
        }), 404

    return jsonify(result), 200


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
        score_service
        .get_previous_submission(
            submission_id
        )
    )

    if error == "submission_not_found":

        return jsonify({
            "message": "Submission not found"
        }), 404

    if error == "db_error":

        return jsonify({
            "message": "Database error"
        }), 500

    if result is None:

        return jsonify({
            "message": "No previous submission"
        }), 404

    return jsonify({
        "submission": result
    }), 200


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

        return jsonify([
            {
                "id": item.id,
                "round_id": item.round_id,
                "user_id": item.user_id,
                "title": item.title,
                "story_description": (
                    item.story_description
                ),
                "status": item.status,
                "final_score": (
                    float(item.final_score)
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
        ]), 200

    except Exception as error:

        return jsonify({
            "message": (
                "Failed to list submissions"
            ),
            "error": str(error),
        }), 500


# ============================================================
# LIST SUBMISSIONS BY ROLE
# ============================================================

@submission_bp.route(
    "/my",
    methods=["GET"],
)
@token_required
def get_my_submissions():

    user_id = request.user.get("user_id")

    if not user_id:
        return jsonify({
            "message": "User information is missing in token"
        }), 401

    round_id_param = request.args.get("round_id")
    round_id = None

    if round_id_param is not None:
        try:
            round_id = int(round_id_param)
        except (ValueError, TypeError):
            return jsonify({
                "message": "Invalid round_id"
            }), 400

    status = request.args.get("status")

    if status and status not in [
        "draft",
        "submitted",
        "flagged",
        "evaluated",
    ]:
        return jsonify({
            "message": "Invalid status"
        }), 400

    ai_flag = request.args.get("ai_flag")

    if ai_flag and ai_flag not in [
        "safe",
        "medium",
        "high",
    ]:
        return jsonify({
            "message": "Invalid ai_flag"
        }), 400

    try:
        data = submission_service.get_my_submissions(
            user_id=user_id,
            round_id=round_id,
            status=status,
            ai_flag=ai_flag,
        )
        return jsonify(data), 200

    except Exception as error:
        return jsonify({
            "message": "Failed to get my submissions",
            "error": str(error),
        }), 500


@role_required("organizer", "admin")
def get_organizer_contest_submissions(contest_id):

    user_id = request.user.get("user_id")
    user_role = request.user.get("role")

    if not user_id:
        return jsonify({
            "message": "User information is missing in token"
        }), 401

    round_id_param = request.args.get("round_id")
    round_id = None

    if round_id_param is not None:
        try:
            round_id = int(round_id_param)
        except (ValueError, TypeError):
            return jsonify({
                "message": "Invalid round_id"
            }), 400

    status = request.args.get("status")

    if status and status not in [
        "draft",
        "submitted",
        "flagged",
        "evaluated",
    ]:
        return jsonify({
            "message": "Invalid status"
        }), 400

    ai_flag = request.args.get("ai_flag")

    if ai_flag and ai_flag not in [
        "safe",
        "medium",
        "high",
    ]:
        return jsonify({
            "message": "Invalid ai_flag"
        }), 400

    try:
        data = submission_service.get_organizer_submissions(
            contest_id=contest_id,
            user_id=user_id,
            user_role=user_role,
            round_id=round_id,
            status=status,
            ai_flag=ai_flag,
        )
        return jsonify(data), 200

    except ValueError as error:
        return jsonify({
            "message": str(error)
        }), 404

    except PermissionError as error:
        return jsonify({
            "message": str(error)
        }), 403

    except Exception as error:
        return jsonify({
            "message": "Failed to get organizer contest submissions",
            "error": str(error),
        }), 500


@role_required("judge", "admin")
def get_judge_assignment_submissions(assignment_id):

    user_id = request.user.get("user_id")
    user_role = request.user.get("role")

    if not user_id:
        return jsonify({
            "message": "User information is missing in token"
        }), 401

    round_id_param = request.args.get("round_id")
    round_id = None

    if round_id_param is not None:
        try:
            round_id = int(round_id_param)
        except (ValueError, TypeError):
            return jsonify({
                "message": "Invalid round_id"
            }), 400

    status = request.args.get("status")

    if status and status not in [
        "draft",
        "submitted",
        "flagged",
        "evaluated",
    ]:
        return jsonify({
            "message": "Invalid status"
        }), 400

    ai_flag = request.args.get("ai_flag")

    if ai_flag and ai_flag not in [
        "safe",
        "medium",
        "high",
    ]:
        return jsonify({
            "message": "Invalid ai_flag"
        }), 400

    try:
        data = submission_service.get_judge_assignment_submissions(
            assignment_id=assignment_id,
            user_id=user_id,
            user_role=user_role,
            round_id=round_id,
            status=status,
            ai_flag=ai_flag,
        )
        return jsonify(data), 200

    except ValueError as error:
        return jsonify({
            "message": str(error)
        }), 404

    except PermissionError as error:
        return jsonify({
            "message": str(error)
        }), 403

    except Exception as error:
        return jsonify({
            "message": "Failed to get judge assignment submissions",
            "error": str(error),
        }), 500

        