from django.urls import path
from . import views

app_name = "products"

urlpatterns = [
    path("", views.home, name="home"),
    path("my-shop/", views.my_shop, name="my_shop"),
    path("product/add/", views.add_product, name="product_add"),
    path("product/<slug:slug>/edit/", views.edit_product, name="product_edit"),
    path("product/<slug:slug>/delete/", views.product_delete, name="product_delete"),
    path("category/<slug:slug>/", views.category_detail, name="category_detail"),
    path("product/<slug:slug>/", views.product_detail, name="product_detail"),
]