import uuid

from django.shortcuts import render, get_object_or_404
from .models import Product, Category
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.utils.text import slugify
from django.contrib import messages
from .forms import ProductForm, ProductVariantForm
from .models import Brand, ProductImage, ProductVariant


def home(request):
    products = Product.objects.filter(is_active=True).select_related("category", "brand").prefetch_related("images")[:12]
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


def _handle_category(cat_name):
    """Get or create a category by name."""
    category = Category.objects.filter(name__iexact=cat_name).first()
    if not category:
        cat_slug = slugify(cat_name)
        counter = 1
        while Category.objects.filter(slug=cat_slug).exists():
            cat_slug = f"{slugify(cat_name)}-{counter}"
            counter += 1
        category = Category.objects.create(name=cat_name, slug=cat_slug)
    return category


def _handle_brand(brand_name):
    """Get or create a brand by name, or return None if empty."""
    if not brand_name:
        return None
    brand = Brand.objects.filter(name__iexact=brand_name).first()
    if not brand:
        brand_slug = slugify(brand_name)
        counter = 1
        while Brand.objects.filter(slug=brand_slug).exists():
            brand_slug = f"{slugify(brand_name)}-{counter}"
            counter += 1
        brand = Brand.objects.create(name=brand_name, slug=brand_slug)
    return brand


def _save_images(product, images):
    """Save uploaded images for a product."""
    if images:
        has_primary = product.images.filter(is_primary=True).exists()
        for i, image in enumerate(images):
            ProductImage.objects.create(
                product=product,
                image=image,
                is_primary=(not has_primary and i == 0),
            )


def _generate_sku():
    """Generate a unique random SKU like EVO-A7X3K9M2."""
    while True:
        code = uuid.uuid4().hex[:8].upper()
        sku = f"EVO-{code}"
        if not ProductVariant.objects.filter(sku=sku).exists():
            return sku


def _save_variants(product, post_data):
    """Parse and save variants from POST data (dynamic rows)."""
    index = 0
    while f'variant-{index}-color' in post_data or f'variant-{index}-sku' in post_data:
        sku = post_data.get(f'variant-{index}-sku', '').strip()
        color = post_data.get(f'variant-{index}-color', '').strip()
        stock = post_data.get(f'variant-{index}-stock', '0').strip()

        if True:  # Always process the row
            try:
                stock_val = int(stock)
            except (ValueError, TypeError):
                stock_val = 0

            # Check if variant with this SKU already exists (for edits)
            if sku:
                variant = ProductVariant.objects.filter(sku=sku).first()
            else:
                variant = None

            if variant and variant.product_id == product.id:
                # Update existing variant
                variant.color = color
                variant.stock = stock_val
                variant.save()
            else:
                # Create new variant with auto-generated SKU
                ProductVariant.objects.create(
                    product=product,
                    sku=sku if sku else _generate_sku(),
                    color=color,
                    stock=stock_val,
                )

        index += 1


@login_required
def add_product(request):
    """Add a new product (seller only)."""
    if request.user.profile.role != 'S':
        messages.error(request, "Only sellers can add products.")
        return redirect('profile')

    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            product = form.save(commit=False)
            product.seller = request.user

            # Handle category & brand
            product.category = _handle_category(form.cleaned_data['category_name'].strip())
            product.brand = _handle_brand(form.cleaned_data['brand_name'].strip())

            # Generate a unique slug
            base_slug = slugify(product.name)
            slug = base_slug
            counter = 1
            while Product.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            product.slug = slug
            product.save()

            # Save images
            _save_images(product, form.cleaned_data.get('images'))

            # Save variants
            _save_variants(product, request.POST)

            messages.success(request, f"Product '{product.name}' was successfully added!")
            return redirect('products:my_shop')
    else:
        form = ProductForm()

    variant_form = ProductVariantForm()
    return render(request, 'products/product_form.html', {
        'form': form,
        'variant_form': variant_form,
        'mode': 'add',
    })


@login_required
def my_shop(request):
    """Seller dashboard — view all own products, edit or add new ones."""
    if request.user.profile.role != 'S':
        messages.error(request, "Only sellers can access the shop dashboard.")
        return redirect('products:home')

    products = (
        Product.objects
        .filter(seller=request.user)
        .select_related("category", "brand")
        .prefetch_related("images", "variants")
        .order_by("-created_at")
    )
    return render(request, 'products/my_shop.html', {
        'products': products,
        'product_count': products.count(),
    })


@login_required
def edit_product(request, slug):
    """Allow a seller to edit one of their own products."""
    product = get_object_or_404(Product, slug=slug, seller=request.user)

    if request.user.profile.role != 'S':
        messages.error(request, "Only sellers can edit products.")
        return redirect('products:home')

    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            updated = form.save(commit=False)

            # Handle category & brand
            updated.category = _handle_category(form.cleaned_data['category_name'].strip())
            updated.brand = _handle_brand(form.cleaned_data['brand_name'].strip())

            updated.save()

            # Append any newly uploaded images
            _save_images(updated, form.cleaned_data.get('images'))

            # Save variants
            _save_variants(updated, request.POST)

            messages.success(request, f"Product '{updated.name}' was updated successfully!")
            return redirect('products:my_shop')
    else:
        initial = {
            'category_name': product.category.name if product.category else '',
            'brand_name': product.brand.name if product.brand else '',
        }
        form = ProductForm(instance=product, initial=initial)

    variant_form = ProductVariantForm()
    return render(request, 'products/product_form.html', {
        'form': form,
        'variant_form': variant_form,
        'product': product,
        'mode': 'edit',
    })


@login_required
def product_delete(request, slug):
    """Allow a seller to delete one of their own products."""
    product = get_object_or_404(Product, slug=slug, seller=request.user)

    if request.user.profile.role != 'S':
        messages.error(request, "Only sellers can delete products.")
        return redirect('products:home')

    product_name = product.name

    # Delete image files from disk before removing DB records
    for img in product.images.all():
        if img.image and img.image.storage.exists(img.image.name):
            img.image.delete(save=False)

    product.delete()
    messages.success(request, f"Product '{product_name}' was deleted successfully!")
    return redirect('products:my_shop')