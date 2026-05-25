#Модель критичности (OpenAPI: Criticality). Справочник.
from __future__ import annotations

import uuid

from sqlalchemy import Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base


class Criticality(Base):
    __tablename__ = "criticalities"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    level: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)

    # relationships
    issues: Mapped[list["Issue"]] = relationship(
        "Issue", back_populates="criticality"
    )
