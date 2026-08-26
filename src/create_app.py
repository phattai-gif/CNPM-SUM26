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

    app.config.from_object(Config)

    # ---------------------------------------------------------
    # Application initialization
    # ---------------------------------------------------------

    setup_logging()

    init_db(app)

    setup_middleware(app)

    register_routes(app)

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
