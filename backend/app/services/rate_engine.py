"""
Rate engine (CLAUDE.md §9/§20): turns a Rate row (+ its tiers/TOU windows)
and a consumption figure into a charge. No example values are hard-coded
here -- every number comes from the Rate/RateTier/TouRate rows passed in.

Deterministic and unit-tested (see tests/test_rate_engine.py).
"""
from typing import Optional
import datetime
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal


def _d(value) -> Decimal:
    return value if isinstance(value, Decimal) else Decimal(str(value))


def round_money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


@dataclass
class TierSpec:
    tier_from: Decimal
    tier_to: Optional[Decimal]  # None = open-ended
    price: Decimal


@dataclass
class TouSpec:
    start_time: datetime.time
    end_time: datetime.time
    price: Decimal


def calculate_fixed_charge(rate: Decimal) -> Decimal:
    return round_money(_d(rate))


def calculate_per_unit_charge(rate: Decimal, consumption: Decimal) -> Decimal:
    return round_money(_d(rate) * _d(consumption))


def calculate_tiered_charge(consumption: Decimal, tiers: list[TierSpec]) -> Decimal:
    """Progressive tiered billing: each tier only charges the units that
    fall within its own [from, to) band, per the workbook example
    (0-15=$5, 15-30=$6.5, 30+=$7)."""
    consumption = _d(consumption)
    total = Decimal("0")
    for tier in sorted(tiers, key=lambda t: t.tier_from):
        lower = _d(tier.tier_from)
        if consumption <= lower:
            break
        upper_bound = min(consumption, _d(tier.tier_to)) if tier.tier_to is not None else consumption
        units_in_tier = upper_bound - lower
        if units_in_tier > 0:
            total += units_in_tier * _d(tier.price)
    return round_money(total)


def _window_duration_hours(start: datetime.time, end: datetime.time) -> Decimal:
    start_minutes = start.hour * 60 + start.minute
    end_minutes = end.hour * 60 + end.minute
    span = end_minutes - start_minutes
    if span <= 0:  # wraps past midnight, e.g. 16:00 -> 00:00
        span += 24 * 60
    return Decimal(span) / Decimal(60)


def calculate_time_of_use_charge(consumption: Decimal, windows: list[TouSpec]) -> Decimal:
    """MVP simplification (documented): without per-interval AMI data, split
    total consumption across TOU windows proportionally to each window's
    share of the 24h day, then price each share at its window rate. Swap
    for true interval-based billing once smart-meter interval data lands."""
    consumption = _d(consumption)
    durations = [_window_duration_hours(w.start_time, w.end_time) for w in windows]
    total_hours = sum(durations) or Decimal(1)
    total = Decimal("0")
    for window, duration in zip(windows, durations):
        share = consumption * (duration / total_hours)
        total += share * _d(window.price)
    return round_money(total)


def calculate_consumption_charge(*, rate_type: str, rate: Optional[Decimal], basis: Optional[str], consumption: Decimal, tiers: Optional[list[TierSpec]] = None, tou_windows: Optional[list[TouSpec]] = None) -> Decimal:
    if rate_type == "fixed":
        return calculate_fixed_charge(rate)
    if rate_type == "per_unit_area":
        return calculate_per_unit_charge(rate, consumption)
    if rate_type == "variable":
        if basis == "tiered":
            return calculate_tiered_charge(consumption, tiers or [])
        if basis == "time_of_use":
            return calculate_time_of_use_charge(consumption, tou_windows or [])
        raise ValueError(f"Unknown variable rate basis: {basis}")
    raise ValueError(f"Unknown rate_type: {rate_type}")


def calculate_service_charge(*, charge_type: str, rate: Decimal, consumption: Decimal) -> Decimal:
    if charge_type == "fixed":
        return round_money(_d(rate))
    if charge_type == "variable":
        return round_money(_d(rate) * _d(consumption))
    raise ValueError(f"Unknown service charge type: {charge_type}")


def calculate_tax(amount: Decimal, tax_percent: Optional[Decimal]) -> Decimal:
    if not tax_percent:
        return Decimal("0.00")
    return round_money(_d(amount) * _d(tax_percent) / Decimal(100))
