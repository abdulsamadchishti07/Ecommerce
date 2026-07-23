from django import forms
from .models import Product, ProductVariant, Category, Brand
from django.utils.text import slugify


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True

    def value_from_datadict(self, data, files, name):
        if hasattr(files, 'getlist'):
            return files.getlist(name)
        else:
            return files.get(name)


class MultipleFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            result = [single_file_clean(d, initial) for d in data]
        else:
            result = [single_file_clean(data, initial)]
        return result


class ProductForm(forms.ModelForm):
    category_name = forms.CharField(max_length=50, required=True, help_text="Type a category name")
    brand_name = forms.CharField(max_length=50, required=False, help_text="Type a brand name (optional)")
    images = MultipleFileField(required=False, help_text="Select one or more images")

    class Meta:
        model = Product
        fields = ['name', 'description', 'price', 'old_price', 'is_active']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Tailwind styling for text inputs
        text_classes = 'block w-full rounded-md border-0 py-1.5 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-indigo-600 sm:text-sm sm:leading-6 px-3'

        self.fields['name'].widget.attrs.update({'class': text_classes, 'placeholder': 'e.g., Wireless Headphones'})
        self.fields['description'].widget.attrs.update({'class': text_classes, 'rows': 4, 'placeholder': 'Describe your product...'})
        self.fields['price'].widget.attrs.update({'class': text_classes, 'placeholder': '0.00 (optional if Original Price is set)'})
        self.fields['old_price'].widget.attrs.update({'class': text_classes, 'placeholder': '0.00'})
        self.fields['category_name'].widget.attrs.update({'class': text_classes, 'placeholder': 'e.g., Electronics'})
        self.fields['brand_name'].widget.attrs.update({'class': text_classes, 'placeholder': 'e.g., Sony'})
        self.fields['images'].widget.attrs.update({'class': 'block w-full text-sm text-gray-900 border border-gray-300 rounded-lg cursor-pointer bg-gray-50 focus:outline-none file:mr-4 file:py-2 file:px-4 file:border-0 file:text-sm file:font-semibold file:bg-indigo-50 file:text-indigo-700 hover:file:bg-indigo-100'})

        # Make sale price optional
        self.fields['price'].required = False
        self.fields['old_price'].required = False

    def clean(self):
        cleaned_data = super().clean()
        price = cleaned_data.get('price')
        old_price = cleaned_data.get('old_price')

        if price is None and old_price is None:
            self.add_error('price', "Please enter an Original Price or a Sale Price.")
            self.add_error('old_price', "Please enter an Original Price or a Sale Price.")
            return cleaned_data

        # If only old_price is provided (no discount/sale price)
        if price is None and old_price is not None:
            cleaned_data['price'] = old_price
            cleaned_data['old_price'] = None
        # If both price (sale price) and old_price (original price) are provided
        elif price is not None and old_price is not None:
            if price >= old_price:
                self.add_error('price', "Sale price must be smaller than the original price.")
                self.add_error('old_price', "Original price must be greater than the sale price.")

        return cleaned_data


class ProductVariantForm(forms.ModelForm):
    """Form for a single product variant (SKU, size, color, stock, price override)."""

    class Meta:
        model = ProductVariant
        fields = ['sku', 'size', 'color', 'stock', 'price_override']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        text_classes = 'block w-full rounded-md border-0 py-1.5 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-indigo-600 sm:text-sm sm:leading-6 px-3'

        self.fields['sku'].widget.attrs.update({'class': text_classes, 'placeholder': 'e.g., SKU-001'})
        self.fields['size'].widget.attrs.update({'class': text_classes, 'placeholder': 'e.g., Medium'})
        self.fields['color'].widget.attrs.update({'class': text_classes, 'placeholder': 'e.g., Black'})
        self.fields['stock'].widget.attrs.update({'class': text_classes, 'placeholder': '0'})
        self.fields['price_override'].widget.attrs.update({'class': text_classes, 'placeholder': 'Leave blank to use product price'})
        self.fields['price_override'].required = False
        self.fields['size'].required = False
        self.fields['color'].required = False
