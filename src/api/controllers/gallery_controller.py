"""Gallery API Controller."""

from flask import Blueprint, jsonify, request
from sqlalchemy import extract, or_, distinct

from infrastructure.models.app.app_submission_model import SubmissionModel
from infrastructure.models.app.app_submission_file_model import SubmissionFileModel
from infrastructure.models.app.app_submission_film_metadata_model import (
    SubmissionFilmMetadataModel,
)
from infrastructure.models.app.app_round_model import RoundModel
from infrastructure.models.app.app_contest_model import ContestModel
from infrastructure.models.app.app_user_model import UserModel


# ============================================================
# Blueprint
# ============================================================

gallery_bp = Blueprint(
    "gallery",
    __name__,
    url_prefix="/api",
)


# ============================================================
# Database session
# ============================================================

def get_db_session():
    """Retrieve active database session."""
    try:
        from api.controllers.contest_controller import contest_service

        return contest_service.repository.session

    except Exception:
        from infrastructure.databases.factory_database import FactoryDatabase

        return FactoryDatabase.get_database("POSTGREE").session


# ============================================================
# GET /api/gallery
# ============================================================

@gallery_bp.route("/gallery", methods=["GET"])
def get_public_gallery():
    """
    Public Gallery API.

    GET /api/gallery

    Supports:
        - film_stock
        - camera_model / camera
        - contest / contest_id
        - year
        - search
        - page
        - limit
    """

    try:
        session = get_db_session()

        # ----------------------------------------------------
        # Query parameters
        # ----------------------------------------------------

        film_stock = request.args.get("film_stock")
        camera_model = request.args.get("camera_model")

        # Support both old and new parameter names
        if not camera_model:
            camera_model = request.args.get("camera")

        raw_contest = request.args.get("contest")

        if raw_contest is None:
            raw_contest = request.args.get("contest_id")

        raw_year = request.args.get("year")
        search_query = request.args.get("search")

        raw_page = request.args.get("page", "1")
        raw_limit = request.args.get("limit", "20")

        # Normalize strings
        film_stock = film_stock.strip() if film_stock else None
        camera_model = camera_model.strip() if camera_model else None
        search_query = search_query.strip() if search_query else None

        # ----------------------------------------------------
        # Validate page
        # ----------------------------------------------------

        try:
            page = int(raw_page)

            if page < 1:
                return jsonify({
                    "message": (
                        "Invalid parameter: "
                        "page must be an integer >= 1"
                    )
                }), 400

        except (ValueError, TypeError):
            return jsonify({
                "message": (
                    "Invalid parameter: "
                    "page must be an integer"
                )
            }), 400

        # ----------------------------------------------------
        # Validate limit
        # ----------------------------------------------------

        try:
            limit = int(raw_limit)

            if limit <= 0:
                return jsonify({
                    "message": (
                        "Invalid parameter: "
                        "limit must be an integer > 0"
                    )
                }), 400

            if limit > 100:
                return jsonify({
                    "message": (
                        "Invalid parameter: "
                        "limit cannot exceed 100"
                    )
                }), 400

        except (ValueError, TypeError):
            return jsonify({
                "message": (
                    "Invalid parameter: "
                    "limit must be an integer"
                )
            }), 400

        # ----------------------------------------------------
        # Validate year
        # ----------------------------------------------------

        year = None

        if raw_year is not None and raw_year != "":
            try:
                year = int(raw_year)

                if year < 1800 or year > 2200:
                    return jsonify({
                        "message": (
                            "Invalid parameter: "
                            "year must be a valid year"
                        )
                    }), 400

            except (ValueError, TypeError):
                return jsonify({
                    "message": (
                        "Invalid parameter: "
                        "year must be a valid integer"
                    )
                }), 400

        # ----------------------------------------------------
        # Validate contest
        # ----------------------------------------------------

        contest_id = None

        if raw_contest is not None and raw_contest != "":
            try:
                contest_id = int(raw_contest)

                if contest_id <= 0:
                    return jsonify({
                        "message": (
                            "Invalid parameter: "
                            "contest ID must be a positive integer"
                        )
                    }), 400

            except (ValueError, TypeError):
                return jsonify({
                    "message": (
                        "Invalid parameter: "
                        "contest must be a valid integer ID"
                    )
                }), 400

        # ----------------------------------------------------
        # Base query
        # ----------------------------------------------------

        # Public Gallery only shows winner submissions.
        query = (
            session.query(
                SubmissionModel,
                SubmissionFileModel,
                SubmissionFilmMetadataModel,
                ContestModel,
                UserModel,
            )
            .join(
                RoundModel,
                SubmissionModel.round_id == RoundModel.id,
            )
            .join(
                ContestModel,
                RoundModel.contest_id == ContestModel.id,
            )
            .join(
                UserModel,
                SubmissionModel.user_id == UserModel.id,
            )
            .outerjoin(
                SubmissionFileModel,
                SubmissionFileModel.submission_id
                == SubmissionModel.id,
            )
            .outerjoin(
                SubmissionFilmMetadataModel,
                SubmissionFilmMetadataModel.submission_id
                == SubmissionModel.id,
            )
            .filter(
                SubmissionModel.status == "winner"
            )
        )

        # ----------------------------------------------------
        # Filters
        # ----------------------------------------------------

        if film_stock:
            query = query.filter(
                SubmissionFilmMetadataModel.film_stock.ilike(
                    f"%{film_stock}%"
                )
            )

        if camera_model:
            query = query.filter(
                SubmissionFilmMetadataModel.camera_body.ilike(
                    f"%{camera_model}%"
                )
            )

        if contest_id is not None:
            query = query.filter(
                ContestModel.id == contest_id
            )

        if year is not None:
            query = query.filter(
                or_(
                    extract(
                        "year",
                        SubmissionModel.created_at,
                    ) == year,
                    extract(
                        "year",
                        SubmissionModel.submitted_at,
                    ) == year,
                )
            )

        if search_query:
            search_pattern = f"%{search_query}%"

            query = query.filter(
                or_(
                    SubmissionModel.title.ilike(
                        search_pattern
                    ),
                    SubmissionModel.story_description.ilike(
                        search_pattern
                    ),
                    UserModel.full_name.ilike(
                        search_pattern
                    ),
                    UserModel.username.ilike(
                        search_pattern
                    ),
                    ContestModel.title.ilike(
                        search_pattern
                    ),
                )
            )

        # ----------------------------------------------------
        # Pagination
        # ----------------------------------------------------

        total_count = query.count()

        total_pages = (
            (total_count + limit - 1) // limit
            if total_count > 0
            else 1
        )

        offset = (page - 1) * limit

        rows = (
            query
            .order_by(
                SubmissionModel.created_at.desc()
            )
            .offset(offset)
            .limit(limit)
            .all()
        )

        # ----------------------------------------------------
        # Response
        # ----------------------------------------------------

        submissions = []

        for (
            sub,
            sub_file,
            meta,
            contest,
            user,
        ) in rows:

            image_hd_url = (
                sub_file.image_hd_url
                if sub_file
                else None
            )

            thumbnail_url = (
                sub_file.thumbnail_url
                if sub_file
                and sub_file.thumbnail_url
                else image_hd_url
            )

            if user:
                author_name = (
                    user.full_name
                    or user.username
                    or "Tác giả vô danh"
                )
            else:
                author_name = "Tác giả vô danh"

            submission_year = (
                sub.created_at.year
                if sub.created_at
                else None
            )

            submissions.append({
                "id": sub.id,
                "title": sub.title,
                "story_description": sub.story_description,
                "status": sub.status,
                "final_score": (
                    float(sub.final_score)
                    if sub.final_score is not None
                    else None
                ),
                "created_at": (
                    sub.created_at.isoformat()
                    if sub.created_at
                    else None
                ),
                "year": submission_year,

                "image_hd_url": image_hd_url,
                "thumbnail_url": thumbnail_url,

                "author": {
                    "id": (
                        user.id
                        if user
                        else None
                    ),
                    "name": author_name,
                    "username": (
                        user.username
                        if user
                        else ""
                    ),
                    "avatar_url": (
                        user.avatar_url
                        if user
                        else None
                    ),
                },

                "contest": {
                    "id": (
                        contest.id
                        if contest
                        else None
                    ),
                    "title": (
                        contest.title
                        if contest
                        else None
                    ),
                    "slug": (
                        contest.slug
                        if contest
                        else None
                    ),
                },

                "film_metadata": {
                    "film_stock": (
                        meta.film_stock
                        if meta
                        else ""
                    ),
                    "camera_body": (
                        meta.camera_body
                        if meta
                        else ""
                    ),
                    "lens": (
                        meta.lens
                        if meta
                        else ""
                    ),
                    "film_iso": (
                        meta.film_iso
                        if meta
                        else None
                    ),
                    "lab_name": (
                        meta.lab_name
                        if meta
                        else ""
                    ),
                    "scanner_info": (
                        meta.scanner_info
                        if meta
                        else ""
                    ),
                    "development_process": (
                        meta.development_process
                        if meta
                        else "C-41"
                    ),
                    "taken_at_location": (
                        meta.taken_at_location
                        if meta
                        else ""
                    ),
                },
            })

        return jsonify({
            "submissions": submissions,
            "total": total_count,
            "page": page,
            "limit": limit,
            "total_pages": total_pages,
        }), 200

    except Exception as error:
        import traceback

        traceback.print_exc()

        return jsonify({
            "message": "Error fetching gallery submissions",
            "error": str(error),
            "submissions": [],
            "total": 0,
        }), 500


