from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, Text, JSON, func
from sqlalchemy.orm import Mapped, mapped_column

from database.db import Base


class Shop(Base):
    __tablename__ = "shops"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    shop_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    phone_number: Mapped[list | None] = mapped_column(JSON, nullable=True)
    category: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    gst_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    miscellaneous_data: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    extracted_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    image_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    role = mapped_column(String, default="normal")