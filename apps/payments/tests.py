from decimal import Decimal
import json
from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from django.urls import reverse

from apps.orders.models import Order
from apps.payments.forms import BankTransferForm
from apps.payments.models import Payment, generate_transaction_id
from apps.products.models import Category, Product, ProductVariant

User = get_user_model()


class PaymentModelTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="paymentuser@example.com", password="password123"
        )
        self.order = Order.objects.create(
            user=self.user,
            email="paymentuser@example.com",
            first_name="Payment",
            last_name="Tester",
            street_address="Street 1",
            city="Lahore",
            postal_code="54000",
            total_amount=Decimal("150.00"),
            payment_method="CARD",
        )
        self.payment = Payment.objects.create(
            order=self.order,
            payment_method="CARD",
            amount=Decimal("150.00"),
            status="PENDING",
        )

    def test_payment_creation_and_str(self):
        self.assertTrue(self.payment.transaction_id.startswith("TXN-"))
        self.assertEqual(self.payment.amount, Decimal("150.00"))
        self.assertIn("Pending", str(self.payment))

    def test_mark_as_successful_updates_order(self):
        self.payment.mark_as_successful(transaction_id="TXN-SUCCESS-123")
        self.assertEqual(self.payment.status, "SUCCESSFUL")
        self.assertEqual(self.payment.transaction_id, "TXN-SUCCESS-123")
        
        self.order.refresh_from_db()
        self.assertEqual(self.order.payment_status, "PAID")
        self.assertEqual(self.order.status, "PROCESSING")

    def test_mark_as_failed(self):
        self.payment.mark_as_failed(reason="Insufficient funds")
        self.assertEqual(self.payment.status, "FAILED")
        self.assertIn("Insufficient funds", self.payment.notes)

    def test_payment_data_encryption_at_rest(self):
        self.payment.bank_reference = "TRX-ENCRYPTED-REF-99"
        self.payment.provider_response = {"client_secret": "secret_12345", "status": "succeeded"}
        self.payment.save()

        self.payment.refresh_from_db()

        # Direct database column checks: must NOT store plain text
        self.assertNotEqual(self.payment.encrypted_bank_reference, "TRX-ENCRYPTED-REF-99")
        self.assertNotIn("TRX-ENCRYPTED-REF-99", self.payment.encrypted_bank_reference)
        self.assertNotIn("secret_12345", self.payment.encrypted_provider_response)

        # Transparent properties: must decrypt cleanly
        self.assertEqual(self.payment.bank_reference, "TRX-ENCRYPTED-REF-99")
        self.assertEqual(self.payment.provider_response.get("status"), "succeeded")
        # Verify sanitization redacted the secret
        self.assertEqual(self.payment.provider_response.get("client_secret"), "[ENCRYPTED/REDACTED]")


class ProcessPaymentViewTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            email="carduser@example.com", password="password123"
        )
        self.order = Order.objects.create(
            user=self.user,
            email="carduser@example.com",
            first_name="Card",
            last_name="User",
            street_address="Card Addr",
            city="Karachi",
            postal_code="75000",
            total_amount=Decimal("200.00"),
            payment_method="CARD",
        )

    def test_process_payment_get_renders_card_portal(self):
        self.client.force_login(self.user)
        response = self.client.get(
            reverse("payments:process", kwargs={"order_number": self.order.order_number})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Complete Your Payment")

    def test_process_payment_post_simulates_success(self):
        self.client.force_login(self.user)
        post_data = {"simulate_success": "1"}
        response = self.client.post(
            reverse("payments:process", kwargs={"order_number": self.order.order_number}),
            data=post_data,
        )
        self.assertRedirects(
            response,
            reverse("orders:order_confirmation", kwargs={"order_number": self.order.order_number}),
        )
        
        self.order.refresh_from_db()
        self.assertEqual(self.order.payment_status, "PAID")
        self.assertEqual(self.order.status, "PROCESSING")

    def test_process_redirects_if_already_paid(self):
        self.client.force_login(self.user)
        self.order.payment_status = "PAID"
        self.order.save()
        response = self.client.get(
            reverse("payments:process", kwargs={"order_number": self.order.order_number})
        )
        self.assertRedirects(
            response,
            reverse("orders:order_confirmation", kwargs={"order_number": self.order.order_number}),
        )


class BankTransferViewTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            email="bankuser@example.com", password="password123"
        )
        self.order = Order.objects.create(
            user=self.user,
            email="bankuser@example.com",
            first_name="Bank",
            last_name="User",
            street_address="Bank St",
            city="Islamabad",
            postal_code="44000",
            total_amount=Decimal("350.00"),
            payment_method="BANK",
        )

    def test_bank_transfer_get(self):
        self.client.force_login(self.user)
        response = self.client.get(
            reverse("payments:bank_transfer", kwargs={"order_number": self.order.order_number})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Direct Bank Transfer")
        self.assertContains(response, "EvoCart Global Bank")

    def test_bank_transfer_post_submits_reference(self):
        self.client.force_login(self.user)
        post_data = {
            "bank_reference": "TRX-9988776655",
            "notes": "Transferred via mobile banking app.",
        }
        response = self.client.post(
            reverse("payments:bank_transfer", kwargs={"order_number": self.order.order_number}),
            data=post_data,
        )
        self.assertRedirects(
            response,
            reverse("orders:order_confirmation", kwargs={"order_number": self.order.order_number}),
        )
        
        payment = Payment.objects.get(order=self.order)
        self.assertEqual(payment.bank_reference, "TRX-9988776655")
        self.assertEqual(payment.status, "PROCESSING")


class StripeWebhookAndStatusTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.order = Order.objects.create(
            email="webhook@example.com",
            first_name="Webhook",
            last_name="Test",
            street_address="Street 2",
            city="City",
            postal_code="10000",
            total_amount=Decimal("80.00"),
            payment_method="CARD",
        )

    def test_stripe_webhook_succeeded(self):
        payload = {
            "type": "payment_intent.succeeded",
            "data": {
                "object": {
                    "id": "pi_test_12345",
                    "metadata": {"order_number": self.order.order_number},
                }
            },
        }
        response = self.client.post(
            reverse("payments:stripe_webhook"),
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        
        self.order.refresh_from_db()
        self.assertEqual(self.order.payment_status, "PAID")
        self.assertEqual(self.order.status, "PROCESSING")

    def test_payment_status_api(self):
        response = self.client.get(
            reverse("payments:payment_status", kwargs={"order_number": self.order.order_number})
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["order_number"], self.order.order_number)
        self.assertIn("payment_status", data)
