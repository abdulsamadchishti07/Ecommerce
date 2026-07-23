from django.contrib import admin
from .models import Order, OrderItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("product_name", "variant_info", "price", "quantity", "subtotal_display")
    can_delete = False

    def subtotal_display(self, obj):
        return f"Rs {obj.subtotal}"
    subtotal_display.short_description = "Subtotal"


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        "order_number",
        "email",
        "full_name",
        "total_amount_display",
        "status",
        "payment_status",
        "payment_method",
        "created_at",
    )
    list_filter = ("status", "payment_status", "payment_method", "created_at")
    search_fields = ("order_number", "email", "first_name", "last_name", "street_address", "city")
    readonly_fields = ("order_number", "created_at", "updated_at", "total_amount_display")
    inlines = [OrderItemInline]

    fieldsets = (
        ("Order Information", {
            "fields": ("order_number", "user", "status", "payment_status", "payment_method", "total_amount_display")
        }),
        ("Customer Details", {
            "fields": ("email", "first_name", "last_name", "phone")
        }),
        ("Shipping Address", {
            "fields": ("street_address", "city", "state", "postal_code", "country")
        }),
        ("Timestamps", {
            "fields": ("created_at", "updated_at")
        }),
    )

    def total_amount_display(self, obj):
        return f"Rs {obj.total_amount}"
    total_amount_display.short_description = "Total Amount"
