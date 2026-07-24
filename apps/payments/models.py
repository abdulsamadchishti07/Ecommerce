import uuid
from decimal import Decimal
from django.core.validators import MinValueValidator
from django.db import models

from apps.core.models import TimeStampField
from apps.orders.models import Order
from .utils import encrypt_payment_data, decrypt_payment_data, sanitize_payment_data


def generate_transaction_id():
    """Generate a unique transaction reference like TXN-20260724-X9Y8Z7."""
    import datetime
    today_str = datetime.date.today().strftime("%Y%m%d")
    short_uuid = uuid.uuid4().hex[:6].upper()
    return f"TXN-{today_str}-{short_uuid}"


class Payment(TimeStampField):
    STATUS_CHOICES = (
        ("PENDING", "Pending"),
        ("PROCESSING", "Processing"),
        ("SUCCESSFUL", "Successful"),
        ("FAILED", "Failed"),
        ("REFUNDED", "Refunded"),
    )

    PAYMENT_METHOD_CHOICES = (
        ("COD", "Cash on Delivery"),
        ("CARD", "Credit / Debit Card"),
        ("BANK", "Direct Bank Transfer"),
    )

    order = models.OneToOneField(
        Order,
        on_delete=models.CASCADE,
        related_name="payment",
    )

    transaction_id = models.CharField(
        max_length=100,
        unique=True,
        default=generate_transaction_id,
        editable=False,
    )

    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHOD_CHOICES,
        default="COD",
    )

    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="PENDING",
    )

    # Encrypted fields stored at rest in database
    encrypted_bank_reference = models.TextField(blank=True, help_text="AES-256 Encrypted Bank Reference")
    encrypted_provider_response = models.TextField(blank=True, help_text="AES-256 Encrypted Stripe/Provider Response")

    # Bank transfer receipt file
    bank_receipt = models.ImageField(upload_to="receipts/", blank=True, null=True)

    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Payment {self.transaction_id} — {self.get_status_display()} (Order #{self.order.order_number})"

    # --- Property wrappers for AES-256 transparent encryption/decryption ---

    @property
    def bank_reference(self):
        return decrypt_payment_data(self.encrypted_bank_reference)

    @bank_reference.setter
    def bank_reference(self, value):
        self.encrypted_bank_reference = encrypt_payment_data(value)

    @property
    def provider_response(self):
        return decrypt_payment_data(self.encrypted_provider_response)

    @provider_response.setter
    def provider_response(self, value):
        sanitized_value = sanitize_payment_data(value)
        self.encrypted_provider_response = encrypt_payment_data(sanitized_value)

    @property
    def is_successful(self):
        return self.status == "SUCCESSFUL"

    def mark_as_successful(self, transaction_id=None, provider_response=None):
        """Mark payment as successful and update associated order status."""
        self.status = "SUCCESSFUL"
        if transaction_id:
            self.transaction_id = transaction_id
        if provider_response:
            self.provider_response = provider_response
        self.save()

        # Update associated order payment_status and order status
        self.order.payment_status = "PAID"
        if self.order.status == "PENDING":
            self.order.status = "PROCESSING"
        self.order.save(update_fields=["payment_status", "status", "updated_at"])

    def mark_as_failed(self, reason=None, provider_response=None):
        """Mark payment as failed."""
        self.status = "FAILED"
        if reason:
            self.notes = f"Failure reason: {reason}"
        if provider_response:
            self.provider_response = provider_response
        self.save()
