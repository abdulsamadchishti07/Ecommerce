from django.shortcuts import render, get_object_or_404
from .models import Product, Category


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

from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.utils.text import slugify
from django.contrib import messages
from .forms import ProductForm
from .models import Brand, ProductImage

@login_required
def add_product(request):
    # Only allow sellers to add products
    if request.user.profile.role != 'S':
        messages.error(request, "Only sellers can add products.")
        return redirect('profile')
        
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            product = form.save(commit=False)
            product.seller = request.user
            
            # Handle dynamic category
            cat_name = form.cleaned_data['category_name'].strip()
            category = Category.objects.filter(name__iexact=cat_name).first()
            if not category:
                cat_slug = slugify(cat_name)
                counter = 1
                while Category.objects.filter(slug=cat_slug).exists():
                    cat_slug = f"{slugify(cat_name)}-{counter}"
                    counter += 1
                category = Category.objects.create(name=cat_name, slug=cat_slug)
            product.category = category

            # Handle dynamic brand
            brand_name = form.cleaned_data['brand_name'].strip()
            if brand_name:
                brand = Brand.objects.filter(name__iexact=brand_name).first()
                if not brand:
                    brand_slug = slugify(brand_name)
                    counter = 1
                    while Brand.objects.filter(slug=brand_slug).exists():
                        brand_slug = f"{slugify(brand_name)}-{counter}"
                        counter += 1
                    brand = Brand.objects.create(name=brand_name, slug=brand_slug)
                product.brand = brand
            
            # Generate a unique slug based on the product name
            base_slug = slugify(product.name)
            slug = base_slug
            counter = 1
            while Product.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            product.slug = slug
            product.save()
            
            # Save uploaded images
            images = form.cleaned_data.get('images')
            if images:
                for i, image in enumerate(images):
                    ProductImage.objects.create(
                        product=product,
                        image=image,
                        is_primary=(i == 0)
                    )
                
            messages.success(request, f"Product '{product.name}' was successfully added!")
            return redirect('products:product_detail', slug=product.slug)
    else:
        form = ProductForm()
        
    return render(request, 'products/product_form.html', {'form': form})