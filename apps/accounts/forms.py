# pyrefly: ignore [missing-import]
from allauth.account.forms import LoginForm
from django.contrib.auth import get_user_model
from django import forms
from django.utils.translation import gettext_lazy as _

User = get_user_model()

class CustomLoginForm(LoginForm):
    def clean(self):
        # We need to get the "login" field, which could be email
        login = self.cleaned_data.get("login")
        if login:
            users = User.objects.filter(email__iexact=login)
            if not users.exists():
                raise forms.ValidationError(_("Does not have an account."))
        
        # Proceed with the default clean method which will check password
        return super().clean()

class ProfileUpdateForm(forms.ModelForm):
    first_name = forms.CharField(max_length=30, required=False)
    last_name = forms.CharField(max_length=30, required=False)

    class Meta:
        from .models import Profile
        model = Profile
        fields = ['avatar', 'bio', 'street_address', 'city', 'state', 'postal_code', 'country']

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if self.user:
            self.fields['first_name'].initial = self.user.first_name
            self.fields['last_name'].initial = self.user.last_name
            
        # Add Tailwind styling to the country select dropdown
        self.fields['country'].widget.attrs.update({
            'class': 'block w-full rounded-md border-0 py-1.5 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 focus:ring-2 focus:ring-inset focus:ring-indigo-600 sm:max-w-xs sm:text-sm sm:leading-6 px-3'
        })

    def save(self, commit=True):
        profile = super().save(commit=False)
        if self.user:
            self.user.first_name = self.cleaned_data.get('first_name')
            self.user.last_name = self.cleaned_data.get('last_name')
            if commit:
                self.user.save()
        if commit:
            profile.save()
        return profile

class ShopSetupForm(forms.ModelForm):
    class Meta:
        from .models import Profile
        model = Profile
        fields = ['shop_name', 'shop_description']
