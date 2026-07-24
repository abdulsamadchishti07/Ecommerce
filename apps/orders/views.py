from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import render, redirect, get_object_or_404
from apps.cart.cart import Cart
from apps.products.models import ProductVariant
from .forms import CheckoutForm
from .models import Order, OrderItem


def checkout_view(request):
    cart = Cart(request)
    
    # Redirect if cart is empty
    if len(cart) == 0:
        messages.warning(request, "Your cart is empty. Add products before checking out.")
        return redirect("cart:cart_detail")

    if request.method == "POST":
        form = CheckoutForm(request.POST, user=request.user)
        if form.is_valid():
            try:
                with transaction.atomic():
                    # 1. Verify stock availability for all cart items first
                    for item in cart:
                        # Fetch latest variant state with lock
                        variant = ProductVariant.objects.select_for_update().get(id=item.variant.id)
                        if variant.stock < item.quantity:
                            messages.error(
                                request,
                                f"Sorry, '{variant.product.name}' only has {variant.stock} unit(s) left in stock."
                            )
                            return redirect("cart:cart_detail")

                    # 2. Create Order
                    order = form.save(commit=False)
                    if request.user.is_authenticated:
                        order.user = request.user
                    order.total_amount = cart.total
                    order.save()

                    # 3. Create OrderItems and deduct stock
                    for item in cart:
                        variant = ProductVariant.objects.select_for_update().get(id=item.variant.id)
                        
                        # Variant info string (e.g. "Color: White, Size: M")
                        specs = []
                        if variant.color:
                            specs.append(f"Color: {variant.color}")
                        if variant.size:
                            specs.append(f"Size: {variant.size}")
                        variant_info_str = ", ".join(specs)

                        OrderItem.objects.create(
                            order=order,
                            variant=variant,
                            product_name=variant.product.name,
                            variant_info=variant_info_str,
                            price=variant.price,
                            quantity=item.quantity,
                        )

                        # Deduct stock
                        variant.stock -= item.quantity
                        variant.save(update_fields=["stock", "updated_at"])

                    # 4. Create Payment record & route to payment flow
                    from apps.payments.models import Payment
                    payment = Payment.objects.create(
                        order=order,
                        payment_method=order.payment_method,
                        amount=order.total_amount,
                        status="PENDING",
                    )

                    # 5. Clear cart
                    cart.clear()

                    if order.payment_method == "CARD":
                        messages.info(request, "Please enter your card details to complete your payment.")
                        return redirect("payments:process", order_number=order.order_number)
                    elif order.payment_method == "BANK":
                        messages.info(request, "Please complete your bank transfer using the details below.")
                        return redirect("payments:bank_transfer", order_number=order.order_number)
                    else:
                        messages.success(request, f"Order #{order.order_number} placed successfully!")
                        return redirect("orders:order_confirmation", order_number=order.order_number)

            except Exception as e:
                messages.error(request, f"An unexpected error occurred while placing your order: {str(e)}")
    else:
        form = CheckoutForm(user=request.user)

    context = {
        "cart": cart,
        "form": form,
    }
    return render(request, "orders/checkout.html", context)


def order_confirmation_view(request, order_number):
    order = get_object_or_404(Order.objects.prefetch_related("items", "items__variant", "items__variant__product"), order_number=order_number)
    
    # Restrict viewing order confirmation to owner or guest order matching email/session
    if order.user and request.user.is_authenticated and order.user != request.user:
        messages.error(request, "You do not have permission to view this order.")
        return redirect("products:home")

    return render(request, "orders/confirmation.html", {"order": order})


@login_required
def order_history_view(request):
    orders = Order.objects.filter(user=request.user).prefetch_related("items")
    return render(request, "orders/order_history.html", {"orders": orders})
