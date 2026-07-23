from django.urls import path
from . import views

app_name = "orders"

urlpatterns = [
    path("checkout/", views.checkout_view, name="checkout"),
    path("confirmation/<str:order_number>/", views.order_confirmation_view, name="order_confirmation"),
    path("history/", views.order_history_view, name="order_history"),
]
