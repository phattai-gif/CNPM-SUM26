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

"""
Gallery Controller - Handles public photo gallery endpoints and multi-criteria filters.
FE06.1 & FE06.2 implementation.
"""

from flask import Blueprint, jsonify, request
from sqlalchemy import extract, or_, distinct
from infrastructure.models.app.app_submission_model import SubmissionModel
from infrastructure.models.app.app_submission_file_model import SubmissionFileModel
from infrastructure.models.app.app_submission_film_metadata_model import SubmissionFilmMetadataModel
from infrastructure.models.app.app_round_model import RoundModel
from infrastructure.models.app.app_contest_model import ContestModel
from infrastructure.models.app.app_user_model import UserModel

gallery_bp = Blueprint('gallery_api', __name__, url_prefix='/api/gallery')


def get_db_session():
    """Retrieve active database session."""
    try:
        from api.controllers.contest_controller import contest_service
        return contest_service.repository.session
    except Exception:
        from infrastructure.databases.factory_database import FactoryDatabase
        return FactoryDatabase.get_database("POSTGREE").session


@gallery_bp.route('', methods=['GET'])
def get_public_gallery():
    """
    GET /api/gallery
    Fetch public submissions with filtering (film_stock, camera, contest_id, year, search)
    and pagination (page, limit).
    """
    try:
        session = get_db_session()

        # Extract query params
        film_stock = request.args.get('film_stock', '').strip()
        camera = request.args.get('camera', '').strip()
        contest_id_param = request.args.get('contest_id', '').strip()
        year_param = request.args.get('year', '').strip()
        search_query = request.args.get('search', '').strip()
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 12, type=int)

        if page < 1:
            page = 1
        if limit < 1 or limit > 100:
            limit = 12

        # Public gallery is restricted to winner-approved submissions only.
        query = (
            session.query(
                SubmissionModel,
                SubmissionFileModel,
                SubmissionFilmMetadataModel,
                ContestModel,
                UserModel
            )
            .join(RoundModel, SubmissionModel.round_id == RoundModel.id)
            .join(ContestModel, RoundModel.contest_id == ContestModel.id)
            .join(UserModel, SubmissionModel.user_id == UserModel.id)
            .outerjoin(SubmissionFileModel, SubmissionFileModel.submission_id == SubmissionModel.id)
            .outerjoin(SubmissionFilmMetadataModel, SubmissionFilmMetadataModel.submission_id == SubmissionModel.id)
            .filter(SubmissionModel.status == 'winner')
        )

        # Filters
        if film_stock:
            query = query.filter(SubmissionFilmMetadataModel.film_stock.ilike(f"%{film_stock}%"))

        if camera:
            query = query.filter(SubmissionFilmMetadataModel.camera_body.ilike(f"%{camera}%"))

        if contest_id_param and contest_id_param.isdigit():
            query = query.filter(ContestModel.id == int(contest_id_param))

        if year_param and year_param.isdigit():
            year_val = int(year_param)
            query = query.filter(
                or_(
                    extract('year', SubmissionModel.created_at) == year_val,
                    extract('year', SubmissionModel.submitted_at) == year_val
                )
            )

        if search_query:
            search_pattern = f"%{search_query}%"
            query = query.filter(
                or_(
                    SubmissionModel.title.ilike(search_pattern),
                    SubmissionModel.story_description.ilike(search_pattern),
                    UserModel.full_name.ilike(search_pattern),
                    UserModel.username.ilike(search_pattern),
                    ContestModel.title.ilike(search_pattern)
                )
            )

        total_count = query.count()
        total_pages = (total_count + limit - 1) // limit if total_count > 0 else 1

        offset = (page - 1) * limit
        rows = (
            query.order_by(SubmissionModel.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

        submissions = []
        for sub, sub_file, meta, contest, user in rows:
            img_url = sub_file.image_hd_url if sub_file else None
            thumb_url = (sub_file.thumbnail_url if sub_file and sub_file.thumbnail_url else img_url)

            author_name = user.full_name or user.username if user else "Tác giả vô danh"
            year = sub.created_at.year if sub.created_at else None

            submissions.append({
                "id": sub.id,
                "title": sub.title,
                "story_description": sub.story_description,
                "status": sub.status,
                "final_score": float(sub.final_score) if sub.final_score is not None else None,
                "created_at": sub.created_at.isoformat() if sub.created_at else None,
                "year": year,
                "image_hd_url": img_url,
                "thumbnail_url": thumb_url,
                "author": {
                    "id": user.id if user else None,
                    "name": author_name,
                    "avatar_url": user.avatar_url if user else None
                },
                "contest": {
                    "id": contest.id if contest else None,
                    "title": contest.title if contest else None
                },
                "film_metadata": {
                    "film_stock": meta.film_stock if meta else "",
                    "camera_body": meta.camera_body if meta else "",
                    "lens": meta.lens if meta else "",
                    "film_iso": meta.film_iso if meta else None,
                    "lab_name": meta.lab_name if meta else "",
                    "scanner_info": meta.scanner_info if meta else "",
                    "taken_at_location": meta.taken_at_location if meta else ""
                }
            })

        return jsonify({
            "submissions": submissions,
            "total": total_count,
            "page": page,
            "limit": limit,
            "total_pages": total_pages
        }), 200

    except Exception as error:
        return jsonify({
            "message": "Error fetching gallery submissions",
            "error": str(error),
            "submissions": [],
            "total": 0
        }), 500


@gallery_bp.route('/filters', methods=['GET'])
def get_gallery_filters():
    """
    GET /api/gallery/filters
    Returns unique film_stocks, cameras, contests, and years available for public gallery filters.
    """
    try:
        session = get_db_session()

        # Film stocks
        film_stocks_rows = (
            session.query(distinct(SubmissionFilmMetadataModel.film_stock))
            .join(SubmissionModel, SubmissionFilmMetadataModel.submission_id == SubmissionModel.id)
            .filter(SubmissionModel.status == 'winner')
            .filter(SubmissionFilmMetadataModel.film_stock.isnot(None))
            .filter(SubmissionFilmMetadataModel.film_stock != '')
            .all()
        )
        film_stocks = sorted([r[0] for r in film_stocks_rows if r[0]])

        # Cameras
        cameras_rows = (
            session.query(distinct(SubmissionFilmMetadataModel.camera_body))
            .join(SubmissionModel, SubmissionFilmMetadataModel.submission_id == SubmissionModel.id)
            .filter(SubmissionModel.status == 'winner')
            .filter(SubmissionFilmMetadataModel.camera_body.isnot(None))
            .filter(SubmissionFilmMetadataModel.camera_body != '')
            .all()
        )
        cameras = sorted([r[0] for r in cameras_rows if r[0]])

        # Contests
        contests_rows = (
            session.query(distinct(ContestModel.id), ContestModel.title)
            .join(RoundModel, RoundModel.contest_id == ContestModel.id)
            .join(SubmissionModel, SubmissionModel.round_id == RoundModel.id)
            .filter(SubmissionModel.status == 'winner')
            .all()
        )
        contests = [{"id": r[0], "title": r[1]} for r in contests_rows]
        contests.sort(key=lambda c: c["title"])

        # Years
        years_rows = (
            session.query(distinct(extract('year', SubmissionModel.created_at)))
            .filter(SubmissionModel.status == 'winner')
            .all()
        )
        years = sorted([int(r[0]) for r in years_rows if r[0] is not None], reverse=True)

        return jsonify({
            "film_stocks": film_stocks,
            "cameras": cameras,
            "contests": contests,
            "years": years
        }), 200

    except Exception as error:
        return jsonify({
            "message": "Error fetching filter metadata",
            "error": str(error),
            "film_stocks": [],
            "cameras": [],
            "contests": [],
            "years": []
        }), 500


@gallery_bp.route('/<int:submission_id>', methods=['GET'])
def get_public_submission_detail(submission_id):
    """
    GET /api/gallery/<submission_id>
    Fetch detail of a specific public submission.
    """
    try:
        session = get_db_session()

        row = (
            session.query(
                SubmissionModel,
                SubmissionFileModel,
                SubmissionFilmMetadataModel,
                ContestModel,
                UserModel,
                RoundModel
            )
            .join(RoundModel, SubmissionModel.round_id == RoundModel.id)
            .join(ContestModel, RoundModel.contest_id == ContestModel.id)
            .join(UserModel, SubmissionModel.user_id == UserModel.id)
            .outerjoin(SubmissionFileModel, SubmissionFileModel.submission_id == SubmissionModel.id)
            .outerjoin(SubmissionFilmMetadataModel, SubmissionFilmMetadataModel.submission_id == SubmissionModel.id)
            .filter(SubmissionModel.id == submission_id)
            .filter(SubmissionModel.status == 'winner')
            .first()
        )

        if not row:
            return jsonify({
                "message": "Public photo submission not found"
            }), 404

        sub, sub_file, meta, contest, user, round_obj = row
        img_url = sub_file.image_hd_url if sub_file else None
        thumb_url = (sub_file.thumbnail_url if sub_file and sub_file.thumbnail_url else img_url)

        author_name = user.full_name or user.username if user else "Tác giả vô danh"
        year = sub.created_at.year if sub.created_at else None

        detail = {
            "id": sub.id,
            "title": sub.title,
            "story_description": sub.story_description,
            "status": sub.status,
            "final_score": float(sub.final_score) if sub.final_score is not None else None,
            "created_at": sub.created_at.isoformat() if sub.created_at else None,
            "submitted_at": sub.submitted_at.isoformat() if sub.submitted_at else None,
            "year": year,
            "image_hd_url": img_url,
            "thumbnail_url": thumb_url,
            "author": {
                "id": user.id if user else None,
                "name": author_name,
                "username": user.username if user else "",
                "avatar_url": user.avatar_url if user else None,
                "bio": user.bio if user else ""
            },
            "contest": {
                "id": contest.id if contest else None,
                "title": contest.title if contest else None,
                "slug": contest.slug if contest else None
            },
            "round": {
                "id": round_obj.id if round_obj else None,
                "title": round_obj.title if round_obj else None
            },
            "film_metadata": {
                "film_stock": meta.film_stock if meta else "",
                "camera_body": meta.camera_body if meta else "",
                "lens": meta.lens if meta else "",
                "film_iso": meta.film_iso if meta else None,
                "lab_name": meta.lab_name if meta else "",
                "scanner_info": meta.scanner_info if meta else "",
                "development_process": meta.development_process if meta else "C-41",
                "taken_at_location": meta.taken_at_location if meta else ""
            }
        }

        return jsonify({"submission": detail}), 200

    except Exception as error:
        return jsonify({
            "message": "Error fetching photo details",
            "error": str(error)
        }), 500
