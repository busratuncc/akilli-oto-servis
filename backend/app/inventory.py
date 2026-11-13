from decimal import Decimal, ROUND_HALF_UP

QUANTITY = Decimal("0.01")
MONEY = Decimal("0.01")


class InsufficientStockError(ValueError):
    pass


def quantity(value: Decimal | int | str) -> Decimal:
    return Decimal(value).quantize(QUANTITY, rounding=ROUND_HALF_UP)


def apply_movement(
    current: Decimal,
    movement_type: str,
    requested_quantity: Decimal,
) -> tuple[Decimal, Decimal]:
    amount = quantity(requested_quantity)
    if amount <= Decimal("0"):
        raise ValueError("Stok hareket miktarı sıfırdan büyük olmalıdır")
    if movement_type == "stock_in":
        delta = amount
    elif movement_type in {"stock_out", "invoice_sale"}:
        delta = -amount
    else:
        raise ValueError("Desteklenmeyen stok hareketi")
    balance = quantity(current + delta)
    if balance < Decimal("0"):
        raise InsufficientStockError("Yetersiz stok")
    return delta, balance


def inventory_values(parts: list[object]) -> tuple[Decimal, Decimal]:
    cost = sum(
        (part.stock_quantity * part.purchase_price for part in parts),
        Decimal("0"),
    ).quantize(MONEY, rounding=ROUND_HALF_UP)
    sale = sum(
        (part.stock_quantity * part.sale_price for part in parts),
        Decimal("0"),
    ).quantize(MONEY, rounding=ROUND_HALF_UP)
    return cost, sale
