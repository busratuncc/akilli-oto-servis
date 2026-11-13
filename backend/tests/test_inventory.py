from decimal import Decimal
from types import SimpleNamespace

import pytest

from app import inventory


def test_stock_in_increases_balance():
    delta, balance = inventory.apply_movement(
        Decimal("4.50"),
        "stock_in",
        Decimal("2.25"),
    )
    assert delta == Decimal("2.25")
    assert balance == Decimal("6.75")


def test_stock_out_decreases_balance():
    delta, balance = inventory.apply_movement(
        Decimal("10"),
        "stock_out",
        Decimal("3"),
    )
    assert delta == Decimal("-3.00")
    assert balance == Decimal("7.00")


def test_invoice_sale_cannot_make_stock_negative():
    with pytest.raises(inventory.InsufficientStockError):
        inventory.apply_movement(
            Decimal("2"),
            "invoice_sale",
            Decimal("3"),
        )


def test_inventory_values_use_current_quantity():
    parts = [
        SimpleNamespace(
            stock_quantity=Decimal("2"),
            purchase_price=Decimal("100"),
            sale_price=Decimal("150"),
        ),
        SimpleNamespace(
            stock_quantity=Decimal("1.5"),
            purchase_price=Decimal("20"),
            sale_price=Decimal("40"),
        ),
    ]
    cost, sale = inventory.inventory_values(parts)
    assert cost == Decimal("230.00")
    assert sale == Decimal("360.00")
