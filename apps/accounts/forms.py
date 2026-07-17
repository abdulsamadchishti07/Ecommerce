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