# ============================================================
# GET /api/gallery/filters
# ============================================================

@gallery_bp.route("/gallery/filters", methods=["GET"])
def get_gallery_filters():
    """
    GET /api/gallery/filters

    Returns unique:
        - film_stocks
        - cameras
        - contests
        - years
    """

    try:
        session = get_db_session()

        # ----------------------------------------------------
        # Film stocks
        # ----------------------------------------------------

        film_stocks_rows = (
            session.query(
                distinct(
                    SubmissionFilmMetadataModel.film_stock
                )
            )
            .join(
                SubmissionModel,
                SubmissionFilmMetadataModel.submission_id
                == SubmissionModel.id,
            )
            .filter(
                SubmissionModel.status == "winner"
            )
            .filter(
                SubmissionFilmMetadataModel.film_stock.isnot(
                    None
                )
            )
            .filter(
                SubmissionFilmMetadataModel.film_stock != ""
            )
            .all()
        )

        film_stocks = sorted(
            [
                row[0]
                for row in film_stocks_rows
                if row[0]
            ]
        )

        # ----------------------------------------------------
        # Cameras
        # ----------------------------------------------------

        cameras_rows = (
            session.query(
                distinct(
                    SubmissionFilmMetadataModel.camera_body
                )
            )
            .join(
                SubmissionModel,
                SubmissionFilmMetadataModel.submission_id
                == SubmissionModel.id,
            )
            .filter(
                SubmissionModel.status == "winner"
            )
            .filter(
                SubmissionFilmMetadataModel.camera_body.isnot(
                    None
                )
            )
            .filter(
                SubmissionFilmMetadataModel.camera_body != ""
            )
            .all()
        )

        cameras = sorted(
            [
                row[0]
                for row in cameras_rows
                if row[0]
            ]
        )

        # ----------------------------------------------------
        # Contests
        # ----------------------------------------------------

        contests_rows = (
            session.query(
                distinct(
                    ContestModel.id
                ),
                ContestModel.title,
            )
            .join(
                RoundModel,
                RoundModel.contest_id
                == ContestModel.id,
            )
            .join(
                SubmissionModel,
                SubmissionModel.round_id
                == RoundModel.id,
            )
            .filter(
                SubmissionModel.status == "winner"
            )
            .all()
        )

        contests = [
            {
                "id": row[0],
                "title": row[1],
            }
            for row in contests_rows
        ]

        contests.sort(
            key=lambda item: item["title"] or ""
        )

        # ----------------------------------------------------
        # Years
        # ----------------------------------------------------

        years_rows = (
            session.query(
                distinct(
                    extract(
                        "year",
                        SubmissionModel.created_at,
                    )
                )
            )
            .filter(
                SubmissionModel.status == "winner"
            )
            .all()
        )

        years = sorted(
            [
                int(row[0])
                for row in years_rows
                if row[0] is not None
            ],
            reverse=True,
        )

        return jsonify({
            "film_stocks": film_stocks,
            "cameras": cameras,
            "contests": contests,
            "years": years,
        }), 200

    except Exception as error:
        import traceback

        traceback.print_exc()

        return jsonify({
            "message": "Error fetching filter metadata",
            "error": str(error),
            "film_stocks": [],
            "cameras": [],
            "contests": [],
            "years": [],
        }), 500


