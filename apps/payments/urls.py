from django.urls import path
from . import views

app_name = "payments"

urlpatterns = [
    path("process/<str:order_number>/", views.process_payment_view, name="process"),
    path("bank-transfer/<str:order_number>/", views.bank_transfer_view, name="bank_transfer"),
    path("webhook/stripe/", views.stripe_webhook_view, name="stripe_webhook"),
    path("status/<str:order_number>/", views.payment_status_view, name="payment_status"),
]
