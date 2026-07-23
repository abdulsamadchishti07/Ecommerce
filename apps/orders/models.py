import uuid
from decimal import Decimal
from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django_countries.fields import CountryField

from apps.core.models import TimeStampField
from apps.products.models import ProductVariant


def generate_order_number():
    """Generate a unique human-readable order number like EVO-20260722-A1B2."""
    import datetime
    today_str = datetime.date.today().strftime("%Y%m%d")
    short_uuid = uuid.uuid4().hex[:6].upper()
    return f"EVO-{today_str}-{short_uuid}"


class Order(TimeStampField):
    STATUS_CHOICES = (
        ("PENDING", "Pending"),
        ("PROCESSING", "Processing"),
        ("SHIPPED", "Shipped"),
        ("DELIVERED", "Delivered"),
        ("CANCELLED", "Cancelled"),
    )

    PAYMENT_STATUS_CHOICES = (
        ("UNPAID", "Unpaid"),
        ("PAID", "Paid"),
        ("REFUNDED", "Refunded"),
    )

    PAYMENT_METHOD_CHOICES = (
        ("COD", "Cash on Delivery"),
        ("CARD", "Credit / Debit Card"),
        ("BANK", "Direct Bank Transfer"),
    )

    order_number = models.CharField(
        max_length=50,
        unique=True,
        default=generate_order_number,
        editable=False,
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="orders",
        null=True,
        blank=True,
    )

    # Customer Contact
    email = models.EmailField()
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    phone = models.CharField(max_length=20, blank=True)

    # Shipping Address
    street_address = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=20)
    country = CountryField(default="PK")

    # Order Totals & Status
    total_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="PENDING",
    )

    payment_status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default="UNPAID",
    )

    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHOD_CHOICES,
        default="COD",
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Order #{self.order_number} ({self.get_status_display()})"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def shipping_address_formatted(self):
        parts = [self.street_address, self.city, self.state, self.postal_code]
        address = ", ".join(p for p in parts if p)
        if self.country:
            address += f", {self.country.name}"
        return address


class OrderItem(TimeStampField):
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="items",
    )

    variant = models.ForeignKey(
        ProductVariant,
        on_delete=models.PROTECT,
        related_name="order_items",
    )

    # Snapshots at order creation time
    product_name = models.CharField(max_length=150)
    variant_info = models.CharField(max_length=100, blank=True)

    price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
    )

    quantity = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(1)],
    )

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.quantity}x {self.product_name} ({self.variant_info})"

    @property
    def subtotal(self):
        return self.price * self.quantity
