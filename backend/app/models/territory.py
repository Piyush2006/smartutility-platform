"""
Territory hierarchy (workbook §8): Region -> Country -> State -> City ->
Zone -> Division -> Area -> Sub-Area -> Premise. Each level (below Region)
requires its parent to exist -- enforced via NOT NULL FK, and again in the
service layer with a clear error message.
"""
from typing import Optional

from sqlalchemy import Boolean, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TenantOwnedMixin, TimestampMixin, UUIDPKMixin


class Region(UUIDPKMixin, TimestampMixin, TenantOwnedMixin, Base):
    __tablename__ = "regions"
    name: Mapped[str] = mapped_column(String(50), nullable=False)


class Country(UUIDPKMixin, TimestampMixin, TenantOwnedMixin, Base):
    __tablename__ = "countries"
    region_id: Mapped[str] = mapped_column(ForeignKey("regions.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(50), nullable=False)


class State(UUIDPKMixin, TimestampMixin, TenantOwnedMixin, Base):
    __tablename__ = "states"
    country_id: Mapped[str] = mapped_column(ForeignKey("countries.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(50), nullable=False)


class City(UUIDPKMixin, TimestampMixin, TenantOwnedMixin, Base):
    __tablename__ = "cities"
    state_id: Mapped[str] = mapped_column(ForeignKey("states.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(50), nullable=False)


class Zone(UUIDPKMixin, TimestampMixin, TenantOwnedMixin, Base):
    __tablename__ = "zones"
    city_id: Mapped[str] = mapped_column(ForeignKey("cities.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(50), nullable=False)


class Division(UUIDPKMixin, TimestampMixin, TenantOwnedMixin, Base):
    __tablename__ = "divisions"
    zone_id: Mapped[str] = mapped_column(ForeignKey("zones.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(50), nullable=False)


class Area(UUIDPKMixin, TimestampMixin, TenantOwnedMixin, Base):
    __tablename__ = "areas"
    division_id: Mapped[str] = mapped_column(ForeignKey("divisions.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(50), nullable=False)


class SubArea(UUIDPKMixin, TimestampMixin, TenantOwnedMixin, Base):
    __tablename__ = "sub_areas"
    area_id: Mapped[str] = mapped_column(ForeignKey("areas.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    servicable: Mapped[bool] = mapped_column(Boolean, default=True)


class Premise(UUIDPKMixin, TimestampMixin, TenantOwnedMixin, Base):
    __tablename__ = "premises"
    sub_area_id: Mapped[str] = mapped_column(ForeignKey("sub_areas.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    latitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    longitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
