from abc import ABC, abstractmethod
import os
import weakref

from sqlalchemy import create_engine
from sqlalchemy.exc import InvalidRequestError
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool


class ResilientSession(Session):
    def refresh(self, instance, attribute_names=None, with_for_update=None):
        try:
            return super().refresh(instance, attribute_names, with_for_update)
        except InvalidRequestError:
            # Re-attach detached ORM instances before refresh.
            self.add(instance)
            return super().refresh(instance, attribute_names, with_for_update)


class AbstractDatabase(ABC):
    def __init__(self):
        self.database_uri = (
            os.environ.get("DATABASE_URI")
            or os.environ.get("POSTGREE_DATABASE_URL")
        )

        if not self.database_uri:
            raise ValueError(
                "DATABASE_URI is not configured. "
                "Please set DATABASE_URI or POSTGREE_DATABASE_URL in .env"
            )

        engine_options = {"pool_pre_ping": True}

        if self.database_uri.startswith("sqlite:///:memory:"):
            engine_options.update(
                {
                    "connect_args": {"check_same_thread": False},
                    "poolclass": StaticPool,
                }
            )
        else:
            engine_options.update(
                {
                    "pool_size": int(os.environ.get("DB_POOL_SIZE", "5")),
                    "max_overflow": int(os.environ.get("DB_MAX_OVERFLOW", "0")),
                    "pool_timeout": int(os.environ.get("DB_POOL_TIMEOUT", "10")),
                }
            )

        self.engine = create_engine(
            self.database_uri,
            **engine_options,
        )

        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine,
            class_=ResilientSession,
        )
        self._sessions = weakref.WeakSet()

    @property
    def session(self):
        session = self.SessionLocal()
        self._sessions.add(session)
        return session

    def close_sessions(self):
        """Close sessions created through this database instance."""
        for session in list(self._sessions):
            session.close()

    @abstractmethod
    def init_database(self, app):
        pass