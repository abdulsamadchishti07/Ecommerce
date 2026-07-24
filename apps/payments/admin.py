from django.contrib import admin
from .models import Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        "transaction_id",
        "order",
        "payment_method",
        "amount",
        "status",
        "bank_reference",
        "created_at",
    )
    list_filter = ("status", "payment_method", "created_at")
    search_fields = (
        "transaction_id",
        "order__order_number",
        "order__email",
        "bank_reference",
    )
    readonly_fields = ("transaction_id", "created_at", "updated_at")
    actions = ["mark_as_successful_action", "mark_as_failed_action"]

    @admin.action(description="Mark selected payments as Successful & update orders")
    def mark_as_successful_action(self, request, queryset):
        count = 0
        for payment in queryset:
            payment.mark_as_successful()
            count += 1
        self.message_user(request, f"Successfully updated {count} payment(s) to SUCCESSFUL.")

    @admin.action(description="Mark selected payments as Failed")
    def mark_as_failed_action(self, request, queryset):
        count = 0
        for payment in queryset:
            payment.mark_as_failed(reason="Marked as failed by administrator.")
            count += 1
        self.message_user(request, f"Successfully updated {count} payment(s) to FAILED.")
