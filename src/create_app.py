from pathlib import Path

from flask import Flask

from config import Config
from api.middleware import setup_middleware
from api.routes import register_routes
from infrastructure.databases import init_db
from app_logging import setup_logging


def create_app():
    frontend_dir = Path(__file__).resolve().parent.parent / 'frontend'
    app = Flask(
        __name__,
        template_folder=str(frontend_dir / 'templates'),
        static_folder=str(frontend_dir / 'static'),
        static_url_path='/static',
    )
    app.config.from_object(Config)

    setup_logging()
    init_db(app)
    setup_middleware(app)
    register_routes(app)

    return app
