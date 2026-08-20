from flask import (
    Blueprint,
    jsonify,
    request,
)

import io
import os
import json

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
# HELPERS
# ============================================================

def _get_user_id():
    return request.user.get("user_id")


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
            if getattr(submission, "final_score", None) is not None
            else None
        ),
        "submitted_at": (
            submission.submitted_at.isoformat()
            if getattr(submission, "submitted_at", None)
            else None
        ),
        "created_at": (
            submission.created_at.isoformat()
            if getattr(submission, "created_at", None)
            else None
        ),
        "updated_at": (
            submission.updated_at.isoformat()
            if getattr(submission, "updated_at", None)
            else None
        ),
    }


def _validate_image_file(file_obj):
    """
    Validate uploaded image and return:

        file_bytes,
        filename,
        content_type

    or raise ValueError.
    """

    if not file_obj:
        raise ValueError("No image file provided")

    filename = file_obj.filename or ""

    if not filename:
        raise ValueError("Filename is required")

    content_type = (
        file_obj.content_type or ""
    ).lower()

    if content_type not in ALLOWED_IMAGE_TYPES:
        raise ValueError(
            "Invalid file type"
        )

    extension = os.path.splitext(
        filename
    )[1].lower()

    if extension not in ALLOWED_IMAGE_EXTENSIONS:
        raise ValueError(
            "Invalid file extension"
        )

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


def _collect_uploaded_files():
    """
    Collect all uploaded files from multipart/form-data.
    """

    uploaded_files = []

    for key in request.files:
        file_objects = request.files.getlist(key)

        for file_obj in file_objects:
            if (
                file_obj
                and file_obj.filename
            ):
                uploaded_files.append(file_obj)

    return uploaded_files


def _parse_film_metadata(data):
    """
    Parse film_metadata from JSON + individual fields.
    """

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

    try:

        (
            file_bytes,
            filename,
            content_type,
        ) = _validate_image_file(
            image_file
        )

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
# ============================================================

@submission_bp.route(
    "",
    methods=["POST"],
)
@token_required
def create_submission():

    user_id = _get_user_id()

    if not user_id:
        return jsonify({
            "message": (
                "User information is missing "
                "in token"
            )
        }), 401

    data = request.form

    round_id = data.get("round_id")
    title = data.get("title")

    if not round_id:
        return jsonify({
            "message": "round_id is required"
        }), 400

    try:
        round_id = int(round_id)
    except (
        ValueError,
        TypeError,
    ):
        return jsonify({
            "message": "round_id must be an integer"
        }), 400

    status = data.get(
        "status",
        "draft",
    )

    allowed_statuses = [
        "draft",
        "submitted",
        "flagged",
        "evaluated",
    ]

    if status not in allowed_statuses:
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

    if status == "submitted":

        if not title or not title.strip():
            return jsonify({
                "message": "title is required"
            }), 400

        title = title.strip()

    elif title:
        title = title.strip()

    # --------------------------------------------------------
    # FILES
    # --------------------------------------------------------

    uploaded_files = _collect_uploaded_files()

    if (
        status == "submitted"
        and not uploaded_files
    ):
        return jsonify({
            "message": "No image file provided"
        }), 400

    files_list = []

    for file_obj in uploaded_files:

        try:

            (
                file_bytes,
                filename,
                content_type,
            ) = _validate_image_file(
                file_obj
            )

            files_list.append({
                "file_bytes": file_bytes,
                "filename": filename,
                "content_type": content_type,
            })

        except ValueError as error:

            return jsonify({
                "message": str(error)
            }), 400

    # --------------------------------------------------------
    # FILM METADATA
    # --------------------------------------------------------

    try:

        film_metadata = _parse_film_metadata(
            data
        )

    except ValueError as error:

        return jsonify({
            "message": str(error)
        }), 400

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

    if (
        "development_process"
        not in film_metadata
    ):
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
            "submission": _serialize_submission(
                submission
            ),
        }), 201

    except ValueError as error:

        return jsonify({
            "message": str(error)
        }), 400

    except PermissionError as error:

        return jsonify({
            "message": str(error)
        }), 403

    except Exception as error:

        return jsonify({
            "message": (
                "Failed to create submission"
            ),
            "error": str(error),
        }), 500


# ============================================================
# UPDATE DRAFT SUBMISSION
# ============================================================

