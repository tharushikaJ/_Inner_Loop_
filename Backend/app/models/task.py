from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import BigInteger, Date, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        primary_key=True
    )

    task_title: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )

    description: Mapped[str | None] = mapped_column(Text)

    project_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("projects.id", ondelete="CASCADE")
    )

    assigned_user_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("users.id")
    )

    priority: Mapped[str | None] = mapped_column(String(50))

    status: Mapped[str | None] = mapped_column(String(50))

    progress_percentage: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=0, nullable=False)

    due_date: Mapped[date | None] = mapped_column(Date)

    progress_note: Mapped[str | None] = mapped_column(Text)

    created_source: Mapped[str | None] = mapped_column(String(100))

    completion_evidence_link: Mapped[str | None] = mapped_column(Text)
    sequence_id: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    parent_task_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now()
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now()
    )
