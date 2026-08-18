from flask import (
    Blueprint,
    jsonify,
    request,
)

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
from services.ai_detection_service import AiDetectionService


submission_bp = Blueprint(
    "submission",
    __name__,
    url_prefix="/submissions",
)


# ============================================================
# SERVICES
# ============================================================

submission_repo = SubmissionRepository()

submission_service = SubmissionService(
    submission_repo=submission_repo,
)

ai_detection_service = AiDetectionService()

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

    try:

        file_bytes = image_file.read()

        if not file_bytes:
            return jsonify({
                "message": "File content is empty"
            }), 400

        storage_info = (
            submission_service
            .upload_submission_image(
                file_bytes=file_bytes,
                filename=image_file.filename,
                content_type=(
                    image_file.content_type
                    or "image/jpeg"
                ),
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
    # Validate title
    # --------------------------------------------------------

    if not title:
        return jsonify({
            "message": "title is required"
        }), 400

    # ========================================================
    # GET FILES
    # Supports:
    #
    # file
    # file1
    # file2
    # file3
    # ...
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
    # At least one image
    # --------------------------------------------------------

    if not uploaded_files:

        return jsonify({
            "message": "No image file provided"
        }), 400

    # ========================================================
    # FILM METADATA
    # ========================================================

    film_metadata = {}

    # --------------------------------------------------------
    # Optional JSON metadata
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
    # film_stock required
    # --------------------------------------------------------

    if not film_metadata.get("film_stock"):

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
    # READ FILES
    # ========================================================

    files_list = []

    for file_obj in uploaded_files:

        try:

            file_bytes = file_obj.read()

        except Exception as error:

            return jsonify({
                "message": (
                    f"Failed to read file "
                    f"{file_obj.filename}"
                ),
                "error": str(error),
            }), 400

        if not file_bytes:

            return jsonify({
                "message": (
                    f"File content is empty "
                    f"for {file_obj.filename}"
                ),
            }), 400

        files_list.append({
            "file_bytes": file_bytes,
            "filename": file_obj.filename,
            "content_type": (
                file_obj.content_type
                or "image/jpeg"
            ),
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

    status = data.get(
        "status",
        "submitted",
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
                title=title,
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
)
def get_submission(submission_id):

    # ========================================================
    # GET SUBMISSION
    # ========================================================

    try:

      result = (
    submission_repo
    .get_by_id_with_details(
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
                "Failed to serialize submission details"
            ),
            "error": str(error),
        }), 500

        # ========================================================
    # AI FLAG
    #
    # AI is OPTIONAL.
    # AI failure MUST NOT affect
    # submission detail response.
    # ========================================================

    ai_flag_data = None

    try:
        existing_flag = (
            submission_repo.get_ai_flag(
                submission_id
            )
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
        # AI information is optional.
        # Failure must not break submission detail API.
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
        score_service.submit_feedback(
            submission_id=submission_id,
            judge_id=judge_id,
            summary_feedback=(
                summary_feedback
            ),
            final_recommendation=(
                final_recommendation
            ),
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
        .get_next_submission(
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
            "message": "No next submission"
        }), 404

    return jsonify({
        "submission": result
    }), 200


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
            "message": "Failed to list submissions",
            "error": str(error),
        }), 500
