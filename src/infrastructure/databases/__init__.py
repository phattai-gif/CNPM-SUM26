from infrastructure.databases.base import Base
from infrastructure.databases.factory_database import FactoryDatabase

# Import canonical app models before metadata.create_all() so all tables are registered.
from infrastructure.models import *  # noqa: F401,F403


def init_db(app):
    db = FactoryDatabase.get_database("POSTGREE")
    db.init_database(app)

    if not app.extensions.get("database_session_cleanup"):
        @app.teardown_appcontext
        def close_database_sessions(error=None):
            db.close_sessions()

        app.extensions["database_session_cleanup"] = True


__all__ = ["Base", "init_db"]