@submission_bp.route(
    "/<int:submission_id>",
    methods=["PUT", "PATCH"],
)
@token_required
def update_submission(submission_id):

    user_id = _get_user_id()

    if not user_id:
        return jsonify({
            "message": (
                "User information is missing "
                "in token"
            )
        }), 401

    # --------------------------------------------------------
    # REQUEST DATA
    # --------------------------------------------------------

    if request.is_json:
        data = request.get_json(
            silent=True
        ) or {}
    else:
        data = request.form

    # --------------------------------------------------------
    # TITLE
    # --------------------------------------------------------

    title = data.get("title")

    if title is not None:

        title = title.strip()

        if not title:
            return jsonify({
                "message": "title is required"
            }), 400

    # --------------------------------------------------------
    # DESCRIPTION
    # --------------------------------------------------------

    if data.get("description") is not None:

        description = data.get(
            "description"
        )

    else:

        description = data.get(
            "story_description"
        )

    # --------------------------------------------------------
    # FILES
    # --------------------------------------------------------

    files_list = []

    uploaded_files = _collect_uploaded_files()

    for file_obj in uploaded_files:

        try:

            (
                file_bytes,
                filename,
                content_type,
            ) = _validate_image_file(
                file_obj
            )

            files_list.append({
                "file_bytes": file_bytes,
                "filename": filename,
                "content_type": content_type,
            })

        except ValueError as error:

            return jsonify({
                "message": str(error)
            }), 400

    # --------------------------------------------------------
    # FILM METADATA
    # --------------------------------------------------------

    try:

        film_metadata = _parse_film_metadata(
            data
        )

    except ValueError as error:

        return jsonify({
            "message": str(error)
        }), 400

    # --------------------------------------------------------
    # UPDATE
    #
    # IMPORTANT:
    #
    # Use update_draft(), not update_draft_submission().
    #
    # This matches the current SubmissionService /
    # SubmissionRepository flow and the unit test:
    #
    # mock_repo.update_draft.return_value = ...
    #
    # --------------------------------------------------------

    try:
        if request.is_json:
            updated_sub = submission_service.update_draft_submission(
                submission_id=submission_id,
                user_id=user_id,
                title=title,
                story_description=description,
                round_id=data.get("round_id"),
                status=data.get("status"),
                film_metadata=film_metadata or None,
            )
            return jsonify({
                "message": "Submission updated successfully",
                "submission": {
                    "id": updated_sub.id,
                    "title": updated_sub.title,
                    "status": updated_sub.status,
                    "round_id": updated_sub.round_id,
                    "story_description": getattr(updated_sub, "story_description", None),
                    "submitted_at": (
                        updated_sub.submitted_at.isoformat()
                        if getattr(updated_sub, "submitted_at", None)
                        else None
                    ),
                    "updated_at": (
                        updated_sub.updated_at.isoformat()
                        if getattr(updated_sub, "updated_at", None)
                        else None
                    ),
                },
            }), 200

        updated_sub = (
            submission_service
            .update_draft(
                submission_id=submission_id,
                user_id=user_id,
                title=title,
                story_description=description,
                files=files_list,
                film_metadata=(
                    film_metadata
                    if film_metadata
                    else None
                ),
            )
        )

        if updated_sub is None:
            return jsonify({
                "message": "Submission not found"
            }), 404

        return jsonify({
            "message": (
                "Submission draft updated successfully"
            ),
            "submission": _serialize_submission(
                updated_sub
            ),
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

    user_id = _get_user_id()

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
@role_required(
    "organizer",
    "judge",
    "participant",
)
def get_submission(submission_id):

    try:
        detail = submission_service.get_submission_detail(
            submission_id=submission_id,
            user_id=request.user.get("user_id"),
            role=request.user.get("role", "participant"),
        )
        if detail:
            return jsonify(detail), 200
    except PermissionError as error:
        return jsonify({"message": str(error)}), 403
    except (AttributeError, TypeError):
        pass

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

        # ----------------------------------------------------
        # PARTICIPANT OWNERSHIP
        # ----------------------------------------------------

        if request.user.get("role") == "participant":

            if (
                submission.user_id
                != request.user.get("user_id")
            ):

                return jsonify({
                    "message": (
                        "You are not allowed "
                        "to view this submission"
                    )
                }), 403

        # ----------------------------------------------------
        # BASIC DATA
        # ----------------------------------------------------

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
                float(submission.final_score)
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

        # ----------------------------------------------------
        # FILE
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # FILM METADATA
        # ----------------------------------------------------

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

    # --------------------------------------------------------
    # AI FLAG
    # --------------------------------------------------------

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

        ai_flag_data = None

    response["ai_flag"] = ai_flag_data

    return jsonify(response), 200


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

        return jsonify({
            "message": (
                "Judge is not assigned "
                "to this submission"
            )
        }), 403

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

        return jsonify({
            "message": (
                "Judge is not assigned "
                "to this submission"
            )
        }), 403

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
# CALCULATE SUBMISSION SCORE
# ============================================================

@submission_bp.route(
    "/<int:submission_id>/calculate-score",
    methods=["POST"],
)
@token_required
def calculate_submission_score(submission_id):

    user_role = request.user.get("role")

    if user_role not in [
        "organizer",
        "admin",
        "judge",
    ]:

        return jsonify({
            "message": "Forbidden access"
        }), 403

    submission, error = (
        score_service
        .calculate_submission_score(
            submission_id
        )
    )

    if error == "submission_not_found":

        return jsonify({
            "message": "Submission not found"
        }), 404

    return jsonify({
        "message": (
            "Submission score calculated successfully"
        ),
        "submission": {
            "id": submission.id,
            "final_score": (
                float(submission.final_score)
                if submission.final_score is not None
                else None
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

    if (
        result is None
        or result.get("next") is None
    ):

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
# LIST MY SUBMISSIONS
# ============================================================

@submission_bp.route(
    "/my-submissions",
    methods=["GET"],
)
@submission_bp.route(
    "/my",
    methods=["GET"],
)
@token_required
def get_my_submissions():

    user_id = _get_user_id()

    if not user_id:

        return jsonify({
            "message": (
                "User information is missing "
                "in token"
            )
        }), 401

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

            return jsonify({
                "message": "Invalid round_id"
            }), 400

    status = request.args.get(
        "status"
    )

    allowed_statuses = [
        "draft",
        "submitted",
        "flagged",
        "evaluated",
    ]

    if (
        status
        and status not in allowed_statuses
    ):

        return jsonify({
            "message": "Invalid status"
        }), 400

    ai_flag = request.args.get(
        "ai_flag"
    )

    if ai_flag and ai_flag not in [
        "safe",
        "medium",
        "high",
    ]:

        return jsonify({
            "message": "Invalid ai_flag"
        }), 400

    try:

        data = (
            submission_service
            .get_my_submissions(
                user_id=user_id,
                round_id=round_id,
                status=status,
                ai_flag=ai_flag,
            )
        )

        if isinstance(data, dict):

            response_data = {
                "message": (
                    "My submissions "
                    "retrieved successfully"
                ),
                **data,
            }

        else:

            response_data = {
                "message": (
                    "My submissions "
                    "retrieved successfully"
                ),
                "submissions": data,
            }

        return jsonify(
            response_data
        ), 200

    except Exception as error:

        return jsonify({
            "message": (
                "Failed to get my submissions"
            ),
            "error": str(error),
        }), 500


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
    contest_id
):

    user_id = _get_user_id()
    user_role = request.user.get(
        "role"
    )

    if not user_id:

        return jsonify({
            "message": (
                "User information is missing "
                "in token"
            )
        }), 401

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

            return jsonify({
                "message": "Invalid round_id"
            }), 400

    status = request.args.get(
        "status"
    )

    if status and status not in [
        "draft",
        "submitted",
        "flagged",
        "evaluated",
    ]:

        return jsonify({
            "message": "Invalid status"
        }), 400

    ai_flag = request.args.get(
        "ai_flag"
    )

    if ai_flag and ai_flag not in [
        "safe",
        "medium",
        "high",
    ]:

        return jsonify({
            "message": "Invalid ai_flag"
        }), 400

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
            "message": (
                "Failed to get organizer "
                "contest submissions"
            ),
            "error": str(error),
        }), 500


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
    assignment_id
):

    user_id = _get_user_id()
    user_role = request.user.get(
        "role"
    )

    if not user_id:

        return jsonify({
            "message": (
                "User information is missing "
                "in token"
            )
        }), 401

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

            return jsonify({
                "message": "Invalid round_id"
            }), 400

    status = request.args.get(
        "status"
    )

    if status and status not in [
        "draft",
        "submitted",
        "flagged",
        "evaluated",
    ]:

        return jsonify({
            "message": "Invalid status"
        }), 400

    ai_flag = request.args.get(
        "ai_flag"
    )

    if ai_flag and ai_flag not in [
        "safe",
        "medium",
        "high",
    ]:

        return jsonify({
            "message": "Invalid ai_flag"
        }), 400

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
            "message": (
                "Failed to get judge "
                "assignment submissions"
            ),
            "error": str(error),
        }), 500