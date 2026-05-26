"""ORM-модели: User, UserSettings, JobRecord, UsageLog."""

from __future__ import annotations

import time
from typing import Optional

from sqlalchemy import Float, ForeignKey, Integer, String, Text, Boolean
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


def _now() -> float:
    return time.time()


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[float] = mapped_column(Float, default=_now, nullable=False)

    settings: Mapped[Optional["UserSettings"]] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )


class UserSettings(Base):
    __tablename__ = "user_settings"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    # Fernet-зашифрованные ключи (text base64).
    wavespeed_key_enc: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    openrouter_key_enc: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    default_model: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    updated_at: Mapped[float] = mapped_column(Float, default=_now, nullable=False)

    user: Mapped[User] = relationship(back_populates="settings")


class JobRecord(Base):
    """Лёгкая ссылка на job для UI «мои задачи»; полный стейт хранится в файле/памяти."""

    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    status: Mapped[str] = mapped_column(String(32), default="queued", nullable=False)
    generator: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    output_path: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    created_at: Mapped[float] = mapped_column(Float, default=_now, nullable=False)
    updated_at: Mapped[float] = mapped_column(Float, default=_now, nullable=False)


class UsageLog(Base):
    __tablename__ = "usage_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    job_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    model: Mapped[str] = mapped_column(String(128), nullable=False)
    seconds: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    cost_estimate_usd: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    created_at: Mapped[float] = mapped_column(Float, default=_now, nullable=False)
