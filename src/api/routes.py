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

                return (
                    contest_service
                    .repository
                    .session
                )

            except Exception:
                database = FactoryDatabase.get_database(
                    "POSTGREE"
                )
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
                    output.append({
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
                    })

                return jsonify({
                    "contests": output
                }), 200

            except Exception as error:
                return jsonify({
                    "message": "Error",
                    "error": str(error),
                    "contests": [],
                }), 500

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
                    return jsonify({
                        "message": "Not found"
                    }), 404

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
                        rounds.append({
                            "id": round_model.id,
                            "title": round_model.title,
                            "round_number": (
                                round_model.round_number
                            ),
                            "status": round_model.status,
                        })

                except Exception:
                    rounds = []

                return jsonify({
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
                }), 200

            except Exception as error:
                return jsonify({
                    "message": "Error",
                    "error": str(error),
                }), 500

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
    # IMPORTANT:
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
    # Các function xử lý nằm trong submission_controller.py
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