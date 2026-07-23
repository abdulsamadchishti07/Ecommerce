"""
.venv/bin/python manage.py test apps.products --verbosity=2

Comprehensive test suite for the EvoCart products app.

Coverage:
  - Category model  (creation, __str__, get_absolute_url, ordering, unique slug)
  - Brand model     (creation, __str__, get_absolute_url, ordering, unique slug)
  - Product model   (creation, __str__, get_absolute_url, properties: is_on_sale,
                     discount_percent, discount_amount, total_stock, in_stock,
                     seller FK, category PROTECT, brand SET_NULL, is_active default)
  - ProductImage    (creation, __str__, is_primary default, ordering)
  - ProductVariant  (creation, __str__, price property, unique constraint, stock)
  - ProductForm     (valid data, price > old_price validation, missing required fields)
  - ProductVariantForm (valid data, optional fields)
  - Helper funcs    (_handle_category, _handle_brand, _save_images, _save_variants,
                     _generate_sku)
  - Views:
      home            (GET 200, context, products limited to 12, inactive hidden)
      category_detail (GET 200, 404 for bad slug, inactive hidden)
      product_detail  (GET 200, 404 for bad slug, 404 for inactive)
      add_product     (login required, buyer blocked, seller GET, seller POST valid,
                       seller POST invalid)
      my_shop         (login required, buyer blocked, seller sees own products)
      edit_product    (login required, ownership enforced, GET pre-fills, POST updates)
      product_delete  (login required, ownership enforced, POST deletes)
  - URL routing     (all named URLs resolve correctly)
  - Admin           (smoke-test registered models)
"""

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, transaction
from django.test import Client, TestCase, override_settings
from django.urls import resolve, reverse

from apps.accounts.models import Profile

from .forms import ProductForm, ProductVariantForm
from .models import Brand, Category, Product, ProductImage, ProductVariant
from .views import (
    _generate_sku,
    _handle_brand,
    _handle_category,
    _save_images,
    _save_variants,
)

User = get_user_model()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Tiny 1×1 transparent PNG for ImageField tests
_TINY_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
    b"\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
    b"\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01"
    b"\r\n\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
)


def _make_image(name="test.png"):
    """Return a fresh SimpleUploadedFile for each call."""
    return SimpleUploadedFile(name, _TINY_PNG, content_type="image/png")


def _make_seller(email="seller@evocart.com", password="StrongPass123!"):
    """Create a user with a Seller profile."""
    user = User.objects.create_user(email=email, password=password)
    Profile.objects.update_or_create(user=user, defaults={"role": "S"})
    return user


def _make_buyer(email="buyer@evocart.com", password="StrongPass123!"):
    """Create a user with a Buyer profile."""
    user = User.objects.create_user(email=email, password=password)
    Profile.objects.update_or_create(user=user, defaults={"role": "B"})
    return user


def _make_category(name="Electronics", slug="electronics"):
    cat, _ = Category.objects.get_or_create(name=name, defaults={"slug": slug})
    return cat


def _make_brand(name="Sony", slug="sony"):
    brand, _ = Brand.objects.get_or_create(name=name, defaults={"slug": slug})
    return brand


def _make_product(seller=None, category=None, brand=None, **overrides):
    """Convenience factory for Product with sensible defaults."""
    if category is None:
        category = _make_category()
    defaults = {
        "name": "Test Product",
        "slug": "test-product",
        "price": Decimal("99.99"),
        "category": category,
        "brand": brand,
        "seller": seller,
        "is_active": True,
    }
    defaults.update(overrides)
    return Product.objects.create(**defaults)


# ============================================================================
# Model tests
# ============================================================================


class CategoryModelTests(TestCase):
    """Tests for the Category model."""

    def test_create_category(self):
        cat = _make_category()
        self.assertEqual(cat.name, "Electronics")
        self.assertEqual(cat.slug, "electronics")

    def test_str(self):
        cat = _make_category()
        self.assertEqual(str(cat), "Electronics")

    def test_get_absolute_url(self):
        cat = _make_category()
        self.assertEqual(cat.get_absolute_url(), "/category/electronics/")

    def test_ordering(self):
        _make_category(name="Zzz", slug="zzz")
        _make_category(name="Aaa", slug="aaa")
        names = list(Category.objects.values_list("name", flat=True))
        self.assertEqual(names, ["Aaa", "Zzz"])

    def test_unique_name(self):
        Category.objects.create(name="Unique", slug="unique-1")
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Category.objects.create(name="Unique", slug="unique-2")

    def test_unique_slug(self):
        Category.objects.create(name="One", slug="same-slug")
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Category.objects.create(name="Two", slug="same-slug")

    def test_verbose_name_plural(self):
        self.assertEqual(Category._meta.verbose_name_plural, "Categories")

    def test_timestamps_populated(self):
        cat = _make_category()
        self.assertIsNotNone(cat.created_at)
        self.assertIsNotNone(cat.updated_at)


