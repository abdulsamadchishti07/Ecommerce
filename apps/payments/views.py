import json
from decimal import Decimal
# pyrefly: ignore [missing-import]
import stripe
from django.conf import settings
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from apps.orders.models import Order
from .forms import BankTransferForm
from .models import Payment

if settings.STRIPE_SECRET_KEY:
    stripe.api_key = settings.STRIPE_SECRET_KEY


def get_or_create_order_payment(order):
    """Retrieve or create a Payment record for an Order."""
    payment, created = Payment.objects.get_or_create(
        order=order,
        defaults={
            "amount": order.total_amount,
            "payment_method": order.payment_method,
            "status": "PENDING",
        },
    )
    return payment


def process_payment_view(request, order_number):
    """
    Main payment processing portal for an order.
    Handles Card Payments (Stripe / Gateway Simulation), COD, and Direct Bank Transfer routing.
    """
    order = get_object_or_404(Order, order_number=order_number)

    # Permission check: ensure user owns order if logged in
    if order.user and request.user.is_authenticated and order.user != request.user:
        messages.error(request, "You do not have permission to access this payment.")
        return redirect("products:home")

    # If already paid, redirect to confirmation
    if order.payment_status == "PAID":
        messages.info(request, f"Order #{order.order_number} is already paid.")
        return redirect("orders:order_confirmation", order_number=order.order_number)

    payment = get_or_create_order_payment(order)

    # Route based on payment method
    if order.payment_method == "COD":
        messages.info(request, "Your order is placed with Cash on Delivery.")
        return redirect("orders:order_confirmation", order_number=order.order_number)

    elif order.payment_method == "BANK":
        return redirect("payments:bank_transfer", order_number=order.order_number)

    # CARD payment processing
    client_secret = None
    stripe_enabled = bool(settings.STRIPE_SECRET_KEY and settings.STRIPE_PUBLISHABLE_KEY)

    if stripe_enabled:
        try:
            # Create or update Stripe PaymentIntent
            intent = stripe.PaymentIntent.create(
                amount=int(order.total_amount * 100),  # amount in cents
                currency="usd",
                metadata={"order_number": order.order_number},
            )
            client_secret = intent.client_secret
        except Exception as e:
            # Fallback if Stripe credentials fail or test key error occurs
            stripe_enabled = False

    if request.method == "POST":
        # Handle card submission (Stripe confirmation or Card Simulation)
        simulate_success = request.POST.get("simulate_success") == "1" or request.POST.get("stripe_payment_id")
        
        if simulate_success:
            txn_id = request.POST.get("stripe_payment_id") or f"CARD-{order.order_number}"
            payment.mark_as_successful(
                transaction_id=txn_id,
                provider_response={"status": "succeeded", "method": "card"},
            )
            messages.success(request, f"Payment of Rs {order.total_amount} processed successfully!")
            return redirect("orders:order_confirmation", order_number=order.order_number)
        else:
            payment.mark_as_failed(reason="Card transaction declined or cancelled.")
            messages.error(request, "Payment was not successful. Please check your card details and try again.")

    context = {
        "order": order,
        "payment": payment,
        "stripe_enabled": stripe_enabled,
        "stripe_publishable_key": settings.STRIPE_PUBLISHABLE_KEY,
        "client_secret": client_secret,
    }
    return render(request, "payments/process.html", context)


def bank_transfer_view(request, order_number):
    """
    Renders Bank Account Transfer details and handles upload of payment receipt / reference code.
    """
    order = get_object_or_404(Order, order_number=order_number)

    if order.user and request.user.is_authenticated and order.user != request.user:
        messages.error(request, "You do not have permission to access this order.")
        return redirect("products:home")

    payment = get_or_create_order_payment(order)

    if request.method == "POST":
        form = BankTransferForm(request.POST, request.FILES, instance=payment)
        if form.is_valid():
            bank_payment = form.save(commit=False)
            bank_payment.bank_reference = form.cleaned_data.get("bank_reference")
            bank_payment.payment_method = "BANK"
            bank_payment.status = "PROCESSING"
            bank_payment.save()

            messages.success(
                request,
                "Thank you! We received your bank transfer reference details. "
                "Our team will verify your transaction and update your order status.",
            )
            return redirect("orders:order_confirmation", order_number=order.order_number)
    else:
        form = BankTransferForm(instance=payment)

    context = {
        "order": order,
        "payment": payment,
        "form": form,
        "bank_name": "EvoCart Global Bank",
        "account_title": "EvoCart E-Commerce Pvt Ltd",
        "account_number": "1234-5678-9012-3456",
        "iban": "PK36EVOC0001234567890123",
        "swift_code": "EVOCPKKAXXX",
    }
    return render(request, "payments/bank_transfer.html", context)


@csrf_exempt
@require_POST
def stripe_webhook_view(request):
    """
    Stripe Webhook handler to listen for asynchronous payment status events.
    """
    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")
    endpoint_secret = settings.STRIPE_WEBHOOK_SECRET

    event = None

    if endpoint_secret:
        try:
            event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
        except ValueError:
            return HttpResponse(status=400)
        except stripe.error.SignatureVerificationError:
            return HttpResponse(status=400)
    else:
        try:
            event = json.loads(payload)
        except Exception:
            return HttpResponse(status=400)

    # Handle PaymentIntent events
    event_type = event.get("type") if isinstance(event, dict) else event.type

    if event_type == "payment_intent.succeeded":
        intent = event["data"]["object"] if isinstance(event, dict) else event.data.object
        order_number = intent.get("metadata", {}).get("order_number")
        
        if order_number:
            try:
                order = Order.objects.get(order_number=order_number)
                payment = get_or_create_order_payment(order)
                payment.mark_as_successful(
                    transaction_id=intent.get("id"),
                    provider_response=intent,
                )
            except Order.DoesNotExist:
                pass

    elif event_type == "payment_intent.payment_failed":
        intent = event["data"]["object"] if isinstance(event, dict) else event.data.object
        order_number = intent.get("metadata", {}).get("order_number")
        
        if order_number:
            try:
                order = Order.objects.get(order_number=order_number)
                payment = get_or_create_order_payment(order)
                payment.mark_as_failed(
                    reason=intent.get("last_payment_error", {}).get("message", "Payment failed"),
                    provider_response=intent,
                )
            except Order.DoesNotExist:
                pass

    return JsonResponse({"status": "success"})


def payment_status_view(request, order_number):
    """API endpoint to query current payment status for an order."""
    order = get_object_or_404(Order, order_number=order_number)
    payment = Payment.objects.filter(order=order).first()
    
    return JsonResponse({
        "order_number": order.order_number,
        "payment_status": order.payment_status,
        "order_status": order.status,
        "payment_state": payment.status if payment else "PENDING",
        "is_paid": order.payment_status == "PAID",
    })
