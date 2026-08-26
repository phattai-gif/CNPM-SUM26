from sqlalchemy import BigInteger, Boolean, Integer, inspect, text
from sqlalchemy.exc import SQLAlchemyError

from infrastructure.databases.abstract_database import AbstractDatabase
from infrastructure.databases.base import Base


class DatabasePostgres(AbstractDatabase):
    def __init__(self):
        super().__init__()

        if self.engine.dialect.name == "sqlite":
            self.engine = self.engine.execution_options(
                schema_translate_map={"app": None}
            )

            self.SessionLocal.configure(bind=self.engine)

            for table in Base.metadata.tables.values():
                is_single_column_pk = len(table.primary_key.columns) == 1

                for column in table.primary_key.columns:
                    if isinstance(column.type, BigInteger):
                        column.type = Integer()

                        if is_single_column_pk:
                            column.autoincrement = True

    def init_database(self, app):
        if self.engine.dialect.name == "sqlite":
            Base.metadata.create_all(bind=self.engine)
            self._add_missing_sqlite_columns()
            return

        with self.engine.begin() as connection:
            connection.execute(
                text("CREATE SCHEMA IF NOT EXISTS app")
            )
            connection.execute(
                text("SET search_path TO app, public")
            )

        Base.metadata.create_all(bind=self.engine)

        try:
            with self.engine.begin() as connection:
                self._add_postgres_column_if_missing(
                    connection, "users", "email_verified",
                    "BOOLEAN NOT NULL DEFAULT FALSE"
                )
                self._add_postgres_column_if_missing(
                    connection, "submission_files", "file_type",
                    "VARCHAR(50) DEFAULT 'main_image' NOT NULL"
                )
                self._add_postgres_column_if_missing(
                    connection, "submission_files", "updated_at",
                    "TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP"
                )
                self._add_postgres_column_if_missing(
                    connection, "submission_film_metadata", "updated_at",
                    "TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP"
                )
                self._add_postgres_column_if_missing(
                    connection, "submissions", "updated_at",
                    "TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP"
                )
                self._add_postgres_column_if_missing(
                    connection, "submission_reviews", "updated_at",
                    "TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP"
                )
        except SQLAlchemyError as error:
            app.logger.warning("PostgreSQL compatibility migration skipped: %s", error)

    @staticmethod
    def _add_postgres_column_if_missing(connection, table_name, column_name, definition):
        existing = {
            column["name"]
            for column in inspect(connection).get_columns(table_name, schema="app")
        }
        if column_name not in existing:
            connection.execute(text(
                f"ALTER TABLE app.{table_name} ADD COLUMN {column_name} {definition}"
            ))

    def _add_missing_sqlite_columns(self):
        """Bring an existing SQLite database up to the current ORM shape."""

        inspector = inspect(self.engine)

        with self.engine.begin() as connection:
            for table in Base.metadata.tables.values():
                table_name = table.name

                if table_name not in inspector.get_table_names():
                    continue

                existing = {
                    column["name"]
                    for column in inspector.get_columns(table_name)
                }

                for column in table.columns:
                    if column.name in existing:
                        continue

                    column_type = column.type.compile(
                        dialect=self.engine.dialect
                    )

                    default_value = "0" if isinstance(column.type, Boolean) else "''"
                    nullable = "" if column.nullable else f" NOT NULL DEFAULT {default_value}"

                    connection.execute(
                        text(
                            f'ALTER TABLE "{table_name}" '
                            f'ADD COLUMN "{column.name}" '
                            f"{column_type}{nullable}"
                        )
                    )