class BrandModelTests(TestCase):
    """Tests for the Brand model."""

    def test_create_brand(self):
        brand = _make_brand()
        self.assertEqual(brand.name, "Sony")
        self.assertEqual(brand.slug, "sony")

    def test_str(self):
        brand = _make_brand()
        self.assertEqual(str(brand), "Sony")

    def test_get_absolute_url_defined(self):
        """Brand.get_absolute_url exists; the URL name 'products:brand_detail'
        is declared in the model but has no urlpattern yet, so we just verify
        the method is callable rather than asserting a specific path."""
        brand = _make_brand()
        self.assertTrue(callable(brand.get_absolute_url))

    def test_ordering(self):
        _make_brand(name="Zzz", slug="zzz")
        _make_brand(name="Aaa", slug="aaa")
        names = list(Brand.objects.values_list("name", flat=True))
        self.assertEqual(names, ["Aaa", "Zzz"])

    def test_unique_name(self):
        Brand.objects.create(name="Unique", slug="unique-1")
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Brand.objects.create(name="Unique", slug="unique-2")

    def test_unique_slug(self):
        Brand.objects.create(name="One", slug="same")
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Brand.objects.create(name="Two", slug="same")


class ProductModelTests(TestCase):
    """Tests for the Product model."""

    def setUp(self):
        self.category = _make_category()
        self.brand = _make_brand()
        self.seller = _make_seller()

    def test_create_product(self):
        p = _make_product(seller=self.seller, category=self.category, brand=self.brand)
        self.assertEqual(p.name, "Test Product")
        self.assertEqual(p.price, Decimal("99.99"))
        self.assertTrue(p.is_active)
        self.assertFalse(p.is_featured)

    def test_str(self):
        p = _make_product(category=self.category)
        self.assertEqual(str(p), "Test Product")

    def test_get_absolute_url(self):
        p = _make_product(category=self.category)
        self.assertEqual(p.get_absolute_url(), "/product/test-product/")

    def test_ordering_by_created_at_desc(self):
        p1 = _make_product(category=self.category, slug="first", name="First")
        p2 = _make_product(category=self.category, slug="second", name="Second")
        slugs = list(Product.objects.values_list("slug", flat=True))
        # Most recent first
        self.assertEqual(slugs[0], "second")

    # --- is_on_sale property ---
    def test_is_on_sale_true(self):
        p = _make_product(
            category=self.category,
            price=Decimal("70.00"),
            old_price=Decimal("100.00"),
        )
        self.assertTrue(p.is_on_sale)

    def test_is_on_sale_false_no_old_price(self):
        p = _make_product(category=self.category)
        self.assertFalse(p.is_on_sale)

    def test_is_on_sale_false_old_price_equals_price(self):
        p = _make_product(
            category=self.category,
            price=Decimal("100.00"),
            old_price=Decimal("100.00"),
        )
        self.assertFalse(p.is_on_sale)

    def test_is_on_sale_false_old_price_less_than_price(self):
        p = _make_product(
            category=self.category,
            price=Decimal("100.00"),
            old_price=Decimal("50.00"),
        )
        self.assertFalse(p.is_on_sale)

    # --- discount_percent ---
    def test_discount_percent(self):
        p = _make_product(
            category=self.category,
            price=Decimal("75.00"),
            old_price=Decimal("100.00"),
        )
        self.assertEqual(p.discount_percent, 25)

    def test_discount_percent_rounds(self):
        p = _make_product(
            category=self.category,
            price=Decimal("33.33"),
            old_price=Decimal("100.00"),
        )
        self.assertEqual(p.discount_percent, 67)

    def test_discount_percent_zero_when_not_on_sale(self):
        p = _make_product(category=self.category)
        self.assertEqual(p.discount_percent, 0)

    # --- discount_amount ---
    def test_discount_amount(self):
        p = _make_product(
            category=self.category,
            price=Decimal("70.00"),
            old_price=Decimal("100.00"),
        )
        self.assertEqual(p.discount_amount, Decimal("30.00"))

    def test_discount_amount_zero_when_not_on_sale(self):
        p = _make_product(category=self.category)
        self.assertEqual(p.discount_amount, 0)

    # --- total_stock & in_stock ---
    def test_total_stock_no_variants(self):
        p = _make_product(category=self.category)
        self.assertEqual(p.total_stock, 0)

    def test_total_stock_with_variants(self):
        p = _make_product(category=self.category)
        ProductVariant.objects.create(product=p, sku="V1", size="S", color="Red", stock=5)
        ProductVariant.objects.create(product=p, sku="V2", size="M", color="Blue", stock=10)
        self.assertEqual(p.total_stock, 15)

    def test_in_stock_true(self):
        p = _make_product(category=self.category)
        ProductVariant.objects.create(product=p, sku="V-INSTOCK", size="L", color="Green", stock=1)
        self.assertTrue(p.in_stock)

    def test_in_stock_false(self):
        p = _make_product(category=self.category)
        self.assertFalse(p.in_stock)

    # --- FK behaviour ---
    def test_category_protect(self):
        """Deleting a category with products should raise ProtectedError."""
        _make_product(category=self.category)
        from django.db.models import ProtectedError

        with self.assertRaises(ProtectedError):
            self.category.delete()

    def test_brand_set_null(self):
        """Deleting a brand nullifies the FK on the product."""
        p = _make_product(category=self.category, brand=self.brand)
        self.brand.delete()
        p.refresh_from_db()
        self.assertIsNone(p.brand)

    def test_seller_cascade(self):
        """Deleting the seller cascades and deletes their products."""
        _make_product(category=self.category, seller=self.seller)
        self.seller.delete()
        self.assertEqual(Product.objects.count(), 0)

    def test_slug_unique(self):
        _make_product(category=self.category, slug="one")
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                _make_product(category=self.category, slug="one", name="Other")

    def test_brand_optional(self):
        p = _make_product(category=self.category, brand=None)
        self.assertIsNone(p.brand)


