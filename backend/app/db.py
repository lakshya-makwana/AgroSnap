import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, Integer, String, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker


class Base(DeclarativeBase):
    pass


class Feedback(Base):
    """[A2] A farmer's verdict on a prediction. Photos are kept only with consent."""

    __tablename__ = "feedback"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    model_version: Mapped[str] = mapped_column(String(80))
    mapping_version: Mapped[str] = mapped_column(String(40))
    verdict: Mapped[str] = mapped_column(String(10))  # correct | wrong | unsure
    predicted_class_id: Mapped[int] = mapped_column(Integer)
    correct_class_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    crop: Mapped[str | None] = mapped_column(String(80), nullable=True)
    photo_consent: Mapped[bool] = mapped_column(Boolean, default=False)
    image_key: Mapped[str | None] = mapped_column(String(200), nullable=True)


def make_sessionmaker(url: str) -> sessionmaker:
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    engine = create_engine(url, connect_args=connect_args)
    # TODO(Phase 7): replace with Alembic migrations (docs/DATABASE.md).
    Base.metadata.create_all(engine)
    return sessionmaker(engine, expire_on_commit=False)
