"""Gallery API Controller."""

from flask import Blueprint, jsonify, request

from infrastructure.repositories.submission_repository import SubmissionRepository
from services.submission_service import SubmissionService

gallery_bp = Blueprint("gallery", __name__, url_prefix="/api")


@gallery_bp.route("/gallery", methods=["GET"])
def get_public_gallery():
    """
    Public Gallery API endpoint.
    GET /api/gallery
    Supports filtering by film_stock, camera_model, contest, year and pagination (page, limit).
    """
    submission_service = SubmissionService()

    raw_page = request.args.get("page", 1)
    raw_limit = request.args.get("limit", 20)
    raw_year = request.args.get("year")
    raw_contest = request.args.get("contest")
    film_stock = request.args.get("film_stock")
    camera_model = request.args.get("camera_model")

    # Validate page
    try:
        page = int(raw_page)
        if page < 1:
            return jsonify({"message": "Invalid parameter: page must be an integer >= 1"}), 400
    except (ValueError, TypeError):
        return jsonify({"message": "Invalid parameter: page must be an integer"}), 400

    # Validate limit
    try:
        limit = int(raw_limit)
        if limit <= 0:
            return jsonify({"message": "Invalid parameter: limit must be an integer > 0"}), 400
        if limit > 100:
            return jsonify({"message": "Invalid parameter: limit cannot exceed 100"}), 400
    except (ValueError, TypeError):
        return jsonify({"message": "Invalid parameter: limit must be an integer"}), 400

    # Validate year
    year = None
    if raw_year is not None and raw_year != "":
        try:
            year = int(raw_year)
            if year < 1800 or year > 2200:
                return jsonify({"message": "Invalid parameter: year must be a valid year"}), 400
        except (ValueError, TypeError):
            return jsonify({"message": "Invalid parameter: year must be a valid integer"}), 400

    # Validate contest
    contest_id = None
    if raw_contest is not None and raw_contest != "":
        try:
            contest_id = int(raw_contest)
            if contest_id <= 0:
                return jsonify({"message": "Invalid parameter: contest ID must be a positive integer"}), 400
        except (ValueError, TypeError):
            return jsonify({"message": "Invalid parameter: contest must be a valid integer ID"}), 400

    try:
        data = submission_service.get_public_gallery(
            film_stock=film_stock,
            camera_model=camera_model,
            contest_id=contest_id,
            year=year,
            page=page,
            limit=limit,
        )
        return jsonify(data), 200
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"message": str(e)}), 500