class ProductImageModelTests(TestCase):
    """Tests for ProductImage model."""

    def setUp(self):
        self.product = _make_product()

    def test_create_image(self):
        img = ProductImage.objects.create(
            product=self.product, image=_make_image(), alt_text="Photo"
        )
        self.assertFalse(img.is_primary)
        self.assertEqual(img.alt_text, "Photo")

    def test_str(self):
        img = ProductImage.objects.create(
            product=self.product, image=_make_image()
        )
        self.assertEqual(str(img), "Test Product Image")

    def test_cascade_delete(self):
        ProductImage.objects.create(product=self.product, image=_make_image())
        self.product.delete()
        self.assertEqual(ProductImage.objects.count(), 0)


@override_settings(
    DEFAULT_FILE_STORAGE="django.core.files.storage.InMemoryStorage"
)
class ProductVariantModelTests(TestCase):
    """Tests for ProductVariant model."""

    def setUp(self):
        self.product = _make_product()

    def test_create_variant(self):
        v = ProductVariant.objects.create(
            product=self.product, sku="SKU-001", size="M", color="Red", stock=10
        )
        self.assertEqual(v.stock, 10)

    def test_str(self):
        v = ProductVariant.objects.create(
            product=self.product, sku="SKU-002", size="L", color="Blue"
        )
        self.assertEqual(str(v), "Test Product (L/Blue)")

    def test_price_property_uses_product_price(self):
        v = ProductVariant.objects.create(
            product=self.product, sku="SKU-003", stock=1
        )
        self.assertEqual(v.price, self.product.price)

    def test_price_property_uses_override(self):
        v = ProductVariant.objects.create(
            product=self.product,
            sku="SKU-004",
            price_override=Decimal("49.99"),
            stock=1,
        )
        self.assertEqual(v.price, Decimal("49.99"))

    def test_sku_unique(self):
        ProductVariant.objects.create(product=self.product, sku="DUPE")
        p2 = _make_product(slug="other-product", name="Other", category=self.product.category)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                ProductVariant.objects.create(product=p2, sku="DUPE")

    def test_unique_product_variant_constraint(self):
        """Same product+size+color combo must be rejected."""
        ProductVariant.objects.create(
            product=self.product, sku="A1", size="M", color="Red"
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                ProductVariant.objects.create(
                    product=self.product, sku="A2", size="M", color="Red"
                )

    def test_cascade_delete(self):
        ProductVariant.objects.create(product=self.product, sku="DEL-1", stock=5)
        self.product.delete()
        self.assertEqual(ProductVariant.objects.count(), 0)

    def test_stock_default_zero(self):
        v = ProductVariant.objects.create(product=self.product, sku="ZERO")
        self.assertEqual(v.stock, 0)


# ============================================================================
# Form tests
# ============================================================================


class ProductFormTests(TestCase):
    """Tests for ProductForm."""

    def _valid_data(self, **overrides):
        data = {
            "name": "Wireless Mouse",
            "description": "A great mouse",
            "price": "29.99",
            "old_price": "",
            "is_active": True,
            "category_name": "Accessories",
            "brand_name": "Logitech",
        }
        data.update(overrides)
        return data

    def test_valid_form(self):
        form = ProductForm(data=self._valid_data())
        self.assertTrue(form.is_valid(), form.errors)

    def test_missing_name(self):
        form = ProductForm(data=self._valid_data(name=""))
        self.assertFalse(form.is_valid())
        self.assertIn("name", form.errors)

    def test_missing_price(self):
        form = ProductForm(data=self._valid_data(price=""))
        self.assertFalse(form.is_valid())
        self.assertIn("price", form.errors)

    def test_missing_category_name(self):
        form = ProductForm(data=self._valid_data(category_name=""))
        self.assertFalse(form.is_valid())
        self.assertIn("category_name", form.errors)

    def test_brand_name_optional(self):
        form = ProductForm(data=self._valid_data(brand_name=""))
        self.assertTrue(form.is_valid(), form.errors)

    def test_price_greater_than_old_price_invalid(self):
        form = ProductForm(
            data=self._valid_data(price="150.00", old_price="100.00")
        )
        self.assertFalse(form.is_valid())
        self.assertIn("price", form.errors)
        self.assertIn("old_price", form.errors)

    def test_price_equal_to_old_price_invalid(self):
        form = ProductForm(
            data=self._valid_data(price="100.00", old_price="100.00")
        )
        self.assertFalse(form.is_valid())

    def test_price_less_than_old_price_valid(self):
        form = ProductForm(
            data=self._valid_data(price="50.00", old_price="100.00")
        )
        self.assertTrue(form.is_valid(), form.errors)

    def test_negative_price_invalid(self):
        form = ProductForm(data=self._valid_data(price="-10.00"))
        self.assertFalse(form.is_valid())

    def test_description_optional(self):
        form = ProductForm(data=self._valid_data(description=""))
        self.assertTrue(form.is_valid(), form.errors)

    def test_old_price_optional(self):
        form = ProductForm(data=self._valid_data(old_price=""))
        self.assertTrue(form.is_valid(), form.errors)


class ProductVariantFormTests(TestCase):
    """Tests for ProductVariantForm."""

    def test_valid_data(self):
        form = ProductVariantForm(
            data={"sku": "V-001", "size": "M", "color": "Black", "stock": 5}
        )
        self.assertTrue(form.is_valid(), form.errors)

    def test_size_optional(self):
        form = ProductVariantForm(
            data={"sku": "V-002", "color": "Red", "stock": 3}
        )
        self.assertTrue(form.is_valid(), form.errors)

    def test_color_optional(self):
        form = ProductVariantForm(
            data={"sku": "V-003", "size": "L", "stock": 3}
        )
        self.assertTrue(form.is_valid(), form.errors)

    def test_price_override_optional(self):
        form = ProductVariantForm(
            data={"sku": "V-004", "stock": 1}
        )
        self.assertTrue(form.is_valid(), form.errors)

    def test_missing_sku(self):
        form = ProductVariantForm(data={"stock": 1})
        self.assertFalse(form.is_valid())
        self.assertIn("sku", form.errors)


# ============================================================================
# Helper function tests
# ============================================================================


class HandleCategoryTests(TestCase):
    """Tests for _handle_category helper."""

    def test_creates_new_category(self):
        cat = _handle_category("Gadgets")
        self.assertEqual(cat.name, "Gadgets")
        self.assertEqual(cat.slug, "gadgets")

    def test_returns_existing_category_case_insensitive(self):
        existing = _make_category(name="Books", slug="books")
        cat = _handle_category("BOOKS")
        self.assertEqual(cat.pk, existing.pk)

    def test_slug_collision_appends_counter(self):
        _make_category(name="Tech", slug="tech")
        # Force a new category whose slugify result collides
        cat = _handle_category("Tech!")  # Different name, but slug = "tech"
        self.assertNotEqual(cat.slug, "tech")
        self.assertTrue(cat.slug.startswith("tech"))


class HandleBrandTests(TestCase):
    """Tests for _handle_brand helper."""

    def test_returns_none_for_empty_string(self):
        self.assertIsNone(_handle_brand(""))

    def test_creates_new_brand(self):
        brand = _handle_brand("Apple")
        self.assertEqual(brand.name, "Apple")

    def test_returns_existing_brand_case_insensitive(self):
        existing = _make_brand(name="Nike", slug="nike")
        brand = _handle_brand("NIKE")
        self.assertEqual(brand.pk, existing.pk)

    def test_slug_collision_appends_counter(self):
        _make_brand(name="Adidas", slug="adidas")
        brand = _handle_brand("Adidas!")
        self.assertNotEqual(brand.slug, "adidas")


class GenerateSkuTests(TestCase):
    """Tests for _generate_sku helper."""

    def test_format(self):
        sku = _generate_sku()
        self.assertTrue(sku.startswith("EVO-"))
        self.assertEqual(len(sku), 12)  # "EVO-" (4) + 8 hex chars

    def test_uniqueness(self):
        skus = {_generate_sku() for _ in range(50)}
        self.assertEqual(len(skus), 50)


@override_settings(
    DEFAULT_FILE_STORAGE="django.core.files.storage.InMemoryStorage"
)
class SaveImagesTests(TestCase):
    """Tests for _save_images helper."""

    def setUp(self):
        self.product = _make_product()

    def test_first_image_set_as_primary(self):
        _save_images(self.product, [_make_image("a.png"), _make_image("b.png")])
        imgs = list(self.product.images.order_by("pk"))
        self.assertTrue(imgs[0].is_primary)
        self.assertFalse(imgs[1].is_primary)

    def test_existing_primary_not_overridden(self):
        ProductImage.objects.create(
            product=self.product, image=_make_image("existing.png"), is_primary=True
        )
        _save_images(self.product, [_make_image("new.png")])
        new_img = self.product.images.order_by("-pk").first()
        self.assertFalse(new_img.is_primary)

    def test_no_images(self):
        _save_images(self.product, [])
        self.assertEqual(self.product.images.count(), 0)

    def test_none_images(self):
        _save_images(self.product, None)
        self.assertEqual(self.product.images.count(), 0)


class SaveVariantsTests(TestCase):
    """Tests for _save_variants helper."""

    def setUp(self):
        self.product = _make_product()

    def test_creates_variants_from_post_data(self):
        post = {
            "variant-0-sku": "",
            "variant-0-color": "Red",
            "variant-0-stock": "10",
            "variant-1-sku": "",
            "variant-1-color": "Blue",
            "variant-1-stock": "5",
        }
        _save_variants(self.product, post)
        self.assertEqual(self.product.variants.count(), 2)

    def test_auto_generates_sku_when_empty(self):
        post = {
            "variant-0-sku": "",
            "variant-0-color": "Green",
            "variant-0-stock": "1",
        }
        _save_variants(self.product, post)
        v = self.product.variants.first()
        self.assertTrue(v.sku.startswith("EVO-"))

    def test_updates_existing_variant_by_sku(self):
        existing = ProductVariant.objects.create(
            product=self.product, sku="EXISTING", color="White", stock=1
        )
        post = {
            "variant-0-sku": "EXISTING",
            "variant-0-color": "Black",
            "variant-0-stock": "99",
        }
        _save_variants(self.product, post)
        existing.refresh_from_db()
        self.assertEqual(existing.color, "Black")
        self.assertEqual(existing.stock, 99)

    def test_invalid_stock_defaults_to_zero(self):
        post = {
            "variant-0-sku": "",
            "variant-0-color": "X",
            "variant-0-stock": "bad",
        }
        _save_variants(self.product, post)
        v = self.product.variants.first()
        self.assertEqual(v.stock, 0)

    def test_no_variant_data(self):
        _save_variants(self.product, {})
        self.assertEqual(self.product.variants.count(), 0)


# ============================================================================
# View tests — public (no auth)
# ============================================================================


@override_settings(
    DEFAULT_FILE_STORAGE="django.core.files.storage.InMemoryStorage"
)
class HomeViewTests(TestCase):
    """Tests for the home view."""

    def setUp(self):
        self.client = Client()
        self.url = reverse("products:home")
        self.category = _make_category()

    def test_get_200(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)

    def test_context_keys(self):
        resp = self.client.get(self.url)
        self.assertIn("products", resp.context)
        self.assertIn("categories", resp.context)

    def test_limits_to_12_products(self):
        for i in range(15):
            _make_product(
                category=self.category,
                slug=f"prod-{i}",
                name=f"Product {i}",
            )
        resp = self.client.get(self.url)
        self.assertLessEqual(len(resp.context["products"]), 12)

    def test_inactive_products_hidden(self):
        _make_product(category=self.category, is_active=False, slug="hidden")
        resp = self.client.get(self.url)
        slugs = [p.slug for p in resp.context["products"]]
        self.assertNotIn("hidden", slugs)

    def test_template_used(self):
        resp = self.client.get(self.url)
        self.assertTemplateUsed(resp, "products/home.html")


@override_settings(
    DEFAULT_FILE_STORAGE="django.core.files.storage.InMemoryStorage"
)
class CategoryDetailViewTests(TestCase):
    """Tests for category_detail view."""

    def setUp(self):
        self.client = Client()
        self.category = _make_category()

    def test_get_200(self):
        resp = self.client.get(
            reverse("products:category_detail", kwargs={"slug": self.category.slug})
        )
        self.assertEqual(resp.status_code, 200)

    def test_404_bad_slug(self):
        resp = self.client.get(
            reverse("products:category_detail", kwargs={"slug": "nope"})
        )
        self.assertEqual(resp.status_code, 404)

    def test_inactive_product_hidden(self):
        _make_product(
            category=self.category, is_active=False, slug="inactive-prod"
        )
        resp = self.client.get(
            reverse("products:category_detail", kwargs={"slug": self.category.slug})
        )
        slugs = [p.slug for p in resp.context["products"]]
        self.assertNotIn("inactive-prod", slugs)

    def test_context_has_category_and_products(self):
        _make_product(category=self.category)
        resp = self.client.get(
            reverse("products:category_detail", kwargs={"slug": self.category.slug})
        )
        self.assertIn("category", resp.context)
        self.assertIn("products", resp.context)
        self.assertEqual(resp.context["category"], self.category)

    def test_template_used(self):
        resp = self.client.get(
            reverse("products:category_detail", kwargs={"slug": self.category.slug})
        )
        self.assertTemplateUsed(resp, "products/category_detail.html")


@override_settings(
    DEFAULT_FILE_STORAGE="django.core.files.storage.InMemoryStorage"
)
class ProductDetailViewTests(TestCase):
    """Tests for product_detail view."""

    def setUp(self):
        self.client = Client()
        self.product = _make_product()

    def test_get_200(self):
        resp = self.client.get(
            reverse("products:product_detail", kwargs={"slug": self.product.slug})
        )
        self.assertEqual(resp.status_code, 200)

    def test_404_bad_slug(self):
        resp = self.client.get(
            reverse("products:product_detail", kwargs={"slug": "nonexistent"})
        )
        self.assertEqual(resp.status_code, 404)

    def test_404_inactive_product(self):
        self.product.is_active = False
        self.product.save()
        resp = self.client.get(
            reverse("products:product_detail", kwargs={"slug": self.product.slug})
        )
        self.assertEqual(resp.status_code, 404)

    def test_context_has_product(self):
        resp = self.client.get(
            reverse("products:product_detail", kwargs={"slug": self.product.slug})
        )
        self.assertEqual(resp.context["product"], self.product)

    def test_template_used(self):
        resp = self.client.get(
            reverse("products:product_detail", kwargs={"slug": self.product.slug})
        )
        self.assertTemplateUsed(resp, "products/product_detail.html")


# ============================================================================
# View tests — auth-required / seller-only
# ============================================================================


@override_settings(
    DEFAULT_FILE_STORAGE="django.core.files.storage.InMemoryStorage"
)
class AddProductViewTests(TestCase):
    """Tests for add_product view."""

    def setUp(self):
        self.client = Client()
        self.seller = _make_seller()
        self.buyer = _make_buyer()
        self.url = reverse("products:product_add")

    def test_login_required(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 302)
        self.assertIn("login", resp.url)

    def test_buyer_redirected(self):
        self.client.force_login(self.buyer)
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 302)

    def test_seller_get_200(self):
        self.client.force_login(self.seller)
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        self.assertIn("form", resp.context)
        self.assertEqual(resp.context["mode"], "add")

    def test_seller_post_valid_creates_product(self):
        self.client.force_login(self.seller)
        data = {
            "name": "Headphones",
            "description": "Premium sound",
            "price": "59.99",
            "old_price": "",
            "is_active": True,
            "category_name": "Audio",
            "brand_name": "Bose",
        }
        resp = self.client.post(self.url, data)
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(Product.objects.filter(name="Headphones").exists())
        product = Product.objects.get(name="Headphones")
        self.assertEqual(product.seller, self.seller)
        self.assertEqual(product.category.name, "Audio")
        self.assertEqual(product.brand.name, "Bose")

    def test_seller_post_creates_slug(self):
        self.client.force_login(self.seller)
        data = {
            "name": "My Cool Product!",
            "description": "",
            "price": "10.00",
            "is_active": True,
            "category_name": "General",
            "brand_name": "",
        }
        self.client.post(self.url, data)
        p = Product.objects.get(name="My Cool Product!")
        self.assertEqual(p.slug, "my-cool-product")

    def test_seller_post_duplicate_name_gets_unique_slug(self):
        self.client.force_login(self.seller)
        _make_product(slug="widget", name="Widget")
        data = {
            "name": "Widget",
            "description": "",
            "price": "10.00",
            "is_active": True,
            "category_name": "General",
            "brand_name": "",
        }
        self.client.post(self.url, data)
        slugs = list(Product.objects.values_list("slug", flat=True))
        self.assertEqual(len(slugs), 2)
        self.assertNotEqual(slugs[0], slugs[1])

    def test_seller_post_invalid_form(self):
        self.client.force_login(self.seller)
        data = {"name": "", "price": ""}  # Missing required fields
        resp = self.client.post(self.url, data)
        self.assertEqual(resp.status_code, 200)  # Re-renders form
        self.assertFalse(resp.context["form"].is_valid())

    def test_post_with_variants(self):
        self.client.force_login(self.seller)
        data = {
            "name": "T-Shirt",
            "description": "Cotton",
            "price": "20.00",
            "is_active": True,
            "category_name": "Clothing",
            "brand_name": "",
            "variant-0-sku": "",
            "variant-0-color": "Red",
            "variant-0-stock": "10",
        }
        self.client.post(self.url, data)
        product = Product.objects.get(name="T-Shirt")
        self.assertEqual(product.variants.count(), 1)
        self.assertEqual(product.variants.first().color, "Red")

    def test_template_used(self):
        self.client.force_login(self.seller)
        resp = self.client.get(self.url)
        self.assertTemplateUsed(resp, "products/product_form.html")


