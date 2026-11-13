from decimal import Decimal, ROUND_HALF_UP

from app import models, schemas

MONEY = Decimal("0.01")


class FinanceValidationError(ValueError):
    pass


def money(value: Decimal | int | str) -> Decimal:
    return Decimal(value).quantize(MONEY, rounding=ROUND_HALF_UP)


def calculate_invoice(
    items: list[schemas.InvoiceLineCreate],
    discount_amount: Decimal,
    tax_rate: Decimal,
) -> tuple[list[Decimal], Decimal, Decimal, Decimal]:
    line_totals = [money(item.quantity * item.unit_price) for item in items]
    subtotal = money(sum(line_totals, Decimal("0")))
    discount = money(discount_amount)
    if discount > subtotal:
        raise FinanceValidationError("İndirim ara toplamdan büyük olamaz")
    taxable_amount = subtotal - discount
    tax_amount = money(taxable_amount * tax_rate / Decimal("100"))
    total_amount = money(taxable_amount + tax_amount)
    return line_totals, subtotal, tax_amount, total_amount


def paid_amount(invoice: models.Invoice) -> Decimal:
    return money(sum((payment.amount for payment in invoice.payments), Decimal("0")))


def balance_due(invoice: models.Invoice) -> Decimal:
    return max(money(invoice.total_amount - paid_amount(invoice)), Decimal("0.00"))


def update_status(invoice: models.Invoice) -> None:
    paid = paid_amount(invoice)
    if paid <= Decimal("0"):
        invoice.status = "issued"
    elif paid >= invoice.total_amount:
        invoice.status = "paid"
    else:
        invoice.status = "partially_paid"


def to_read(invoice: models.Invoice) -> schemas.InvoiceRead:
    paid = paid_amount(invoice)
    return schemas.InvoiceRead(
        id=invoice.id,
        work_order_id=invoice.work_order_id,
        invoice_number=invoice.invoice_number,
        status=invoice.status,
        currency=invoice.currency,
        subtotal=invoice.subtotal,
        discount_amount=invoice.discount_amount,
        tax_rate=invoice.tax_rate,
        tax_amount=invoice.tax_amount,
        total_amount=invoice.total_amount,
        paid_amount=paid,
        balance_due=max(money(invoice.total_amount - paid), Decimal("0.00")),
        notes=invoice.notes,
        issued_at=invoice.issued_at,
        due_date=invoice.due_date,
        created_at=invoice.created_at,
        line_items=[schemas.InvoiceLineRead.model_validate(item) for item in invoice.line_items],
        payments=[schemas.PaymentRead.model_validate(item) for item in invoice.payments],
    )
