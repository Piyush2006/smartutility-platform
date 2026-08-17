import datetime
from decimal import Decimal

from app.services.rate_engine import (
    TierSpec,
    TouSpec,
    calculate_consumption_charge,
    calculate_fixed_charge,
    calculate_per_unit_charge,
    calculate_service_charge,
    calculate_tax,
    calculate_tiered_charge,
    calculate_time_of_use_charge,
)


def test_fixed_charge():
    assert calculate_fixed_charge(Decimal("50")) == Decimal("50.00")


def test_per_unit_area_charge():
    assert calculate_per_unit_charge(Decimal("2.5"), Decimal("100")) == Decimal("250.00")


def test_tiered_charge_matches_workbook_example():
    # 0-15 = $5, 15-30 = $6.5, 30+ = $7 (workbook §9)
    tiers = [
        TierSpec(Decimal("0"), Decimal("15"), Decimal("5")),
        TierSpec(Decimal("15"), Decimal("30"), Decimal("6.5")),
        TierSpec(Decimal("30"), None, Decimal("7")),
    ]
    # consumption = 40 -> 15*5 + 15*6.5 + 10*7 = 75 + 97.5 + 70 = 242.5
    assert calculate_tiered_charge(Decimal("40"), tiers) == Decimal("242.50")


def test_tiered_charge_within_first_tier_only():
    tiers = [
        TierSpec(Decimal("0"), Decimal("15"), Decimal("5")),
        TierSpec(Decimal("15"), Decimal("30"), Decimal("6.5")),
        TierSpec(Decimal("30"), None, Decimal("7")),
    ]
    assert calculate_tiered_charge(Decimal("10"), tiers) == Decimal("50.00")


def test_time_of_use_matches_workbook_example():
    # 12am-4pm = $4.5784 (16h), 4pm-12am = $5.67 (8h) (workbook §9)
    windows = [
        TouSpec(datetime.time(0, 0), datetime.time(16, 0), Decimal("4.5784")),
        TouSpec(datetime.time(16, 0), datetime.time(0, 0), Decimal("5.67")),
    ]
    consumption = Decimal("24")
    # 16h window gets 16/24 of consumption = 16 units @ 4.5784 = 73.2544
    # 8h window gets 8/24 of consumption = 8 units @ 5.67 = 45.36
    # total = 118.6144 -> rounds to 118.61
    assert calculate_time_of_use_charge(consumption, windows) == Decimal("118.61")


def test_calculate_consumption_charge_dispatches_by_rate_type():
    assert calculate_consumption_charge(rate_type="fixed", rate=Decimal("10"), basis=None, consumption=Decimal("5")) == Decimal("10.00")
    assert calculate_consumption_charge(rate_type="per_unit_area", rate=Decimal("2"), basis=None, consumption=Decimal("5")) == Decimal("10.00")


def test_service_charge_fixed_and_variable():
    assert calculate_service_charge(charge_type="fixed", rate=Decimal("50"), consumption=Decimal("999")) == Decimal("50.00")
    assert calculate_service_charge(charge_type="variable", rate=Decimal("0.5"), consumption=Decimal("10")) == Decimal("5.00")


def test_tax_calculation():
    assert calculate_tax(Decimal("100"), Decimal("13")) == Decimal("13.00")
    assert calculate_tax(Decimal("100"), None) == Decimal("0.00")
    assert calculate_tax(Decimal("242.50"), Decimal("8.5")) == Decimal("20.61")