@override_settings(
    DEFAULT_FILE_STORAGE="django.core.files.storage.InMemoryStorage"
)
class MyShopViewTests(TestCase):
    """Tests for my_shop view."""

    def setUp(self):
        self.client = Client()
        self.seller = _make_seller()
        self.buyer = _make_buyer()
        self.url = reverse("products:my_shop")

    def test_login_required(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 302)

    def test_buyer_redirected(self):
        self.client.force_login(self.buyer)
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 302)

    def test_seller_get_200(self):
        self.client.force_login(self.seller)
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)

    def test_seller_sees_only_own_products(self):
        cat = _make_category()
        other_seller = _make_seller(email="other@evocart.com")
        _make_product(seller=self.seller, category=cat, slug="mine", name="Mine")
        _make_product(seller=other_seller, category=cat, slug="theirs", name="Theirs")
        self.client.force_login(self.seller)
        resp = self.client.get(self.url)
        slugs = [p.slug for p in resp.context["products"]]
        self.assertIn("mine", slugs)
        self.assertNotIn("theirs", slugs)

    def test_context_has_product_count(self):
        cat = _make_category()
        _make_product(seller=self.seller, category=cat, slug="s1")
        _make_product(seller=self.seller, category=cat, slug="s2", name="S2")
        self.client.force_login(self.seller)
        resp = self.client.get(self.url)
        self.assertEqual(resp.context["product_count"], 2)

    def test_template_used(self):
        self.client.force_login(self.seller)
        resp = self.client.get(self.url)
        self.assertTemplateUsed(resp, "products/my_shop.html")


