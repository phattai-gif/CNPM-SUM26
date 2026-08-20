from dotenv import load_dotenv

load_dotenv()
from pathlib import Path

from flask import Flask, jsonify, redirect, url_for, render_template
from jinja2 import ChoiceLoader, FileSystemLoader
from flasgger import Swagger
from flask_swagger_ui import get_swaggerui_blueprint

from api.routes import register_routes
from api.swagger import spec
from api.middleware import middleware
from infrastructure.databases import init_db
from config import Config


# ============================================================
# SCHEDULER
# ============================================================

_scheduler_service = None


def start_scheduler(app):
    """
    Start the application scheduler.

    SchedulerService handles the automatic transition of
    Contest/Round statuses.
    """
    global _scheduler_service

    try:
        from services.scheduler_service import SchedulerService

        # Reuse singleton scheduler service
        _scheduler_service = SchedulerService.get_instance()

        # Initialize scheduler
        _scheduler_service.init_app(app)

        # init_app() automatically starts the scheduler
        # when TESTING is False.
        if _scheduler_service.is_running:
            print(
                "[Scheduler] Contest/Round status scheduler started."
            )

        return _scheduler_service

    except Exception as error:
        print(
            "[Scheduler] Failed to start "
            f"Contest/Round status scheduler: {error}"
        )
        return None


def stop_scheduler():
    """
    Stop the application scheduler safely.
    """
    global _scheduler_service

    if _scheduler_service is not None:
        try:
            _scheduler_service.stop()
            print(
                "[Scheduler] Contest/Round status scheduler stopped."
            )
        except Exception as error:
            print(
                "[Scheduler] Failed to stop scheduler: "
                f"{error}"
            )
        finally:
            _scheduler_service = None

# ============================================================
# APPLICATION FACTORY
# ============================================================

