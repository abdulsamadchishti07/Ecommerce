from decimal import Decimal
from django.contrib.auth import get_user_model
from django.test import TestCase, RequestFactory
from django.contrib.sessions.middleware import SessionMiddleware

from apps.products.models import Category, Product, ProductVariant
from apps.cart.models import Cart as CartModel, CartItem
from apps.cart.cart import Cart

User = get_user_model()


class CartSystemTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(email="test@example.com", password="password123")
        self.category = Category.objects.create(name="Mobile", slug="mobile")
        self.product = Product.objects.create(
            name="Galaxy A12",
            slug="galaxy-a12",
            price=Decimal("20000.00"),
            category=self.category,
        )
        self.variant_1 = ProductVariant.objects.create(
            product=self.product,
            sku="SKU-A12-W",
            color="White",
            stock=10,
        )
        self.variant_2 = ProductVariant.objects.create(
            product=self.product,
            sku="SKU-A12-B",
            color="Black",
            stock=5,
        )

    def _get_request(self, user=None):
        request = self.factory.get("/")
        middleware = SessionMiddleware(lambda r: None)
        middleware.process_request(request)
        request.session.save()
        request.user = user or self.user
        return request

    def test_cart_creation_for_guest(self):
        request = self.factory.get("/")
        middleware = SessionMiddleware(lambda r: None)
        middleware.process_request(request)
        request.session.save()
        from django.contrib.auth.models import AnonymousUser
        request.user = AnonymousUser()

        cart = Cart(request)
        self.assertIsNotNone(cart.cart_obj)
        self.assertIsNone(cart.cart_obj.user)
        self.assertEqual(cart.cart_obj.session_key, request.session.session_key)

    def test_cart_add_and_totals(self):
        request = self._get_request(user=self.user)
        cart = Cart(request)
        
        cart.add(self.variant_1, quantity=2)
        self.assertEqual(len(cart), 2)
        self.assertEqual(cart.total, Decimal("40000.00"))

        cart.add(self.variant_2, quantity=1)
        self.assertEqual(len(cart), 3)
        self.assertEqual(cart.total, Decimal("60000.00"))

    def test_cart_update_and_remove(self):
        request = self._get_request(user=self.user)
        cart = Cart(request)

        cart.add(self.variant_1, quantity=1)
        cart.update(self.variant_1, quantity=5)
        self.assertEqual(len(cart), 5)

        cart.remove(self.variant_1)
        self.assertEqual(len(cart), 0)

    def test_guest_to_user_cart_merge(self):
        # 1. Create a guest cart
        guest_request = self.factory.get("/")
        middleware = SessionMiddleware(lambda r: None)
        middleware.process_request(guest_request)
        guest_request.session.save()
        from django.contrib.auth.models import AnonymousUser
        guest_request.user = AnonymousUser()

        guest_cart = Cart(guest_request)
        guest_cart.add(self.variant_1, quantity=2)
        session_key = guest_request.session.session_key

        # 2. Login the user with the same session_key
        user_request = self.factory.get("/")
        user_request.session = guest_request.session
        user_request.user = self.user

        user_cart = Cart(user_request)
        self.assertEqual(user_cart.cart_obj.user, self.user)
        self.assertEqual(len(user_cart), 2)
        self.assertEqual(user_cart.total, Decimal("40000.00"))
        
        # Verify guest cart in DB was cleaned up
        self.assertFalse(CartModel.objects.filter(session_key=session_key, user__isnull=True).exists())
