# Configuration settings for the Flask application
import os
from pathlib import Path
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")
load_dotenv(Path(__file__).resolve().parent / ".env")
load_dotenv()

FRONTEND_UPLOAD_DIR = PROJECT_ROOT / "frontend" / "static" / "uploads"


class FactoryConfig:
    """Factory to get configuration based on environment."""

    @staticmethod
    def get_config(env: str):
        if env == "development":
            return DevelopmentConfig
        elif env == "testing":
            return TestingConfig
        elif env == "production":
            return ProductionConfig
        else:
            return Config


class Config:
    """Base configuration."""

    SECRET_KEY = os.environ.get(
        "SECRET_KEY"
    ) or "dev-secret-key-change-me-in-production-32chars"

    DEBUG = os.environ.get(
        "DEBUG",
        "False",
    ).lower() in ["true", "1"]

    TESTING = os.environ.get(
        "TESTING",
        "False",
    ).lower() in ["true", "1"]

    DATABASE_URI = os.environ.get(
        "DATABASE_URI"
    ) or os.environ.get(
        "POSTGREE_DATABASE_URL"
    )

    CORS_HEADERS = "Content-Type"

    # =========================================================
    # Storage Service Configuration
    # =========================================================

    STORAGE_PROVIDER = os.environ.get(
        "STORAGE_PROVIDER",
        "local",
    ).lower()

    UPLOAD_FOLDER = os.environ.get(
        "UPLOAD_FOLDER",
        str(FRONTEND_UPLOAD_DIR),
    )

    MAX_CONTENT_LENGTH = int(
        os.environ.get(
            "MAX_CONTENT_LENGTH",
            50 * 1024 * 1024,
        )
    )

    BASE_URL = os.environ.get(
        "BASE_URL",
        "http://localhost:9999",
    )

    # =========================================================
    # Cloudinary Configuration
    # =========================================================

    CLOUDINARY_URL = os.environ.get("CLOUDINARY_URL")

    CLOUDINARY_CLOUD_NAME = os.environ.get(
        "CLOUDINARY_CLOUD_NAME"
    )

    CLOUDINARY_API_KEY = os.environ.get(
        "CLOUDINARY_API_KEY"
    )

    CLOUDINARY_API_SECRET = os.environ.get(
        "CLOUDINARY_API_SECRET"
    )

class DevelopmentConfig(Config):
    """Development configuration."""

    DEBUG = True

    DATABASE_URI = os.environ.get(
        "POSTGREE_DATABASE_URL"
    )


class TestingConfig(Config):
    """Testing configuration."""

    TESTING = True

    DATABASE_URI = os.environ.get(
        "DATABASE_URI"
    ) or os.environ.get(
        "POSTGREE_DATABASE_URL"
    )


class ProductionConfig(Config):
    """Production configuration."""

    DATABASE_URI = os.environ.get(
        "DATABASE_URI"
    ) or os.environ.get(
        "POSTGREE_DATABASE_URL"
    )


# =============================================================
# Swagger Configuration
# =============================================================

template = {
    "swagger": "2.0",
    "info": {
        "title": "Todo API",
        "description": "API for managing todos",
        "version": "1.0.0",
    },
    "basePath": "/",
    "schemes": [
        "http",
        "https",
    ],
    "consumes": [
        "application/json",
    ],
    "produces": [
        "application/json",
    ],
}


class SwaggerConfig:
    """Swagger configuration."""

    template = {
        "swagger": "2.0",
        "info": {
            "title": "Todo API",
            "description": "API for managing todos",
            "version": "1.0.0",
        },
        "basePath": "/",
        "schemes": [
            "http",
            "https",
        ],
        "consumes": [
            "application/json",
        ],
        "produces": [
            "application/json",
        ],
    }

    swagger_config = {
        "headers": [],
        "specs": [
            {
                "endpoint": "apispec",
                "route": "/apispec.json",
                "rule_filter": lambda rule: True,
                "model_filter": lambda tag: True,
            }
        ],
        "static_url_path": "/flasgger_static",
        "swagger_ui": True,
        "specs_route": "/docs",
    }
