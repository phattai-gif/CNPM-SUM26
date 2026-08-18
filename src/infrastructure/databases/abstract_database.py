from abc import ABC, abstractmethod

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from config import FactoryConfig


class AbstractDatabase(ABC):
    def __init__(self):
        self.database_uri = FactoryConfig.get_config(
            "development"
        ).DATABASE_URI

        if not self.database_uri:
            raise ValueError(
                "DATABASE_URI is not configured. "
                "Please set DATABASE_URI or POSTGREE_DATABASE_URL in .env"
            )

        self.engine = create_engine(
            self.database_uri,
            pool_pre_ping=True,
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
