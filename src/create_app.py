from pathlib import Path

from flask import Flask

from config import Config
from api.middleware import setup_middleware
from api.routes import register_routes
from infrastructure.databases import init_db
from app_logging import setup_logging
from services.scheduler_service import SchedulerService

def create_app():
    frontend_dir = (
        Path(__file__).resolve().parent.parent / "frontend"
    )

    app = Flask(
        __name__,
        template_folder=str(frontend_dir / "templates"),
        static_folder=str(frontend_dir / "static"),
        static_url_path="/static",
    )

    # Use safe JSON provider to avoid 500s when tests inject MagicMocks
    try:
        from api.controllers.response_utils import SafeJSONProvider

        app.json_provider_class = SafeJSONProvider
        app.json = SafeJSONProvider(app)
    except Exception:
        pass

    app.config.from_object(Config)
    app.config['JSON_AS_ASCII'] = False
    if hasattr(app, 'json'):
        app.json.ensure_ascii = False

    # ---------------------------------------------------------
    # Application initialization
    # ---------------------------------------------------------

    setup_logging()

    init_db(app)

    setup_middleware(app)

    register_routes(app)

    # Global exception handler to ensure unhandled exceptions return JSON
    try:
        from api.controllers.response_utils import safe_jsonify

        @app.errorhandler(Exception)
        def _handle_unexpected_error(e):
            # Don't expose internal details in production, but include error string in tests
            return safe_jsonify({'message': 'Internal server error', 'error': str(e)}, status=500)
    except Exception:
        pass

    # ---------------------------------------------------------
    # Contest / Round Auto Scheduler
    # ---------------------------------------------------------
    #
    # SchedulerService is responsible for:
    # - Starting APScheduler
    # - Checking contest/round dates
    # - Updating statuses automatically
    # - Logging automatic status changes
    #
    # Scheduler is disabled when TESTING=True so that pytest
    # does not create background threads.
    # ---------------------------------------------------------

    scheduler_service = SchedulerService.get_instance()

    if not app.config.get("TESTING", False):
        scheduler_service.init_app(app)

    return app


# -------------------------------------------------------------
# Run application directly
# -------------------------------------------------------------

if __name__ == "__main__":
    app = create_app()

    app.run(
        host="0.0.0.0",
        port=9999,
        debug=True,
    )
