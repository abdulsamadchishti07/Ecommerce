from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from apps.products.models import ProductVariant
from .cart import Cart


def cart_detail(request):
    cart = Cart(request)
    return render(request, "cart/cart_detail.html", {"cart": cart})


@require_POST
def cart_add(request, variant_id):
    cart = Cart(request)
    variant = get_object_or_404(ProductVariant, id=variant_id)
    quantity = int(request.POST.get("quantity", 1))
    cart.add(variant_id=variant.id, quantity=quantity)
    return redirect("cart:cart_detail")


@require_POST
def cart_update(request, variant_id):
    cart = Cart(request)
    variant = get_object_or_404(ProductVariant, id=variant_id)
    quantity = int(request.POST.get("quantity", 1))
    cart.update(variant_id=variant.id, quantity=quantity)
    return redirect("cart:cart_detail")


@require_POST
def cart_remove(request, variant_id):
    cart = Cart(request)
    cart.remove(variant_id=variant_id)
    return redirect("cart:cart_detail")
