from flask import Blueprint, jsonify, request

from api.role_required import token_required, role_required
from services.score_service import ScoreService


score_bp = Blueprint(
    "score",
    __name__,
    url_prefix="/scores",
)


score_service = ScoreService()


@score_bp.route(
    "/submissions/<int:submission_id>",
    methods=["POST"],
)
@role_required("judge")
def submit_score(submission_id):

    data = request.get_json(silent=True) or {}

    judge_id = request.user.get("user_id")

    if not judge_id:
        return jsonify({
            "message": "Judge information is missing"
        }), 401

    criteria_id = data.get("criteria_id")
    score_value = data.get("score_value")
    comment = data.get("comment")

    if criteria_id is None:
        return jsonify({
            "message": "criteria_id is required"
        }), 400

    if score_value is None:
        return jsonify({
            "message": "score_value is required"
        }), 400

    try:
        criteria_id = int(criteria_id)
    except (ValueError, TypeError):
        return jsonify({
            "message": "criteria_id must be an integer"
        }), 400

    user_role = request.user.get("role", "judge")

    try:
        assigned = score_service.is_judge_assigned(
            submission_id=submission_id,
            judge_id=judge_id,
            user_role=user_role,
        )
    except Exception:
        assigned = False

    if not assigned:
        return jsonify({
            "message": "Judge is not assigned to this submission"
        }), 403

    try:
        model, error = score_service.submit_score(
            submission_id=submission_id,
            judge_id=judge_id,
            criteria_id=criteria_id,
            score_value=score_value,
            comment=comment,
        )
    except Exception as error:
        return jsonify({
            "message": "Failed to save score",
            "error": str(error),
        }), 500

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

    if error == "feedback_finalized":
        return jsonify({
            "message": "This review has already been finalized and can no longer be edited"
        }), 409

    if error == "round_finalized":
        return jsonify({
            "message": "This round has already been finalized and scores are locked"
        }), 409

    if model is None:
        return jsonify({
            "message": "Failed to save score"
        }), 500

    return jsonify({
        "message": "Score saved successfully",
        "score": {
            "id": model.id,
            "submission_id": model.submission_id,
            "judge_id": model.judge_id,
            "criteria_id": model.criteria_id,
            "score_value": float(model.score_value),
            "comment": model.comment,
        },
    }), 200


@score_bp.route(
    "/submissions/<int:submission_id>/feedback",
    methods=["POST"],
)
@role_required("judge")
def submit_feedback(submission_id):

    data = request.get_json(silent=True) or {}

    judge_id = request.user.get("user_id")

    if not judge_id:
        return jsonify({
            "message": "Judge information is missing"
        }), 401

    summary_feedback = data.get("summary_feedback")
    final_recommendation = data.get("final_recommendation")
    is_finalized = bool(data.get("is_finalized", False))

    if isinstance(summary_feedback, str):
        summary_feedback = summary_feedback.strip()

    if not summary_feedback and is_finalized:
        return jsonify({
            "message": "summary_feedback is required"
        }), 400

    if not summary_feedback:
        summary_feedback = ""

    user_role = request.user.get("role", "judge")

    try:
        assigned = score_service.is_judge_assigned(
            submission_id=submission_id,
            judge_id=judge_id,
            user_role=user_role,
        )
    except Exception:
        assigned = False

    if not assigned:
        return jsonify({
            "message": "Judge is not assigned to this submission"
        }), 403

    try:
        model, error = score_service.submit_feedback(
            submission_id=submission_id,
            judge_id=judge_id,
            summary_feedback=summary_feedback,
            final_recommendation=final_recommendation,
            is_finalized=is_finalized,
        )
    except Exception as error:
        return jsonify({
            "message": "Failed to save feedback",
            "error": str(error),
        }), 500

    if error == "submission_not_found":
        return jsonify({
            "message": "Submission not found"
        }), 404

    if error == "feedback_finalized":
        return jsonify({
            "message": "This review has already been finalized and can no longer be edited"
        }), 409

    if error == "round_finalized":
        return jsonify({
            "message": "This round has already been finalized and scores are locked"
        }), 409

    if model is None:
        return jsonify({
            "message": "Failed to save feedback"
        }), 500

    return jsonify({
        "message": "Feedback saved successfully",
        "feedback": {
            "id": model.id,
            "submission_id": model.submission_id,
            "judge_id": model.judge_id,
            "summary_feedback": model.summary_feedback,
            "final_recommendation": model.final_recommendation,
            "is_finalized": bool(getattr(model, "is_finalized", False)),
        },
    }), 200


@score_bp.route(
    "/submissions/<int:submission_id>/state",
    methods=["GET"],
)
@role_required("judge", "admin")
def get_submission_state(submission_id):

    judge_id = request.user.get("user_id")
    user_role = request.user.get("role", "judge")

    if not judge_id:
        return jsonify({
            "message": "Judge information is missing"
        }), 401

    try:
        payload, error = score_service.get_submission_review_data(
            submission_id=submission_id,
            judge_id=judge_id,
            user_role=user_role,
        )
    except Exception as error:
        return jsonify({
            "message": "Failed to get submission state",
            "error": str(error),
        }), 500

    if error == "submission_not_found":
        return jsonify({
            "message": "Submission not found"
        }), 404

    if error == "not_assigned":
        return jsonify({
            "message": "Judge is not assigned to this submission"
        }), 403

    if payload is None:
        return jsonify({
            "message": "Failed to get submission state"
        }), 500

    return jsonify(payload), 200


@score_bp.route(
    "/submissions/<int:submission_id>/calculate",
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

    try:
        submission, error = (
            score_service.calculate_submission_score(
                submission_id
            )
        )
    except Exception as error:
        return jsonify({
            "message": "Failed to calculate submission score",
            "error": str(error),
        }), 500

    if error == "submission_not_found":
        return jsonify({
            "message": "Submission not found"
        }), 404

    if submission is None:
        return jsonify({
            "message": "Failed to calculate submission score"
        }), 500

    return jsonify({
        "message": "Submission score calculated successfully",
        "submission": {
            "id": submission.id,
            "final_score": (
                float(submission.final_score)
                if submission.final_score is not None
                else None
            ),
        },
    }), 200


@score_bp.route(
    "/rounds/<int:round_id>/finalize",
    methods=["POST"],
)
@role_required("organizer", "admin")
def finalize_round(round_id):

    try:
        result, error = score_service.finalize_round(
            round_id
        )
    except Exception as error:
        return jsonify({
            "message": "Failed to finalize round",
            "error": str(error),
        }), 500

    if error == "round_not_found":
        return jsonify({
            "message": "Round not found"
        }), 404

    if error == "round_already_finalized":
        return jsonify({
            "message": "Round has already been finalized"
        }), 409

    if result is None:
        return jsonify({
            "message": "Failed to finalize round"
        }), 500

    return jsonify(result), 200