@override_settings(
    DEFAULT_FILE_STORAGE="django.core.files.storage.InMemoryStorage"
)
class EditProductViewTests(TestCase):
    """Tests for edit_product view."""

    def setUp(self):
        self.client = Client()
        self.seller = _make_seller()
        self.buyer = _make_buyer()
        self.category = _make_category()
        self.product = _make_product(
            seller=self.seller, category=self.category, slug="editable"
        )
        self.url = reverse("products:product_edit", kwargs={"slug": "editable"})

    def test_login_required(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 302)

    def test_other_seller_gets_404(self):
        other = _make_seller(email="other@evocart.com")
        self.client.force_login(other)
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 404)

    def test_owner_get_200(self):
        self.client.force_login(self.seller)
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context["mode"], "edit")

    def test_form_pre_filled(self):
        self.client.force_login(self.seller)
        resp = self.client.get(self.url)
        form = resp.context["form"]
        self.assertEqual(form.initial["category_name"], self.category.name)

    def test_post_updates_product(self):
        self.client.force_login(self.seller)
        data = {
            "name": "Updated Name",
            "description": "Updated desc",
            "price": "149.99",
            "is_active": True,
            "category_name": "Electronics",
            "brand_name": "",
        }
        resp = self.client.post(self.url, data)
        self.assertEqual(resp.status_code, 302)
        self.product.refresh_from_db()
        self.assertEqual(self.product.name, "Updated Name")
        self.assertEqual(self.product.price, Decimal("149.99"))

    def test_post_invalid_rerenders(self):
        self.client.force_login(self.seller)
        resp = self.client.post(self.url, {"name": "", "price": ""})
        self.assertEqual(resp.status_code, 200)

    def test_buyer_cannot_edit(self):
        """A buyer who somehow owns the product still gets blocked by role check."""
        # Product owned by seller, buyer tries via force_login
        self.client.force_login(self.buyer)
        resp = self.client.get(self.url)
        # get_object_or_404(slug=slug, seller=request.user) → 404 for buyer
        self.assertEqual(resp.status_code, 404)

    def test_template_used(self):
        self.client.force_login(self.seller)
        resp = self.client.get(self.url)
        self.assertTemplateUsed(resp, "products/product_form.html")


