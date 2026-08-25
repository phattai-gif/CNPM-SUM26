from abc import ABC, abstractmethod
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


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

        self.engine = create_engine(
            self.database_uri,
            **engine_options,
        )

        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine,
        )

    @property
    def session(self):
        return self.SessionLocal()

    @abstractmethod
    def init_database(self, app):
        pass