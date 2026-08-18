from sqlalchemy import text

from infrastructure.databases.abstract_database import AbstractDatabase
from infrastructure.databases.base import Base


class DatabasePostgres(AbstractDatabase):
    def __init__(self):
        super().__init__()

    def init_database(self, app):
        with self.engine.begin() as connection:
            connection.execute(text("CREATE SCHEMA IF NOT EXISTS app"))
            connection.execute(text("SET search_path TO app, public"))
        Base.metadata.create_all(bind=self.engine)

        # Ensure legacy columns expected by ORM exist in DB.
        # Some deployments may have an older schema missing `updated_at` on submission_files.
        try:
            with self.engine.begin() as connection:
                # Add updated_at to submission_files if missing
                connection.execute(text(
                    "ALTER TABLE app.submission_files "
                    "ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;"
                ))
                # Add updated_at to submission_film_metadata if missing
                connection.execute(text(
                    "ALTER TABLE app.submission_film_metadata "
                    "ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;"
                ))
                # Add updated_at to submissions if missing
                connection.execute(text(
                    "ALTER TABLE app.submissions "
                    "ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;"
                ))
                # Add updated_at to submission_reviews if missing
                connection.execute(text(
                    "ALTER TABLE app.submission_reviews "
                    "ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;"
                ))
        except Exception:
            # Do not fail DB init on alter errors; log is handled elsewhere
            pass
