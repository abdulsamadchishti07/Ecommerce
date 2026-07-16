# pyrefly: ignore [missing-import]
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
# pyrefly: ignore [missing-import]
from allauth.account.models import EmailAddress
from django.contrib.auth import get_user_model

User = get_user_model()

class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    def pre_social_login(self, request, sociallogin):
        # If the social account is already linked, do nothing
        if sociallogin.is_existing:
            return

        # Check if an email is provided by the social provider (Google always verifies/provides it)
        email = sociallogin.account.extra_data.get('email')
        if not email:
            return

        # Try to find a user with this email
        try:
            user = User.objects.get(email__iexact=email)
            
            # Connect the social login to the existing user
            sociallogin.connect(request, user)
            
            # Ensure the EmailAddress object exists for this user and mark it verified
            email_address, created = EmailAddress.objects.get_or_create(
                user=user,
                email=user.email,
                defaults={'verified': True}
            )
            if not email_address.verified:
                email_address.verified = True
                email_address.save()
                
        except User.DoesNotExist:
            pass
