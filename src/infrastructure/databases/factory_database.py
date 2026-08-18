from infrastructure.databases.abstract_database import AbstractDatabase
from infrastructure.databases.database_postgres import DatabasePostgres


class FactoryDatabase:
    _database = None

    @staticmethod
    def get_database(database_type) -> AbstractDatabase:
        if database_type in {"POSTGREE", "POSTGRES"}:
            if FactoryDatabase._database is None:
                FactoryDatabase._database = DatabasePostgres()
            return FactoryDatabase._database

        raise ValueError(
            f"Unsupported database type: {database_type}"
        )
