from decimal import Decimal

import pytest

from app import finance, schemas


def line(item_type: str, description: str, quantity: str, unit_price: str):
    return schemas.InvoiceLineCreate(
        item_type=item_type,
        description=description,
        quantity=Decimal(quantity),
        unit_price=Decimal(unit_price),
    )


def test_calculates_line_totals_discount_tax_and_total():
    totals, subtotal, tax, total = finance.calculate_invoice(
        [
            line("part", "Yağ filtresi", "2", "125.50"),
            line("labor", "Bakım işçiliği", "1", "500"),
        ],
        Decimal("50"),
        Decimal("20"),
    )

    assert totals == [Decimal("251.00"), Decimal("500.00")]
    assert subtotal == Decimal("751.00")
    assert tax == Decimal("140.20")
    assert total == Decimal("841.20")


def test_rounds_each_line_to_two_decimal_places():
    unvalidated_line = schemas.InvoiceLineCreate.model_construct(
        item_type="other",
        description="Sarf malzeme",
        quantity=Decimal("3"),
        unit_price=Decimal("0.335"),
    )
    totals, subtotal, tax, total = finance.calculate_invoice(
        [unvalidated_line],
        Decimal("0"),
        Decimal("0"),
    )

    assert totals == [Decimal("1.01")]
    assert subtotal == Decimal("1.01")
    assert tax == Decimal("0.00")
    assert total == Decimal("1.01")


def test_rejects_discount_larger_than_subtotal():
    with pytest.raises(finance.FinanceValidationError):
        finance.calculate_invoice(
            [line("labor", "Kontrol", "1", "100")],
            Decimal("101"),
            Decimal("20"),
        )