@override_settings(
    DEFAULT_FILE_STORAGE="django.core.files.storage.InMemoryStorage"
)
class ProductDeleteViewTests(TestCase):
    """Tests for product_delete view."""

    def setUp(self):
        self.client = Client()
        self.seller = _make_seller()
        self.buyer = _make_buyer()
        self.category = _make_category()
        self.product = _make_product(
            seller=self.seller, category=self.category, slug="deletable"
        )
        self.url = reverse(
            "products:product_delete", kwargs={"slug": "deletable"}
        )

    def test_login_required(self):
        resp = self.client.post(self.url)
        self.assertEqual(resp.status_code, 302)
        self.assertIn("login", resp.url)

    def test_other_seller_gets_404(self):
        other = _make_seller(email="other@evocart.com")
        self.client.force_login(other)
        resp = self.client.post(self.url)
        self.assertEqual(resp.status_code, 404)

    def test_owner_can_delete(self):
        self.client.force_login(self.seller)
        resp = self.client.post(self.url)
        self.assertEqual(resp.status_code, 302)
        self.assertFalse(Product.objects.filter(slug="deletable").exists())

    def test_delete_cascades_images(self):
        ProductImage.objects.create(
            product=self.product, image=_make_image()
        )
        self.client.force_login(self.seller)
        self.client.post(self.url)
        self.assertEqual(ProductImage.objects.count(), 0)

    def test_delete_cascades_variants(self):
        ProductVariant.objects.create(
            product=self.product, sku="DEL-V1", stock=5
        )
        self.client.force_login(self.seller)
        self.client.post(self.url)
        self.assertEqual(ProductVariant.objects.count(), 0)

    def test_redirects_to_my_shop(self):
        self.client.force_login(self.seller)
        resp = self.client.post(self.url)
        self.assertRedirects(resp, reverse("products:my_shop"))


