import json
# pyrefly: ignore [missing-import]
import redis
# pyrefly: ignore [missing-import]
from django_redis import get_redis_connection
from apps.products.models import ProductVariant


CART_TTL_SECONDS = 60 * 60 * 24 * 7  # 1 week


class Cart:
    def __init__(self, request):
        self.session = request.session
        self.redis = get_redis_connection("default")
        # each visitor needs a stable key even before login — Django's
        # session key already gives us that once we force it to exist
        if not self.session.session_key:
            self.session.save()
        self.key = f"cart:{self.session.session_key}"

    def _get_data(self):
        try:
            raw = self.redis.get(self.key)
            return json.loads(raw) if raw else {}
        except redis.exceptions.ConnectionError:
            return {}

    def _save_data(self, data):
        try:
            self.redis.set(self.key, json.dumps(data), ex=CART_TTL_SECONDS)
        except redis.exceptions.ConnectionError:
            pass

    def add(self, variant_id, quantity=1):
        data = self._get_data()
        variant_id = str(variant_id)
        data[variant_id] = data.get(variant_id, 0) + quantity
        self._save_data(data)

    def update(self, variant_id, quantity):
        data = self._get_data()
        variant_id = str(variant_id)
        if quantity <= 0:
            data.pop(variant_id, None)
        else:
            data[variant_id] = quantity
        self._save_data(data)

    def remove(self, variant_id):
        data = self._get_data()
        data.pop(str(variant_id), None)
        self._save_data(data)

    def clear(self):
        self.redis.delete(self.key)

    def __iter__(self):
        data = self._get_data()
        variant_ids = data.keys()
        variants = ProductVariant.objects.filter(id__in=variant_ids).select_related("product")
        variants_by_id = {str(v.id): v for v in variants}

        for variant_id, quantity in data.items():
            variant = variants_by_id.get(variant_id)
            if not variant:
                continue  # variant was deleted since being added to cart
            yield {
                "variant": variant,
                "quantity": quantity,
                "subtotal": variant.price * quantity,
            }

    def __len__(self):
        return sum(self._get_data().values())

    @property
    def total(self):
        return sum(item["subtotal"] for item in self)