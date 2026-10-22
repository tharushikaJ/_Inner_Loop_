from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import BigInteger, Date, DateTime, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    project_name: Mapped[str] = mapped_column(String(255), nullable=False)
    project_category: Mapped[str | None] = mapped_column(String(100))
    project_description: Mapped[str | None] = mapped_column(Text)
    project_type: Mapped[str | None] = mapped_column(String(100))
    responsible_employee_id: Mapped[int | None] = mapped_column(BigInteger)
    current_status: Mapped[str | None] = mapped_column(String(50))
    progress_percentage: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=0)
    current_progress_update: Mapped[str | None] = mapped_column(Text)
    next_activity: Mapped[str | None] = mapped_column(Text)
    target_date: Mapped[date | None] = mapped_column(Date)
    blockers: Mapped[str | None] = mapped_column(Text)
    related_links: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
