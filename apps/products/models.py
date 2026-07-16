from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.urls import reverse

from apps.core.models import TimeStampField


class Category(TimeStampField):
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(max_length=225, unique=True)

    class Meta:
        verbose_name_plural = "Categories"
        ordering = ["name"]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("products:category_detail", kwargs={"slug": self.slug})


class Brand(TimeStampField):
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(max_length=225, unique=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("products:brand_detail", kwargs={"slug": self.slug})


class Product(TimeStampField):
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=225, unique=True)
    seller = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="products",
        null=True,
        blank=True,
    )

    description = models.TextField(blank=True)

    price = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )

    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="products",
    )

    brand = models.ForeignKey(
        Brand,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="products",
    )

    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("products:product_detail", kwargs={"slug": self.slug})

    @property
    def total_stock(self):
        return sum(variant.stock for variant in self.variants.all())

    @property
    def in_stock(self):
        return self.total_stock > 0


class ProductImage(TimeStampField):
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="images",
    )

    image = models.ImageField(upload_to="products/")
    alt_text = models.CharField(max_length=100, blank=True)
    is_primary = models.BooleanField(default=False)

    class Meta:
        ordering = ["-is_primary", "created_at"]

    def __str__(self):
        return f"{self.product.name} Image"


class ProductVariant(TimeStampField):
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="variants",
    )

    sku = models.CharField(max_length=50, unique=True)

    size = models.CharField(max_length=20, blank=True)
    color = models.CharField(max_length=30, blank=True)

    price_override = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        help_text="Leave blank to use the product price.",
    )

    stock = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["product", "size", "color"],
                name="unique_product_variant",
            )
        ]

    def __str__(self):
        return f"{self.product.name} ({self.size}/{self.color})"

    @property
    def price(self):
        return self.price_override if self.price_override is not None else self.product.price