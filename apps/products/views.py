from django.shortcuts import render, get_object_or_404
from .models import Product, Category


def home(request):
    products = Product.objects.filter(is_active=True).select_related("category", "brand")[:12]
    categories = Category.objects.all()
    return render(request, "products/home.html", {
        "products": products,
        "categories": categories,
    })


def category_detail(request, slug):
    category = get_object_or_404(Category, slug=slug)
    products = category.products.filter(is_active=True).select_related("brand")
    return render(request, "products/category_detail.html", {
        "category": category,
        "products": products,
    })


def product_detail(request, slug):
    product = get_object_or_404(
        Product.objects.select_related("category", "brand").prefetch_related("images", "variants"),
        slug=slug,
        is_active=True,
    )
    return render(request, "products/product_detail.html", {
        "product": product,
    })