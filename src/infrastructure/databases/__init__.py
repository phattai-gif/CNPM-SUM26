from infrastructure.databases.base import Base
from infrastructure.databases.factory_database import FactoryDatabase

# Import canonical app models before metadata.create_all() so all tables are registered.
from infrastructure.models import *  # noqa: F401,F403


def init_db(app):
    db = FactoryDatabase.get_database("POSTGREE")
    db.init_database(app)


__all__ = ["Base", "init_db"]
