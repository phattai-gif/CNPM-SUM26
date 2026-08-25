from flask import (
    Blueprint,
    jsonify,
    request,
    redirect,
    render_template,
)

from api.controllers.auth_controller import auth_bp
from api.controllers.ai_detection_controller import bp as ai_detection_bp
from api.controllers.duplicate_detection_controller import (
    bp as duplicate_detection_bp,
)
from api.controllers.score_controller import score_bp
from api.controllers.submission_controller import (
    submission_bp,
    get_organizer_contest_submissions,
    get_judge_assignment_submissions,
)
from api.controllers.submission_review_controller import (
    bp as submission_review_bp,
)
from api.controllers.contest_controller import (
    contest_bp,
    public_bp as contest_public_bp,
    finalize_round,
)
from api.controllers.judge_controller import judge_bp
from api.controllers.notification_controller import notification_bp
from api.controllers.contest_settings_controller import (
    contest_settings_bp,
)
from api.controllers.moderator_controller import moderator_bp
from api.controllers.admin_controller import admin_bp
from api.role_required import role_required


def register_routes(app):
    # ============================================================
    # CORE BLUEPRINTS
    # ============================================================

    app.register_blueprint(auth_bp)
    app.register_blueprint(ai_detection_bp)
    app.register_blueprint(duplicate_detection_bp)
    app.register_blueprint(submission_bp)
    app.register_blueprint(submission_review_bp)
    app.register_blueprint(contest_bp)

    # Finalize round API alias
    app.add_url_rule(
        "/rounds/<int:round_id>/finalize",
        "finalize_round_root",
        finalize_round,
        methods=["POST"],
    )

    app.register_blueprint(contest_public_bp)
    app.register_blueprint(judge_bp)

    # ============================================================
    # BUSINESS DOMAIN BLUEPRINTS
    # ============================================================

    app.register_blueprint(notification_bp)
    app.register_blueprint(contest_settings_bp)
    app.register_blueprint(score_bp)
    app.register_blueprint(moderator_bp)
    app.register_blueprint(admin_bp)

    # ============================================================
    # PUBLIC UI ROUTES
    # ============================================================

    # Root
    try:
        app.add_url_rule(
            "/",
            "root",
            lambda: redirect("/contests"),
        )
    except Exception:
        pass

    # Profile
    try:
        app.add_url_rule(
            "/profile",
            "profile_page",
            lambda: render_template("profile.html"),
        )
    except Exception:
        pass

    # Portfolio
    try:
        app.add_url_rule(
            "/portfolio",
            "portfolio_page",
            lambda: redirect("/profile"),
        )
    except Exception:
        pass

    # Contests page
    try:
        app.add_url_rule(
            "/contests",
            "contests",
            lambda: render_template("contests.html"),
        )
    except Exception:
        pass

    # Organizer contest config page
    try:
        app.add_url_rule(
            "/organizer/contest-config",
            "organizer_contest_config_page",
            lambda: render_template("create_contest.html"),
        )
    except Exception:
        pass

    # Login
    try:
        app.add_url_rule(
            "/login",
            "login",
            lambda: render_template("login.html"),
        )
    except Exception:
        pass

    # Register
    try:
        app.add_url_rule(
            "/register",
            "register",
            lambda: render_template("register.html"),
        )
    except Exception:
        pass

    # Legacy explore
    try:
        app.add_url_rule(
            "/explore",
            "explore",
            lambda: redirect("/contests"),
        )
    except Exception:
        pass

    # Public contest detail
    try:
        app.add_url_rule(
            "/contest/<int:contest_id>",
            "public_contest_page",
            lambda contest_id: render_template(
                "contest_public_detail.html"
            ),
        )
    except Exception:
        pass

    # Judge review center page
    try:
        app.add_url_rule(
            "/judge/review",
            "judge_review_center",
            lambda: render_template("submission_review.html"),
        )
    except Exception:
        pass

    # ============================================================
    # PUBLIC CONTEST APIs
    # ============================================================

    try:
        from infrastructure.models.app import (
            ContestModel,
            RoundModel,
        )

        from infrastructure.databases.factory_database import (
            FactoryDatabase,
        )

        def get_database_session():
            """
            Get current database session.
            """

            try:
                from api.controllers.contest_controller import (
                    contest_service,
                )

                return contest_service.repository.session

            except Exception:
                database = FactoryDatabase.get_database("POSTGREE")
                return database.session

        # ========================================================
        # GET PUBLIC CONTESTS
        # ========================================================

        def api_list_contests():
            try:
                session = get_database_session()

                contests = (
                    session
                    .query(ContestModel)
                    .filter(
                        ContestModel.status.in_(
                            [
                                "published",
                                "active",
                            ]
                        )
                    )
                    .order_by(
                        ContestModel.created_at.desc()
                    )
                    .all()
                )

                output = []

                for contest in contests:
                    output.append(
                        {
                            "id": contest.id,
                            "title": contest.title,
                            "description": contest.description,
                            "status": contest.status,
                            "start_date": (
                                str(contest.start_date)
                                if contest.start_date
                                else None
                            ),
                            "end_date": (
                                str(contest.end_date)
                                if contest.end_date
                                else None
                            ),
                            "banner_url": contest.banner_url,
                        }
                    )

                return jsonify(
                    {
                        "contests": output,
                    }
                ), 200

            except Exception as error:
                return jsonify(
                    {
                        "message": "Error",
                        "error": str(error),
                        "contests": [],
                    }
                ), 500

        app.add_url_rule(
            "/api/contests",
            "api_contests",
            api_list_contests,
            methods=["GET"],
        )

        # ========================================================
        # GET PUBLIC CONTEST DETAIL
        # ========================================================

        def api_get_contest(contest_id):
            try:
                session = get_database_session()

                contest = (
                    session
                    .query(ContestModel)
                    .filter_by(id=contest_id)
                    .first()
                )

                if not contest:
                    return jsonify(
                        {
                            "message": "Not found",
                        }
                    ), 404

                rounds = []

                try:
                    round_models = (
                        session
                        .query(RoundModel)
                        .filter_by(
                            contest_id=contest.id
                        )
                        .order_by(
                            RoundModel.round_number.asc()
                        )
                        .all()
                    )

                    for round_model in round_models:
                        rounds.append(
                            {
                                "id": round_model.id,
                                "title": round_model.title,
                                "round_number": (
                                    round_model.round_number
                                ),
                                "status": round_model.status,
                            }
                        )

                except Exception:
                    rounds = []

                return jsonify(
                    {
                        "contest": {
                            "id": contest.id,
                            "title": contest.title,
                            "description": contest.description,
                            "status": contest.status,
                            "start_date": (
                                str(contest.start_date)
                                if contest.start_date
                                else None
                            ),
                            "end_date": (
                                str(contest.end_date)
                                if contest.end_date
                                else None
                            ),
                            "banner_url": contest.banner_url,
                            "rounds": rounds,
                        }
                    }
                ), 200

            except Exception as error:
                return jsonify(
                    {
                        "message": "Error",
                        "error": str(error),
                    }
                ), 500

        app.add_url_rule(
            "/api/contests/<int:contest_id>",
            "api_get_contest",
            api_get_contest,
            methods=["GET"],
        )

    except Exception:
        pass

    # ============================================================
    # SUBMISSION LIST APIs
    # ============================================================
    #
    # Participant:
    # GET /submissions/my
    #
    # Organizer:
    # GET /organizer/contests/<contest_id>/submissions
    #
    # Judge:
    # GET /judge/assignments/<assignment_id>/submissions
    #
    # ============================================================

    try:
        # --------------------------------------------------------
        # ORGANIZER
        # --------------------------------------------------------

        app.add_url_rule(
            "/organizer/contests/<int:contest_id>/submissions",
            "organizer_contest_submissions",
            get_organizer_contest_submissions,
            methods=["GET"],
        )

        # --------------------------------------------------------
        # API alias cho organizer
        # --------------------------------------------------------

        app.add_url_rule(
            "/api/contests/<int:contest_id>/submissions",
            "api_contest_submissions",
            get_organizer_contest_submissions,
            methods=["GET"],
        )

        # --------------------------------------------------------
        # JUDGE
        # --------------------------------------------------------

        app.add_url_rule(
            "/judge/assignments/<int:assignment_id>/submissions",
            "judge_assignment_submissions",
            get_judge_assignment_submissions,
            methods=["GET"],
        )

        # ========================================================
        # JUDGE REVIEW DETAIL API
        # ========================================================

        @role_required("judge", "admin")
        def judge_review_submission_detail(submission_id):
            from infrastructure.databases.factory_database import (
                FactoryDatabase,
            )

            from infrastructure.models.app import (
                CriteriaModel,
                JudgeAssignmentModel,
                SubmissionFileModel,
                SubmissionFilmMetadataModel,
                SubmissionModel,
            )

            session = (
                FactoryDatabase
                .get_database("POSTGREE")
                .session
            )

            # ----------------------------------------------------
            # Find submission
            # ----------------------------------------------------

            submission = (
                session
                .query(SubmissionModel)
                .filter_by(id=submission_id)
                .first()
            )

            if not submission:
                return jsonify(
                    {
                        "message": "Submission not found",
                    }
                ), 404

            user_id = request.user.get("user_id")
            user_role = request.user.get("role")

            # ----------------------------------------------------
            # Check judge assignment
            # ----------------------------------------------------

            if user_role != "admin":
                assignments = (
                    session
                    .query(JudgeAssignmentModel)
                    .filter(
                        JudgeAssignmentModel.round_id
                        == submission.round_id,
                        JudgeAssignmentModel.judge_id
                        == user_id,
                    )
                    .all()
                )

                is_allowed = any(
                    item.submission_id is None
                    or item.submission_id == submission.id
                    for item in assignments
                )

                if not is_allowed:
                    return jsonify(
                        {
                            "message": "Forbidden",
                        }
                    ), 403

            # ----------------------------------------------------
            # Main image
            # ----------------------------------------------------

            main_image_file = (
                session
                .query(SubmissionFileModel)
                .filter_by(
                    submission_id=submission.id,
                    file_type="main_image",
                )
                .first()
            )

            # ----------------------------------------------------
            # Film metadata
            # ----------------------------------------------------

            film_metadata = (
                session
                .query(SubmissionFilmMetadataModel)
                .filter_by(
                    submission_id=submission.id
                )
                .first()
            )

            # ----------------------------------------------------
            # Criteria
            # ----------------------------------------------------

            criteria_models = (
                session
                .query(CriteriaModel)
                .filter_by(
                    round_id=submission.round_id
                )
                .order_by(
                    CriteriaModel.id.asc()
                )
                .all()
            )

            # ----------------------------------------------------
            # Submission navigation
            # ----------------------------------------------------

            round_submissions = (
                session
                .query(SubmissionModel)
                .filter_by(
                    round_id=submission.round_id
                )
                .order_by(
                    SubmissionModel.id.asc()
                )
                .all()
            )

            ordered_ids = [
                item.id
                for item in round_submissions
            ]

            current_index = ordered_ids.index(
                submission.id
            )

            previous_submission_id = (
                ordered_ids[current_index - 1]
                if current_index > 0
                else None
            )

            next_submission_id = (
                ordered_ids[current_index + 1]
                if current_index < len(ordered_ids) - 1
                else None
            )

            # ----------------------------------------------------
            # All submission files
            # ----------------------------------------------------

            all_submission_files = (
                session
                .query(SubmissionFileModel)
                .filter_by(
                    submission_id=submission.id
                )
                .all()
            )

            files_categorized = {
                "main_image": [],
                "negative": [],
                "contact_sheet": [],
            }

            for submission_file in all_submission_files:
                file_type = (
                    getattr(
                        submission_file,
                        "file_type",
                        "main_image",
                    )
                    or "main_image"
                )

                file_data = {
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
                    "file_type": file_type,
                }

                if file_type not in files_categorized:
                    files_categorized[file_type] = []

                files_categorized[file_type].append(
                    file_data
                )

            # ----------------------------------------------------
            # Response
            # ----------------------------------------------------

            return jsonify(
                {
                    "submission": {
                        "id": submission.id,
                        "round_id": submission.round_id,
                        "status": submission.status,
                        "image_url": (
                            main_image_file.image_hd_url
                            if main_image_file
                            else None
                        ),
                        "files": files_categorized,
                        "metadata": {
                            "camera_body": (
                                film_metadata.camera_body
                                if film_metadata
                                else None
                            ),
                            "lens": (
                                film_metadata.lens
                                if film_metadata
                                else None
                            ),
                            "film_stock": (
                                film_metadata.film_stock
                                if film_metadata
                                else None
                            ),
                            "film_iso": (
                                film_metadata.film_iso
                                if film_metadata
                                else None
                            ),
                            "development_process": (
                                film_metadata.development_process
                                if film_metadata
                                else None
                            ),
                            "width_px": (
                                main_image_file.width_px
                                if main_image_file
                                else None
                            ),
                            "height_px": (
                                main_image_file.height_px
                                if main_image_file
                                else None
                            ),
                        },
                    },
                    "criteria": [
                        {
                            "id": criteria.id,
                            "name": criteria.name,
                            "description": criteria.description,
                            "max_score": float(
                                criteria.max_score
                            ),
                            "weight": float(
                                criteria.weight
                            ),
                        }
                        for criteria in criteria_models
                    ],
                    "navigation": {
                        "previous_submission_id": (
                            previous_submission_id
                        ),
                        "next_submission_id": (
                            next_submission_id
                        ),
                    },
                }
            ), 200

        app.add_url_rule(
            "/api/judge/submissions/<int:submission_id>/review-detail",
            "judge_review_submission_detail",
            judge_review_submission_detail,
            methods=["GET"],
        )

    except Exception as error:
        print(
            "[Routes] Failed to register submission routes:",
            error,
        )

    # ============================================================
    # SPA FALLBACK
    # ============================================================

    def spa_fallback(path):
        """
        Return 404 for API/static paths.
        Other paths are handled by SPA results page.
        """

        if (
            path.startswith("static")
            or path.startswith("api")
            or "." in path
        ):
            from flask import abort

            return abort(404)

        return render_template("results.html")

    try:
        app.add_url_rule(
            "/<path:path>",
            "spa_fallback",
            spa_fallback,
        )
    except Exception:
        pass