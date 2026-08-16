"""Round ORM model."""

from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.sql import func

from infrastructure.databases.base import Base


class RoundModel(Base):
    __tablename__ = "rounds"
    __table_args__ = {"schema": "app", "extend_existing": True}

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    contest_id = Column(BigInteger, ForeignKey("contests.id", ondelete="CASCADE"), nullable=False)
    round_number = Column(Integer, nullable=False, default=1)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    start_date = Column(DateTime(timezone=True), nullable=True)
    end_date = Column(DateTime(timezone=True), nullable=True)
    weight = Column(Numeric(5, 2), default=1.00)
    status = Column(String(20), nullable=False, default="upcoming")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
        nullable=True,
    )

    end_date = Column(
        DateTime(timezone=True),
        nullable=True,
    )

    weight = Column(
        Numeric(5, 2),
        default=1.00,
    )

    status = Column(
        String(20),
        nullable=False,
        default="upcoming",
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )
>>>>>>> 790426c04c0df979b2e2951e003243881e743d3d:src/infrastructure/models/round_model.py
