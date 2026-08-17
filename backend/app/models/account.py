"""
Account Management (workbook §9-10): Category/Sub-Category, Rate (Fixed /
Per Unit Area / Variable[Tiered|TOU]), Plan + components + Service Charges.
The rate ENGINE (calculation logic) lives in app/services/rate_engine.py --
these are just the storage shapes, no example values hard-coded.
"""
import datetime
from typing import Optional

from sqlalchemy import Boolean, ForeignKey, Numeric, String, Time
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TenantOwnedMixin, TimestampMixin, UUIDPKMixin

RATE_TYPES = ("fixed", "per_unit_area", "variable")
VARIABLE_BASES = ("tiered", "time_of_use")
BILLING_FREQUENCIES = ("monthly", "bi_monthly", "quarterly", "annually")


class Category(UUIDPKMixin, TimestampMixin, TenantOwnedMixin, Base):
    __tablename__ = "categories"
    name: Mapped[str] = mapped_column(String(50), nullable=False)  # Residential, Commercial, Industrial, ...


class SubCategory(UUIDPKMixin, TimestampMixin, TenantOwnedMixin, Base):
    __tablename__ = "sub_categories"
    category_id: Mapped[str] = mapped_column(ForeignKey("categories.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(50), nullable=False)


class Rate(UUIDPKMixin, TimestampMixin, TenantOwnedMixin, Base):
    __tablename__ = "rates"
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    rate_type: Mapped[str] = mapped_column(String(20), nullable=False)  # RATE_TYPES
    # Used directly for fixed / per_unit_area; ignored for variable (tiers/TOU rows carry the numbers).
    rate: Mapped[Optional[float]] = mapped_column(Numeric(12, 3), nullable=True)
    basis: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # VARIABLE_BASES, only if rate_type=variable


class RateTier(UUIDPKMixin, TenantOwnedMixin, Base):
    """One tier row for a `basis=tiered` variable rate, e.g. 0-15 = $5."""

    __tablename__ = "rate_tiers"
    rate_id: Mapped[str] = mapped_column(ForeignKey("rates.id"), nullable=False)
    tier_from: Mapped[float] = mapped_column(Numeric(12, 3), nullable=False)
    tier_to: Mapped[Optional[float]] = mapped_column(Numeric(12, 3), nullable=True)  # null = open-ended ("30+")
    price: Mapped[float] = mapped_column(Numeric(12, 4), nullable=False)


class TouRate(UUIDPKMixin, TenantOwnedMixin, Base):
    """One time-window row for a `basis=time_of_use` variable rate."""

    __tablename__ = "tou_rates"
    rate_id: Mapped[str] = mapped_column(ForeignKey("rates.id"), nullable=False)
    start_time: Mapped[datetime.time] = mapped_column(Time, nullable=False)
    end_time: Mapped[datetime.time] = mapped_column(Time, nullable=False)
    price: Mapped[float] = mapped_column(Numeric(12, 4), nullable=False)


class Plan(UUIDPKMixin, TimestampMixin, TenantOwnedMixin, Base):
    __tablename__ = "plans"
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    category_id: Mapped[str] = mapped_column(ForeignKey("categories.id"), nullable=False)
    sub_category_id: Mapped[str] = mapped_column(ForeignKey("sub_categories.id"), nullable=False)
    tax_percent: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)
    billing_frequency: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # BILLING_FREQUENCIES
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class PlanComponent(UUIDPKMixin, TenantOwnedMixin, Base):
    """One (utility service -> rate) component of a plan. A plan can have many."""

    __tablename__ = "plan_components"
    plan_id: Mapped[str] = mapped_column(ForeignKey("plans.id"), nullable=False)
    utility_service_id: Mapped[str] = mapped_column(ForeignKey("utility_services.id"), nullable=False)
    rate_id: Mapped[str] = mapped_column(ForeignKey("rates.id"), nullable=False)


class ServiceCharge(UUIDPKMixin, TimestampMixin, TenantOwnedMixin, Base):
    __tablename__ = "service_charges"
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    utility_service_id: Mapped[Optional[str]] = mapped_column(ForeignKey("utility_services.id"), nullable=True)  # null = "All"
    charge_type: Mapped[str] = mapped_column(String(20), nullable=False)  # "fixed" | "variable"
    rate: Mapped[float] = mapped_column(Numeric(12, 3), nullable=False)
    plan_id: Mapped[Optional[str]] = mapped_column(ForeignKey("plans.id"), nullable=True)
