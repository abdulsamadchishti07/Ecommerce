from decimal import Decimal
from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from django.urls import reverse

from apps.cart.cart import Cart
from apps.orders.forms import CheckoutForm
from apps.orders.models import Order, OrderItem, generate_order_number
from apps.products.models import Category, Product, ProductVariant

User = get_user_model()


class OrderModelTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="testuser@example.com",
            password="password123",
            first_name="John",
            last_name="Doe",
        )
        self.category = Category.objects.create(name="Electronics", slug="electronics")
        self.product = Product.objects.create(
            name="Smartphone",
            slug="smartphone",
            category=self.category,
            price=Decimal("499.99"),
        )
        self.variant = ProductVariant.objects.create(
            product=self.product,
            sku="PHONE-BLK-64",
            color="Black",
            size="64GB",
            stock=10,
        )
        self.order = Order.objects.create(
            user=self.user,
            email="testuser@example.com",
            first_name="John",
            last_name="Doe",
            phone="+92 300 1234567",
            street_address="123 Main St",
            city="Lahore",
            state="Punjab",
            postal_code="54000",
            country="PK",
            total_amount=Decimal("499.99"),
            payment_method="COD",
        )
        self.order_item = OrderItem.objects.create(
            order=self.order,
            variant=self.variant,
            product_name="Smartphone",
            variant_info="Color: Black, Size: 64GB",
            price=Decimal("499.99"),
            quantity=1,
        )

    def test_order_number_format(self):
        self.assertTrue(self.order.order_number.startswith("EVO-"))
        self.assertEqual(len(self.order.order_number.split("-")), 3)

    def test_full_name_property(self):
        self.assertEqual(self.order.full_name, "John Doe")

    def test_shipping_address_formatted(self):
        self.assertIn("123 Main St", self.order.shipping_address_formatted)
        self.assertIn("Lahore", self.order.shipping_address_formatted)
        self.assertIn("Punjab", self.order.shipping_address_formatted)
        self.assertIn("54000", self.order.shipping_address_formatted)

    def test_order_str(self):
        self.assertEqual(str(self.order), f"Order #{self.order.order_number} (Pending)")

    def test_order_item_subtotal_and_str(self):
        self.assertEqual(self.order_item.subtotal, Decimal("499.99"))
        self.assertEqual(str(self.order_item), "1x Smartphone (Color: Black, Size: 64GB)")


class CheckoutFormTestCase(TestCase):
    def test_valid_checkout_form(self):
        form_data = {
            "email": "customer@example.com",
            "first_name": "Jane",
            "last_name": "Smith",
            "phone": "+923000000000",
            "street_address": "456 Market Road",
            "city": "Karachi",
            "state": "Sindh",
            "postal_code": "75000",
            "country": "PK",
            "payment_method": "COD",
        }
        form = CheckoutForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_invalid_checkout_form_missing_required_fields(self):
        form_data = {
            "email": "invalid-email",
            "first_name": "",
            "street_address": "",
        }
        form = CheckoutForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn("email", form.errors)
        self.assertIn("first_name", form.errors)
        self.assertIn("street_address", form.errors)


class CheckoutViewTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            email="checkoutuser@example.com",
            password="password123",
            first_name="Ali",
            last_name="Khan",
        )
        self.category = Category.objects.create(name="Fashion", slug="fashion")
        self.product = Product.objects.create(
            name="Jacket",
            slug="jacket",
            category=self.category,
            price=Decimal("99.99"),
        )
        self.variant = ProductVariant.objects.create(
            product=self.product,
            sku="JKT-BLK-L",
            color="Black",
            size="L",
            stock=5,
        )

    def test_checkout_redirects_if_cart_is_empty(self):
        response = self.client.get(reverse("orders:checkout"))
        self.assertRedirects(response, reverse("cart:cart_detail"))

    def test_successful_checkout_creates_order_and_reduces_stock(self):
        # Add item to session cart
        session = self.client.session
        session.save()
        
        # Add to cart via Cart service
        class DummyRequest:
            def __init__(self, client):
                self.user = User.objects.get(id=self.user_id) if hasattr(self, 'user_id') else get_user_model().objects.none()
                self.session = client.session

        request = DummyRequest(self.client)
        request.user = self.user
        request.session = self.client.session
        cart = Cart(request)
        cart.add(self.variant, quantity=2)

        self.client.force_login(self.user)
        form_data = {
            "email": "checkoutuser@example.com",
            "first_name": "Ali",
            "last_name": "Khan",
            "phone": "+923001112233",
            "street_address": "789 Blue Area",
            "city": "Islamabad",
            "state": "ICT",
            "postal_code": "44000",
            "country": "PK",
            "payment_method": "COD",
        }
        response = self.client.post(reverse("orders:checkout"), data=form_data)
        
        self.assertEqual(Order.objects.count(), 1)
        order = Order.objects.first()
        self.assertRedirects(response, reverse("orders:order_confirmation", kwargs={"order_number": order.order_number}))
        
        # Verify order details
        self.assertEqual(order.user, self.user)
        self.assertEqual(order.total_amount, Decimal("199.98"))
        self.assertEqual(order.items.count(), 1)

        # Verify stock reduced
        self.variant.refresh_from_db()
        self.assertEqual(self.variant.stock, 3)

        # Verify cart cleared
        cart = Cart(request)
        self.assertEqual(len(cart), 0)

    def test_checkout_fails_if_stock_insufficient(self):
        self.client.force_login(self.user)
        
        class DummyRequest:
            def __init__(self, client, user):
                self.user = user
                self.session = client.session

        request = DummyRequest(self.client, self.user)
        cart = Cart(request)
        cart.add(self.variant, quantity=10) # Request more than 5 in stock

        form_data = {
            "email": "checkoutuser@example.com",
            "first_name": "Ali",
            "last_name": "Khan",
            "phone": "+923001112233",
            "street_address": "789 Blue Area",
            "city": "Islamabad",
            "state": "ICT",
            "postal_code": "44000",
            "country": "PK",
            "payment_method": "COD",
        }
        response = self.client.post(reverse("orders:checkout"), data=form_data)
        self.assertRedirects(response, reverse("cart:cart_detail"))
        self.assertEqual(Order.objects.count(), 0)
        self.variant.refresh_from_db()
        self.assertEqual(self.variant.stock, 5) # Stock unchanged


class OrderConfirmationViewTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            email="user1@example.com", password="password123"
        )
        self.other_user = User.objects.create_user(
            email="user2@example.com", password="password123"
        )
        self.order = Order.objects.create(
            user=self.user,
            email="user1@example.com",
            first_name="User",
            last_name="One",
            street_address="Address 1",
            city="City 1",
            postal_code="10000",
            total_amount=Decimal("100.00"),
        )

    def test_owner_can_view_order_confirmation(self):
        self.client.force_login(self.user)
        response = self.client.get(
            reverse("orders:order_confirmation", kwargs={"order_number": self.order.order_number})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.order.order_number)

    def test_other_user_cannot_view_order_confirmation(self):
        self.client.force_login(self.other_user)
        response = self.client.get(
            reverse("orders:order_confirmation", kwargs={"order_number": self.order.order_number})
        )
        self.assertRedirects(response, reverse("products:home"))


class OrderHistoryViewTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            email="historyuser@example.com", password="password123"
        )

    def test_unauthenticated_user_redirected_to_login(self):
        response = self.client.get(reverse("orders:order_history"))
        self.assertEqual(response.status_code, 302)

    def test_authenticated_user_can_view_order_history(self):
        self.client.force_login(self.user)
        Order.objects.create(
            user=self.user,
            email="historyuser@example.com",
            first_name="History",
            last_name="User",
            street_address="Addr",
            city="City",
            postal_code="12345",
            total_amount=Decimal("50.00"),
        )
        response = self.client.get(reverse("orders:order_history"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "50.00")

