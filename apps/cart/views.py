from django.contrib import messages
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
    
    # Check stock limit if available
    if variant.stock < quantity:
        messages.error(request, f"Sorry, only {variant.stock} unit(s) available in stock.")
        return redirect("cart:cart_detail")

    cart.add(variant=variant, quantity=quantity)
    messages.success(request, f"Added {variant.product.name} to your cart.")
    return redirect("cart:cart_detail")


@require_POST
def cart_update(request, variant_id):
    cart = Cart(request)
    variant = get_object_or_404(ProductVariant, id=variant_id)
    quantity = int(request.POST.get("quantity", 1))
    
    if quantity > 0 and variant.stock < quantity:
        messages.error(request, f"Only {variant.stock} unit(s) available in stock.")
    else:
        cart.update(variant=variant, quantity=quantity)
        if quantity > 0:
            messages.success(request, "Cart updated.")
        else:
            messages.info(request, "Item removed from cart.")
            
    return redirect("cart:cart_detail")


@require_POST
def cart_remove(request, variant_id):
    cart = Cart(request)
    variant = get_object_or_404(ProductVariant, id=variant_id)
    cart.remove(variant=variant)
    messages.info(request, f"Removed {variant.product.name} from your cart.")
    return redirect("cart:cart_detail")


@require_POST
def cart_clear(request):
    cart = Cart(request)
    cart.clear()
    messages.info(request, "Your cart has been cleared.")
    return redirect("cart:cart_detail")
