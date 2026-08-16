from infrastructure.databases.abstract_database import AbstractDatabase
from infrastructure.databases.base import Base


class DatabasePostgres(AbstractDatabase):
    def __init__(self):
        super().__init__()

    def init_database(self, app):
        Base.metadata.create_all(bind=self.engine)