def create_app():
    frontend_dir = (
        Path(__file__).resolve().parent.parent / "frontend"
    )

    app = Flask(
        __name__,
        template_folder=str(
            frontend_dir / "templates"
        ),
        static_folder=str(
            frontend_dir / "static"
        ),
        static_url_path="/static",
    )

    # --------------------------------------------------------
    # CONFIGURATION
    # --------------------------------------------------------

    app.config.from_object(Config)

    # --------------------------------------------------------
    # SWAGGER
    # --------------------------------------------------------

    Swagger(app)

    # --------------------------------------------------------
    # JINJA TEMPLATE LOADERS
    # --------------------------------------------------------

    try:
        src_templates = str(
            Path(__file__).resolve().parent / "templates"
        )

        existing_loader = getattr(
            app,
            "jinja_loader",
            None,
        )

        loaders = [
            FileSystemLoader(src_templates)
        ]

        if existing_loader:
            loaders.append(existing_loader)

        app.jinja_loader = ChoiceLoader(loaders)

    except Exception as error:
        print(
            f"Warning: failed to configure Jinja loaders: {error}"
        )

    # --------------------------------------------------------
    # REGISTER APPLICATION ROUTES
    # --------------------------------------------------------

    register_routes(app)

    # --------------------------------------------------------
    # HOME
    # --------------------------------------------------------

    @app.route("/")
    def home():
        return jsonify(
            {
                "message": (
                    "AI-powered Film Photography "
                    "Contest Management API"
                ),
                "version": "1.0.0",
                "status": "running",
                "endpoints": {
                    "docs": "/docs",
                    "swagger": "/swagger.json",
                    "auth": "/auth",
                    "contests": "/contest",
                    "submissions": "/submission",
                    "ai_detection": "/ai-detection",
                    "judge": "/judge",
                },
            }
        )

    # --------------------------------------------------------
    # JUDGE BLUEPRINT
    # --------------------------------------------------------

    try:
        from api.controllers.judge_controller import (
            judge_bp,
        )

        if judge_bp.name not in app.blueprints:
            app.register_blueprint(judge_bp)

    except Exception as error:
        print(
            f"Warning: judge blueprint registration failed: {error}"
        )

    # --------------------------------------------------------
    # JUDGE UI BLUEPRINT
    # --------------------------------------------------------

    try:
        from api.controllers.judge_controller import (
            judge_ui_bp,
        )

        if judge_ui_bp.name not in app.blueprints:
            app.register_blueprint(judge_ui_bp)

    except Exception as error:
        print(
            "Warning: judge UI blueprint registration "
            f"failed: {error}"
        )

    # --------------------------------------------------------
    # PUBLIC CONTEST BLUEPRINT
    # --------------------------------------------------------

    try:
        from api.controllers.contest_controller import (
            public_bp,
        )

        if public_bp.name not in app.blueprints:
            app.register_blueprint(public_bp)

    except Exception as error:
        print(
            "Warning: public contest blueprint registration "
            f"failed: {error}"
        )

    # --------------------------------------------------------
    # SHORT REDIRECT ROUTES
    # --------------------------------------------------------

    @app.route("/leaderboard")
    def leaderboard_short():
        return redirect(
            url_for(
                "contest_public.public_leaderboard"
            )
        )

    @app.route("/results")
    def results_short():
        return redirect(
            url_for(
                "contest_public.public_results"
            )
        )

    # --------------------------------------------------------
    # SUBMISSION UI
    # --------------------------------------------------------

    @app.route("/my-submissions")
    def my_submissions_page():
        return render_template(
            "my_submissions.html"
        )

    @app.route(
        "/my-submissions/<int:submission_id>"
    )
    def my_submission_detail_page(
        submission_id,
    ):
        return render_template(
            "submission_detail.html",
            submission_id=submission_id,
        )

    @app.route("/submit")
    def submit_page():
        return render_template(
            "submission.html"
        )

    # --------------------------------------------------------
    # LEADERBOARD DEMO
    # --------------------------------------------------------

    @app.route("/leaderboard-demo")
    def leaderboard_demo():
        winners = [
            {
                "rank": 1,
                "author": "Nguyễn Thị C",
                "title": "Hoàng hôn trên sông",
                "score": 97,
                "image_url": (
                    "https://images.unsplash.com/"
                    "photo-1501785888041-af3ef285b470"
                ),
                "camera": "Leica M6",
                "film_stock": "Kodak Portra 400",
            },
            {
                "rank": 2,
                "author": "Trần Văn D",
                "title": "Bến cảng sớm mai",
                "score": 92,
                "image_url": (
                    "https://images.unsplash.com/"
                    "photo-1470770903676-69b98201ea1c"
                ),
                "camera": "Nikon F3",
                "film_stock": "Ilford HP5",
            },
            {
                "rank": 3,
                "author": "Lê Văn E",
                "title": "Mưa rơi phố nhỏ",
                "score": 89,
                "image_url": (
                    "https://images.unsplash.com/"
                    "photo-1506744038136-46273834b3fb"
                ),
                "camera": "Canon AE-1",
                "film_stock": "Fuji Pro 400H",
            },
        ]

        leaderboard = [
            {
                "rank": 1,
                "author": "Nguyễn Thị C",
                "title": "Hoàng hôn trên sông",
                "score": 97,
            },
            {
                "rank": 2,
                "author": "Trần Văn D",
                "title": "Bến cảng sớm mai",
                "score": 92,
            },
            {
                "rank": 3,
                "author": "Lê Văn E",
                "title": "Mưa rơi phố nhỏ",
                "score": 89,
            },
            {
                "rank": 4,
                "author": "Nguyễn Văn A",
                "title": "Bình minh trên phố cổ",
                "score": 85,
            },
            {
                "rank": 5,
                "author": "Phạm Thị B",
                "title": "Ánh đèn đêm",
                "score": 82,
            },
        ]

        return render_template(
            "leaderboard.html",
            winners=winners,
            leaderboard=leaderboard,
        )

    # --------------------------------------------------------
    # SWAGGER UI
    # --------------------------------------------------------

    SWAGGER_URL = "/docs"
    API_URL = "/swagger.json"

    swaggerui_blueprint = get_swaggerui_blueprint(
        SWAGGER_URL,
        API_URL,
        config={
            "app_name": "Contest Management API"
        },
    )

    if swaggerui_blueprint.name not in app.blueprints:
        app.register_blueprint(
            swaggerui_blueprint,
            url_prefix=SWAGGER_URL,
        )

    # --------------------------------------------------------
    # DATABASE
    # --------------------------------------------------------

    try:
        init_db(app)
    except Exception as error:
        print(
            f"Error initializing database: {error}"
        )

    # --------------------------------------------------------
    # MIDDLEWARE
    # --------------------------------------------------------

    middleware(app)

    # --------------------------------------------------------
    # SWAGGER ROUTE REGISTRATION
    # --------------------------------------------------------

    with app.test_request_context():
        for rule in app.url_map.iter_rules():
            endpoint = rule.endpoint

            if endpoint.startswith(
                (
                    "todo.",
                    "user.",
                    "auth.",
                    "ai_detection.",
                    "contest.",
                    "submission.",
                    "judge.",
                )
            ):
                try:
                    view_func = app.view_functions[
                        endpoint
                    ]

                    print(
                        f"Adding path: "
                        f"{rule.rule} -> {view_func}"
                    )

                    spec.path(
                        view=view_func
                    )

                except Exception as error:
                    print(
                        "Warning: Swagger registration "
                        f"failed for {endpoint}: {error}"
                    )

    # --------------------------------------------------------
    # SWAGGER JSON
    # --------------------------------------------------------

    @app.route("/swagger.json")
    def swagger_json():
        return jsonify(
            spec.to_dict()
        )

    # --------------------------------------------------------
    # JUDGE SHORT LINK
    # --------------------------------------------------------

    @app.route(
        "/judge/<int:submission_id>"
    )
    def judge_short_link(
        submission_id,
    ):
        return redirect(
            url_for(
                "contest_public.public_judge_grading",
                submission_id=submission_id,
            )
        )

    # --------------------------------------------------------
    # START AUTO SCHEDULER
    # --------------------------------------------------------

    start_scheduler(app)

    return app


# ============================================================
# RUN APPLICATION
# ============================================================

if __name__ == "__main__":
    app = create_app()

    app.run(
        host="0.0.0.0",
        port=9999,
        debug=True,
        use_reloader=False,
    )