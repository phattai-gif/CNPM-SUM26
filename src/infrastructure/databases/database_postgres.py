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
