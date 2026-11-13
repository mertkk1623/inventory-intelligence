"""Independent tests for the Package 2 inventory calculation engine."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from config import DEMO_SOURCE
from core.calculations import calculate_inventory
from core.models import InventoryDataset, OpenOrder, ProductMaster, StockMovement
from core.validation import validate_excel_file


def make_dataset(
    *,
    opening_stock: int = 500,
    opening_date: date = date(2026, 10, 1),
    safety_stock: int = 100,
    lead_time_days: int = 12,
    target_coverage_days: int = 20,
    movements: tuple[StockMovement, ...] = (),
    open_orders: tuple[OpenOrder, ...] = (),
) -> InventoryDataset:
    product = ProductMaster(
        product_code="PRF-4040-02",
        product_name="Test Profile 40x40",
        unit="Adet",
        opening_stock=opening_stock,
        opening_stock_date=opening_date,
        safety_stock=safety_stock,
        lead_time_days=lead_time_days,
        target_coverage_days=target_coverage_days,
    )
    return InventoryDataset(
        product=product,
        movements=movements,
        open_orders=open_orders,
        source="upload",
        filename="test.xlsx",
    )


def movement(
    day: date,
    transaction_type: str,
    quantity: int,
) -> StockMovement:
    return StockMovement(
        date=day,
        transaction_type=transaction_type,
        quantity=quantity,
    )


def order(order_no: str, quantity: int, delivery_date: date) -> OpenOrder:
    return OpenOrder(
        order_no=order_no,
        order_quantity=quantity,
        expected_delivery_date=delivery_date,
    )


def test_normal_stock_calculation():
    dataset = make_dataset(
        movements=(
            movement(date(2026, 10, 3), "IN", 100),
            movement(date(2026, 10, 5), "OUT", 40),
            movement(date(2026, 10, 10), "IN", 25),
            movement(date(2026, 10, 11), "OUT", 15),
        )
    )

    result = calculate_inventory(
        dataset, date(2026, 10, 11), today=date(2026, 10, 11)
    )

    assert result.current_stock == 570
    assert result.total_in == 125
    assert result.total_out == 55
    assert result.consumption_coverage_days == 11
    assert result.average_daily_consumption == Decimal(5)
    assert result.days_of_supply == Decimal(114)
    assert result.reorder_point == Decimal(160)
    assert result.target_stock == Decimal(260)
    assert result.inventory_position == 570
    assert result.reorder_required is False
    assert result.suggested_order_quantity == 0
    assert result.negative_stock_warning is False
    assert result.overdue_order_count == 0


def test_only_in_movement():
    dataset = make_dataset(
        opening_stock=100,
        safety_stock=50,
        lead_time_days=10,
        movements=(movement(date(2026, 10, 5), "IN", 50),),
    )

    result = calculate_inventory(
        dataset, date(2026, 10, 10), today=date(2026, 10, 10)
    )

    assert result.current_stock == 150
    assert result.total_in == 50
    assert result.total_out == 0
    assert result.average_daily_consumption == Decimal(0)
    assert result.days_of_supply is None
    assert result.reorder_point == Decimal(50)
    assert result.target_stock == Decimal(50)
    assert result.suggested_order_quantity == 0


def test_only_out_movement():
    dataset = make_dataset(
        opening_stock=100,
        safety_stock=20,
        lead_time_days=5,
        target_coverage_days=10,
        movements=(movement(date(2026, 10, 5), "OUT", 40),),
    )

    result = calculate_inventory(
        dataset, date(2026, 10, 10), today=date(2026, 10, 10)
    )

    assert result.current_stock == 60
    assert result.total_out == 40
    assert result.consumption_coverage_days == 10
    assert result.average_daily_consumption == Decimal(4)
    assert result.days_of_supply == Decimal(15)
    assert result.reorder_point == Decimal(40)
    assert result.target_stock == Decimal(80)
    assert result.reorder_required is False


def test_last_30_days_consumption_uses_calendar_window():
    dataset = make_dataset(
        opening_stock=1000,
        opening_date=date(2026, 1, 1),
        lead_time_days=10,
        movements=(
            movement(date(2026, 10, 14), "OUT", 30),
            movement(date(2026, 10, 15), "OUT", 60),
            movement(date(2026, 10, 31), "OUT", 30),
            movement(date(2026, 11, 13), "OUT", 60),
            movement(date(2026, 11, 14), "OUT", 999),
        ),
    )

    result = calculate_inventory(
        dataset, date(2026, 11, 13), today=date(2026, 11, 13)
    )

    assert result.total_out == 180
    assert result.current_stock == 820
    assert result.consumption_coverage_days == 30
    assert result.average_daily_consumption == Decimal(5)
    assert result.days_of_supply == Decimal(164)
    assert result.reorder_point == Decimal(150)
    assert result.target_stock == Decimal(250)


def test_history_shorter_than_30_days_uses_available_coverage():
    dataset = make_dataset(
        opening_stock=100,
        opening_date=date(2026, 11, 1),
        safety_stock=10,
        lead_time_days=5,
        target_coverage_days=10,
        movements=(movement(date(2026, 11, 5), "OUT", 26),),
    )

    result = calculate_inventory(
        dataset, date(2026, 11, 13), today=date(2026, 11, 13)
    )

    assert result.consumption_coverage_days == 13
    assert result.average_daily_consumption == Decimal(2)
    assert result.current_stock == 74
    assert result.days_of_supply == Decimal(37)


def test_zero_consumption_does_not_divide_by_zero():
    dataset = make_dataset(
        opening_stock=100,
        safety_stock=50,
        lead_time_days=10,
        movements=(movement(date(2026, 10, 5), "IN", 20),),
    )

    result = calculate_inventory(
        dataset, date(2026, 10, 10), today=date(2026, 10, 10)
    )

    assert result.average_daily_consumption == Decimal(0)
    assert result.days_of_supply is None
    assert result.current_stock == 120
    assert result.reorder_point == Decimal(50)
    assert result.target_stock == Decimal(50)
    assert result.suggested_order_quantity == 0


def test_zero_stock_reorders_to_safety_stock():
    dataset = make_dataset(
        opening_stock=0,
        safety_stock=100,
        lead_time_days=12,
    )

    result = calculate_inventory(
        dataset, date(2026, 10, 1), today=date(2026, 10, 1)
    )

    assert result.current_stock == 0
    assert result.average_daily_consumption == Decimal(0)
    assert result.days_of_supply is None
    assert result.reorder_point == Decimal(100)
    assert result.target_stock == Decimal(100)
    assert result.reorder_required is True
    assert result.suggested_order_quantity == 100
    assert result.negative_stock_warning is False


def test_negative_stock_is_reported_and_not_clamped():
    dataset = make_dataset(
        opening_stock=10,
        safety_stock=0,
        lead_time_days=5,
        target_coverage_days=10,
        movements=(movement(date(2026, 10, 2), "OUT", 25),),
    )

    result = calculate_inventory(
        dataset, date(2026, 10, 2), today=date(2026, 10, 2)
    )

    assert result.current_stock == -15
    assert result.lowest_stock_balance == -15
    assert result.negative_stock_warning is True
    assert result.average_daily_consumption == Decimal("12.5")
    assert result.days_of_supply == Decimal("-1.2")
    assert result.reorder_point == Decimal("62.5")
    assert result.target_stock == Decimal("187.5")
    assert result.suggested_order_quantity == 203


def test_movements_after_report_date_are_excluded():
    dataset = make_dataset(
        opening_stock=100,
        safety_stock=0,
        lead_time_days=5,
        target_coverage_days=10,
        movements=(
            movement(date(2026, 10, 5), "IN", 50),
            movement(date(2026, 10, 6), "OUT", 20),
            movement(date(2026, 10, 20), "IN", 999),
            movement(date(2026, 10, 21), "OUT", 888),
        ),
    )

    result = calculate_inventory(
        dataset, date(2026, 10, 10), today=date(2026, 10, 10)
    )

    assert result.total_in == 50
    assert result.total_out == 20
    assert result.current_stock == 130
    assert result.average_daily_consumption == Decimal(2)


def test_open_orders_are_added_to_inventory_position_only():
    dataset = make_dataset(
        opening_stock=100,
        safety_stock=10,
        lead_time_days=5,
        target_coverage_days=10,
        open_orders=(
            order("PO-001", 50, date(2026, 10, 20)),
            order("PO-002", 30, date(2026, 10, 25)),
        ),
    )

    result = calculate_inventory(
        dataset, date(2026, 10, 10), today=date(2026, 10, 10)
    )

    assert result.current_stock == 100
    assert result.total_open_order_quantity == 80
    assert result.inventory_position == 180
    assert result.reorder_required is False


def test_overdue_orders_are_counted():
    dataset = make_dataset(
        opening_stock=100,
        safety_stock=0,
        lead_time_days=5,
        target_coverage_days=10,
        open_orders=(
            order("PO-001", 10, date(2026, 11, 12)),
            order("PO-002", 20, date(2026, 11, 13)),
            order("PO-003", 30, date(2026, 11, 20)),
        ),
    )

    result = calculate_inventory(
        dataset, date(2026, 11, 13), today=date(2026, 11, 13)
    )

    assert result.overdue_order_count == 1
    assert result.total_open_order_quantity == 60
    assert result.inventory_position == 160


def test_reorder_is_suggested_below_reorder_point():
    dataset = make_dataset(
        opening_stock=200,
        opening_date=date(2026, 11, 3),
        safety_stock=50,
        lead_time_days=10,
        movements=(movement(date(2026, 11, 5), "OUT", 100),),
    )

    result = calculate_inventory(
        dataset, date(2026, 11, 12), today=date(2026, 11, 12)
    )

    assert result.average_daily_consumption == Decimal(10)
    assert result.current_stock == 100
    assert result.reorder_point == Decimal(150)
    assert result.target_stock == Decimal(350)
    assert result.reorder_required is True
    assert result.suggested_order_quantity == 250


def test_reorder_is_not_suggested_above_reorder_point():
    dataset = make_dataset(
        opening_stock=500,
        opening_date=date(2026, 11, 3),
        safety_stock=50,
        lead_time_days=10,
        movements=(movement(date(2026, 11, 5), "OUT", 100),),
    )

    result = calculate_inventory(
        dataset, date(2026, 11, 12), today=date(2026, 11, 12)
    )

    assert result.average_daily_consumption == Decimal(10)
    assert result.current_stock == 400
    assert result.reorder_point == Decimal(150)
    assert result.target_stock == Decimal(350)
    assert result.reorder_required is False
    assert result.suggested_order_quantity == 0


def test_reorder_condition_is_inclusive():
    dataset = make_dataset(
        opening_stock=250,
        opening_date=date(2026, 11, 3),
        safety_stock=50,
        lead_time_days=10,
        movements=(movement(date(2026, 11, 5), "OUT", 100),),
    )

    result = calculate_inventory(
        dataset, date(2026, 11, 12), today=date(2026, 11, 12)
    )

    assert result.current_stock == 150
    assert result.reorder_point == Decimal(150)
    assert result.reorder_required is True
    assert result.suggested_order_quantity == 200


def test_suggested_order_quantity_rounds_up():
    dataset = make_dataset(
        opening_stock=35,
        opening_date=date(2026, 11, 3),
        safety_stock=0,
        lead_time_days=5,
        target_coverage_days=10,
        movements=(movement(date(2026, 11, 5), "OUT", 25),),
    )

    result = calculate_inventory(
        dataset, date(2026, 11, 12), today=date(2026, 11, 12)
    )

    assert result.average_daily_consumption == Decimal("2.5")
    assert result.current_stock == 10
    assert result.reorder_point == Decimal("12.5")
    assert result.target_stock == Decimal("37.5")
    assert result.reorder_required is True
    assert result.suggested_order_quantity == 28


def test_target_stock_formula():
    dataset = make_dataset(
        opening_stock=1000,
        opening_date=date(2026, 10, 15),
        safety_stock=100,
        lead_time_days=12,
        target_coverage_days=20,
        movements=(movement(date(2026, 10, 20), "OUT", 300),),
    )

    result = calculate_inventory(
        dataset, date(2026, 11, 13), today=date(2026, 11, 13)
    )

    assert result.consumption_coverage_days == 30
    assert result.average_daily_consumption == Decimal(10)
    assert result.current_stock == 700
    assert result.reorder_point == Decimal(220)
    assert result.target_stock == Decimal(420)
    assert result.reorder_required is False


def test_movement_before_opening_date_is_rejected():
    dataset = make_dataset(
        movements=(movement(date(2026, 9, 30), "IN", 10),)
    )

    with pytest.raises(ValueError, match="before the opening stock date"):
        calculate_inventory(
            dataset, date(2026, 10, 5), today=date(2026, 10, 5)
        )


def test_report_date_before_opening_date_is_rejected():
    dataset = make_dataset(opening_date=date(2026, 10, 10))

    with pytest.raises(ValueError, match="before the opening stock date"):
        calculate_inventory(
            dataset, date(2026, 10, 5), today=date(2026, 10, 5)
        )


def test_historical_report_excludes_current_open_orders():
    dataset = make_dataset(
        opening_stock=1000,
        safety_stock=100,
        lead_time_days=12,
        movements=(movement(date(2026, 10, 5), "OUT", 100),),
        open_orders=(order("PO-001", 50, date(2026, 10, 5)),),
    )

    result = calculate_inventory(
        dataset, date(2026, 10, 10), today=date(2026, 10, 20)
    )

    assert result.current_stock == 900
    assert result.average_daily_consumption == Decimal(10)
    assert result.reorder_point == Decimal(220)
    assert result.target_stock == Decimal(420)
    assert result.total_open_order_quantity == 0
    assert result.inventory_position == 900
    assert result.overdue_order_count == 0
    assert result.reorder_required is False
    assert result.suggested_order_quantity == 0
    assert result.is_historical_report is True
    assert result.replenishment_supported is False
    assert result.replenishment_note


def test_demo_workbook_calculation(demo_path):
    validation = validate_excel_file(
        demo_path,
        source_kind=DEMO_SOURCE,
    )
    assert validation.is_valid
    assert validation.dataset is not None

    result = calculate_inventory(
        validation.dataset,
        date(2026, 11, 13),
        today=date(2026, 11, 13),
    )

    assert result.current_stock == 449
    assert result.total_in == 325
    assert result.total_out == 376
    assert result.consumption_coverage_days == 30
    assert float(result.average_daily_consumption) == pytest.approx(281 / 30)
    assert float(result.reorder_point) == pytest.approx(212.4)
    assert float(result.target_stock) == pytest.approx(399.7333333333)
    assert result.total_open_order_quantity == 300
    assert result.inventory_position == 749
    assert result.overdue_order_count == 0
    assert result.reorder_required is False
    assert result.suggested_order_quantity == 0
    assert result.negative_stock_warning is False
