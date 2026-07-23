from django import forms
# pyrefly: ignore [missing-import]
from django_countries.widgets import CountrySelectWidget
from .models import Order


class CheckoutForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = [
            "email",
            "first_name",
            "last_name",
            "phone",
            "street_address",
            "city",
            "state",
            "postal_code",
            "country",
            "payment_method",
        ]
        widgets = {
            "email": forms.EmailInput(attrs={"class": "form-input", "placeholder": "your.email@example.com"}),
            "first_name": forms.TextInput(attrs={"class": "form-input", "placeholder": "First Name"}),
            "last_name": forms.TextInput(attrs={"class": "form-input", "placeholder": "Last Name"}),
            "phone": forms.TextInput(attrs={"class": "form-input", "placeholder": "+92 300 1234567"}),
            "street_address": forms.TextInput(attrs={"class": "form-input", "placeholder": "House/Street address"}),
            "city": forms.TextInput(attrs={"class": "form-input", "placeholder": "City"}),
            "state": forms.TextInput(attrs={"class": "form-input", "placeholder": "State / Province"}),
            "postal_code": forms.TextInput(attrs={"class": "form-input", "placeholder": "Postal Code"}),
            "country": CountrySelectWidget(attrs={"class": "form-input"}),
            "payment_method": forms.RadioSelect(),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        
        # Pre-fill from user profile if user is authenticated and form is unbound
        if user and user.is_authenticated and not self.is_bound:
            self.fields["email"].initial = user.email
            if hasattr(user, "first_name") and user.first_name:
                self.fields["first_name"].initial = user.first_name
            if hasattr(user, "last_name") and user.last_name:
                self.fields["last_name"].initial = user.last_name
                
            if hasattr(user, "profile"):
                profile = user.profile
                if profile.street_address:
                    self.fields["street_address"].initial = profile.street_address
                if profile.city:
                    self.fields["city"].initial = profile.city
                if profile.state:
                    self.fields["state"].initial = profile.state
                if profile.postal_code:
                    self.fields["postal_code"].initial = profile.postal_code
                if profile.country:
                    self.fields["country"].initial = profile.country
