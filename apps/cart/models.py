from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from apps.core.models import TimeStampField
from apps.products.models import ProductVariant


class Cart(TimeStampField):
    """
    One cart per visitor.

    - Authenticated users  → user is set, session_key is NULL.
    - Guest visitors       → user is NULL, session_key is set.

    When a guest logs in, their session cart is merged into the
    user's cart (handled in the Cart service layer, not here).
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="cart",
        null=True,
        blank=True,
    )

    session_key = models.CharField(
        max_length=40,
        null=True,
        blank=True,
        db_index=True,
        help_text="Django session key for guest carts.",
    )

    class Meta:
        constraints = [
            # A user can only have one cart
            models.UniqueConstraint(
                fields=["user"],
                condition=models.Q(user__isnull=False),
                name="one_cart_per_user",
            ),
            # A session can only have one cart
            models.UniqueConstraint(
                fields=["session_key"],
                condition=models.Q(session_key__isnull=False),
                name="one_cart_per_session",
            ),
        ]

    def __str__(self):
        if self.user:
            return f"Cart for {self.user.email}"
        return f"Cart for session {self.session_key}"

    # ── Helper properties ───────────────────────────────────────

    @property
    def total(self):
        """Sum of all item subtotals (uses the live variant price)."""
        return sum(item.subtotal for item in self.items.select_related(
            "variant", "variant__product"
        ))

    @property
    def item_count(self):
        """Total number of individual units in the cart."""
        return sum(
            item.quantity for item in self.items.all()
        )

    def __len__(self):
        return self.item_count


class CartItem(TimeStampField):
    """
    One row per variant in a cart.

    quantity   – how many units the buyer wants.
    price_at_add – snapshot of the variant price when added; useful for
                   showing "price changed" warnings, but the live price
                   from the variant is used for totals.
    """

    cart = models.ForeignKey(
        Cart,
        on_delete=models.CASCADE,
        related_name="items",
    )

    variant = models.ForeignKey(
        ProductVariant,
        on_delete=models.CASCADE,
        related_name="cart_items",
    )

    quantity = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(1)],
    )

    price_at_add = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Variant price snapshot when item was added.",
    )

    class Meta:
        constraints = [
            # Same variant can only appear once per cart
            models.UniqueConstraint(
                fields=["cart", "variant"],
                name="unique_variant_per_cart",
            ),
        ]
        ordering = ["-created_at"]

    def __str__(self):
        return (
            f"{self.quantity}× {self.variant.product.name} "
            f"({self.variant.color}/{self.variant.size})"
        )

    @property
    def subtotal(self):
        """Live price × quantity (not the snapshot)."""
        return self.variant.price * self.quantity

    @property
    def price_changed(self):
        """True if the variant price has changed since this item was added."""
        return self.variant.price != self.price_at_add
