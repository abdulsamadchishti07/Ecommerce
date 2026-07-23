from apps.cart.models import Cart as CartModel, CartItem
from apps.products.models import ProductVariant


class Cart:
    """
    Service wrapper around the DB-backed Cart and CartItem models.
    Supports authenticated users and guest visitors (via session_key),
    automatically merging guest session carts upon user login.
    """

    def __init__(self, request):
        self.request = request
        self.user = request.user if request.user.is_authenticated else None
        
        # Ensure session key exists for guests or pre-login state
        if not request.session.session_key:
            request.session.save()
        self.session_key = request.session.session_key

        if self.user:
            # 1. Retrieve or create the user's cart
            self.cart_obj, _ = CartModel.objects.get_or_create(user=self.user)
            
            # 2. Check if a guest session cart exists and merge it
            session_cart = CartModel.objects.filter(session_key=self.session_key, user__isnull=True).first()
            if session_cart and session_cart != self.cart_obj:
                self._merge_carts(source_cart=session_cart, target_cart=self.cart_obj)
        else:
            # Guest visitor cart
            self.cart_obj, _ = CartModel.objects.get_or_create(
                session_key=self.session_key,
                user__isnull=True,
            )

    def _get_variant(self, variant_or_id):
        if isinstance(variant_or_id, ProductVariant):
            return variant_or_id
        return ProductVariant.objects.get(id=variant_or_id)

    def _merge_carts(self, source_cart, target_cart):
        """Merge items from a guest session cart into a user cart and delete source."""
        for item in source_cart.items.all():
            target_item, created = CartItem.objects.get_or_create(
                cart=target_cart,
                variant=item.variant,
                defaults={
                    "quantity": item.quantity,
                    "price_at_add": item.price_at_add,
                },
            )
            if not created:
                target_item.quantity += item.quantity
                target_item.save(update_fields=["quantity", "updated_at"])
        
        source_cart.delete()

    def add(self, variant, quantity=1):
        """Add a ProductVariant to the cart or increase its quantity."""
        variant_obj = self._get_variant(variant)
        quantity = max(1, int(quantity))
        item, created = CartItem.objects.get_or_create(
            cart=self.cart_obj,
            variant=variant_obj,
            defaults={
                "quantity": quantity,
                "price_at_add": variant_obj.price,
            },
        )
        if not created:
            item.quantity += quantity
            item.save(update_fields=["quantity", "updated_at"])
        return item

    def update(self, variant, quantity):
        """Set an exact quantity for a ProductVariant in the cart."""
        variant_obj = self._get_variant(variant)
        quantity = int(quantity)
        if quantity <= 0:
            self.remove(variant_obj)
        else:
            item = CartItem.objects.filter(cart=self.cart_obj, variant=variant_obj).first()
            if item:
                item.quantity = quantity
                item.save(update_fields=["quantity", "updated_at"])

    def remove(self, variant):
        """Remove a ProductVariant from the cart."""
        variant_obj = self._get_variant(variant)
        CartItem.objects.filter(cart=self.cart_obj, variant=variant_obj).delete()

    def clear(self):
        """Remove all items from the cart."""
        self.cart_obj.items.all().delete()

    def __iter__(self):
        """Iterate over cart items prefetching variants and products for efficiency."""
        items = self.cart_obj.items.select_related(
            "variant", "variant__product"
        ).prefetch_related(
            "variant__product__images"
        )
        for item in items:
            yield item

    def __len__(self):
        """Total number of items (sum of quantities) in cart."""
        return self.cart_obj.item_count

    @property
    def total(self):
        """Total price sum of all items in cart."""
        return self.cart_obj.total