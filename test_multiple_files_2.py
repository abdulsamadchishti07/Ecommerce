import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.base')
django.setup()

from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils.datastructures import MultiValueDict
from apps.products.forms import ProductForm

files = MultiValueDict({
    'images': [
        SimpleUploadedFile("file1.jpg", b"file_content_1", content_type="image/jpeg"),
    ]
})

data = {
    'name': 'Test Product',
    'description': 'Test',
    'price': '10.00',
    'category_name': 'Test Cat',
    'brand_name': 'Test Brand'
}

form = ProductForm(data=data, files=files)
print("Is valid?", form.is_valid())
if not form.is_valid():
    print("Errors:", form.errors)
