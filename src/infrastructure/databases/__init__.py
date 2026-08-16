from infrastructure.databases.base import Base
from infrastructure.databases.factory_database import FactoryDatabase

# Import canonical app models so metadata is built from the clean ORM definitions.
from infrastructure.models import *  # noqa: F401,F403


def init_db(app):
    FactoryDatabase.get_database('POSTGREE').init_database(app)


__all__ = ["Base", "init_db"]
