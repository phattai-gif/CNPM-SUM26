import os

from infrastructure.databases.abstract_database import AbstractDatabase
from infrastructure.databases.database_postgres import DatabasePostgres
from infrastructure.databases.base import Base


class FactoryDatabase:
    _database = None
    _database_uri = None

    @staticmethod
    def get_database(database_type) -> AbstractDatabase:
        if database_type in {"POSTGREE", "POSTGRES"}:
            database_uri = os.environ.get("DATABASE_URI") or os.environ.get(
                "POSTGREE_DATABASE_URL"
            )
            if (
                FactoryDatabase._database is None
                or FactoryDatabase._database_uri != database_uri
            ):
                FactoryDatabase._database = DatabasePostgres()
                FactoryDatabase._database_uri = database_uri

            # In test runs, SQLite engines may be disposed/reset by other
            # modules. Ensure required tables exist before returning.
            if FactoryDatabase._database.engine.dialect.name == "sqlite":
                Base.metadata.create_all(bind=FactoryDatabase._database.engine)

            return FactoryDatabase._database

        raise ValueError(
            f"Unsupported database type: {database_type}"
        )