# ============================================================
# GET /api/gallery/<submission_id>
# ============================================================

@gallery_bp.route(
    "/gallery/<int:submission_id>",
    methods=["GET"],
)
def get_public_submission_detail(submission_id):
    """
    GET /api/gallery/<submission_id>

    Fetch detail of a public winner submission.
    """

    try:
        session = get_db_session()

        # ----------------------------------------------------
        # Query submission
        # ----------------------------------------------------

        row = (
            session.query(
                SubmissionModel,
                SubmissionFileModel,
                SubmissionFilmMetadataModel,
                ContestModel,
                UserModel,
                RoundModel,
            )
            .join(
                RoundModel,
                SubmissionModel.round_id
                == RoundModel.id,
            )
            .join(
                ContestModel,
                RoundModel.contest_id
                == ContestModel.id,
            )
            .join(
                UserModel,
                SubmissionModel.user_id
                == UserModel.id,
            )
            .outerjoin(
                SubmissionFileModel,
                SubmissionFileModel.submission_id
                == SubmissionModel.id,
            )
            .outerjoin(
                SubmissionFilmMetadataModel,
                SubmissionFilmMetadataModel.submission_id
                == SubmissionModel.id,
            )
            .filter(
                SubmissionModel.id == submission_id
            )
            .filter(
                SubmissionModel.status == "winner"
            )
            .first()
        )

        # ----------------------------------------------------
        # Not found
        # ----------------------------------------------------

        if not row:
            return jsonify({
                "message": "Public photo submission not found"
            }), 404

        (
            sub,
            sub_file,
            meta,
            contest,
            user,
            round_obj,
        ) = row

        # ----------------------------------------------------
        # Image URLs
        # ----------------------------------------------------

        image_hd_url = (
            sub_file.image_hd_url
            if sub_file
            else None
        )

        thumbnail_url = (
            sub_file.thumbnail_url
            if sub_file
            and sub_file.thumbnail_url
            else image_hd_url
        )

        # ----------------------------------------------------
        # Author
        # ----------------------------------------------------

        if user:
            author_name = (
                user.full_name
                or user.username
                or "Tác giả vô danh"
            )
        else:
            author_name = "Tác giả vô danh"

        # ----------------------------------------------------
        # Year
        # ----------------------------------------------------

        year = (
            sub.created_at.year
            if sub.created_at
            else None
        )

        # ----------------------------------------------------
        # Response object
        # ----------------------------------------------------

        detail = {
            "id": sub.id,
            "title": sub.title,
            "story_description": sub.story_description,
            "status": sub.status,

            "final_score": (
                float(sub.final_score)
                if sub.final_score is not None
                else None
            ),

            "created_at": (
                sub.created_at.isoformat()
                if sub.created_at
                else None
            ),

            "submitted_at": (
                sub.submitted_at.isoformat()
                if sub.submitted_at
                else None
            ),

            "year": year,

            "image_hd_url": image_hd_url,
            "thumbnail_url": thumbnail_url,

            "author": {
                "id": (
                    user.id
                    if user
                    else None
                ),
                "name": author_name,
                "username": (
                    user.username
                    if user
                    else ""
                ),
                "avatar_url": (
                    user.avatar_url
                    if user
                    else None
                ),
                "bio": (
                    user.bio
                    if user
                    else ""
                ),
            },

            "contest": {
                "id": (
                    contest.id
                    if contest
                    else None
                ),
                "title": (
                    contest.title
                    if contest
                    else None
                ),
                "slug": (
                    contest.slug
                    if contest
                    else None
                ),
            },

            "round": {
                "id": (
                    round_obj.id
                    if round_obj
                    else None
                ),
                "title": (
                    round_obj.title
                    if round_obj
                    else None
                ),
            },

            "film_metadata": {
                "film_stock": (
                    meta.film_stock
                    if meta
                    else ""
                ),
                "camera_body": (
                    meta.camera_body
                    if meta
                    else ""
                ),
                "lens": (
                    meta.lens
                    if meta
                    else ""
                ),
                "film_iso": (
                    meta.film_iso
                    if meta
                    else None
                ),
                "lab_name": (
                    meta.lab_name
                    if meta
                    else ""
                ),
                "scanner_info": (
                    meta.scanner_info
                    if meta
                    else ""
                ),
                "development_process": (
                    meta.development_process
                    if meta
                    else "C-41"
                ),
                "taken_at_location": (
                    meta.taken_at_location
                    if meta
                    else ""
                ),
            },
        }

        return jsonify({
            "submission": detail
        }), 200

    except Exception as error:
        import traceback

        traceback.print_exc()

        return jsonify({
            "message": "Error fetching photo details",
            "error": str(error),
        }), 500