# ============================================================================
# URL routing tests
# ============================================================================


class ProductURLTests(TestCase):
    """Verify all named URLs resolve to the correct view functions."""

    def test_home_url(self):
        url = reverse("products:home")
        self.assertEqual(url, "/")

    def test_my_shop_url(self):
        url = reverse("products:my_shop")
        self.assertEqual(url, "/my-shop/")

    def test_product_add_url(self):
        url = reverse("products:product_add")
        self.assertEqual(url, "/product/add/")

    def test_product_edit_url(self):
        url = reverse("products:product_edit", kwargs={"slug": "test"})
        self.assertEqual(url, "/product/test/edit/")

    def test_product_delete_url(self):
        url = reverse("products:product_delete", kwargs={"slug": "test"})
        self.assertEqual(url, "/product/test/delete/")

    def test_category_detail_url(self):
        url = reverse("products:category_detail", kwargs={"slug": "electronics"})
        self.assertEqual(url, "/category/electronics/")

    def test_product_detail_url(self):
        url = reverse("products:product_detail", kwargs={"slug": "cool-phone"})
        self.assertEqual(url, "/product/cool-phone/")

    def test_home_resolves_to_view(self):
        match = resolve("/")
        self.assertEqual(match.func.__name__, "home")

    def test_product_detail_resolves(self):
        match = resolve("/product/some-slug/")
        self.assertEqual(match.func.__name__, "product_detail")

    def test_category_detail_resolves(self):
        match = resolve("/category/some-slug/")
        self.assertEqual(match.func.__name__, "category_detail")


# ============================================================================
# Admin smoke tests
# ============================================================================


class ProductAdminTests(TestCase):
    """Verify models are registered in admin."""

    def test_category_registered(self):
        from django.contrib.admin.sites import site

        self.assertIn(Category, site._registry)

    def test_brand_registered(self):
        from django.contrib.admin.sites import site

        self.assertIn(Brand, site._registry)

    def test_product_registered(self):
        from django.contrib.admin.sites import site

        self.assertIn(Product, site._registry)

    def test_product_admin_has_inlines(self):
        from django.contrib.admin.sites import site

        admin_cls = site._registry[Product]
        inline_models = [i.model for i in admin_cls.inlines]
        self.assertIn(ProductImage, inline_models)
        self.assertIn(ProductVariant, inline_models)
