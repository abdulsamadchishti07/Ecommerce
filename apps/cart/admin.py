from django.contrib import admin

from .models import Cart, CartItem


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0
    readonly_fields = ("price_at_add", "subtotal_display")
    raw_id_fields = ("variant",)

    def subtotal_display(self, obj):
        return f"Rs {obj.subtotal}"
    subtotal_display.short_description = "Subtotal"


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "session_key", "item_count", "total_display", "created_at")
    list_filter = ("created_at",)
    search_fields = ("user__email", "session_key")
    raw_id_fields = ("user",)
    inlines = [CartItemInline]

    def total_display(self, obj):
        return f"Rs {obj.total}"
    total_display.short_description = "Total"
