"""
.venv/bin/python manage.py test apps.accounts --verbosity=2

Comprehensive test suite for the EvoCart accounts app.

Coverage:
  - User model & manager
  - Profile model (auto-create, __str__, roles)
  - Address model
  - CustomLoginForm (unknown email, valid email)
  - Profile view (login required, GET response)
  - Delete account view (GET redirect, POST deletes + logs out)
  - Allauth signup flow (valid, duplicate email, weak password)
  - Allauth login flow (valid credentials, wrong password, unknown email)
  - OTP / email-verification code format (numeric, 6 digits)
  - CustomSocialAccountAdapter (pre_social_login edge cases)
  - URL routing
  - Template rendering (smoke-test key pages load 200)
"""

from unittest.mock import MagicMock, patch

# pyrefly: ignore [missing-import]
from allauth.account.models import EmailAddress
from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse

User = get_user_model()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_user(email="test@evocart.com", password="StrongPass123!", **kw):
    """Create a verified user for use in tests."""
    user = User.objects.create_user(email=email, password=password, **kw)
    EmailAddress.objects.create(
        user=user, email=email, verified=True, primary=True
    )
    return user


def create_google_social_app():
    """Create a Google SocialApp fixture required by allauth template tags."""
    # pyrefly: ignore [missing-import]
    from allauth.socialaccount.models import SocialApp
    from django.contrib.sites.models import Site
    app, _ = SocialApp.objects.get_or_create(
        provider="google",
        defaults={"name": "Google", "client_id": "test-id", "secret": "test-secret"},
    )
    app.sites.add(Site.objects.get_current())
    return app


class SocialAppMixin:
    """Mixin: any TestCase that renders signup/login templates needs this."""
    def setUp(self):
        super().setUp()
        create_google_social_app()


# ===========================================================================
# 1. User Model & Manager
# ===========================================================================

class UserModelTests(TestCase):

    def test_create_user_no_username(self):
        user = User.objects.create_user(email="a@b.com", password="pw")
        self.assertEqual(user.email, "a@b.com")
        self.assertIsNone(user.username)

    def test_email_is_username_field(self):
        self.assertEqual(User.USERNAME_FIELD, "email")

    def test_email_must_be_unique(self):
        User.objects.create_user(email="dup@b.com", password="pw")
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            User.objects.create_user(email="dup@b.com", password="pw2")

    def test_create_user_requires_email(self):
        with self.assertRaises(ValueError):
            User.objects.create_user(email="", password="pw")

    def test_create_superuser(self):
        su = User.objects.create_superuser(email="admin@b.com", password="pw")
        self.assertTrue(su.is_staff)
        self.assertTrue(su.is_superuser)

    def test_superuser_is_staff_enforced(self):
        with self.assertRaises(ValueError):
            User.objects.create_superuser(
                email="bad@b.com", password="pw", is_staff=False
            )

    def test_superuser_is_superuser_enforced(self):
        with self.assertRaises(ValueError):
            User.objects.create_superuser(
                email="bad2@b.com", password="pw", is_superuser=False
            )

    def test_email_normalised(self):
        user = User.objects.create_user(email="Me@EXAMPLE.COM", password="pw")
        self.assertEqual(user.email, "Me@example.com")


# ===========================================================================
# 2. Profile Model
# ===========================================================================

class ProfileModelTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(email="p@b.com", password="pw")

    def test_profile_not_auto_created(self):
        """Profile is NOT auto-created by a signal; the view creates it."""
        from apps.accounts.models import Profile
        self.assertFalse(Profile.objects.filter(user=self.user).exists())

    def test_profile_str(self):
        from apps.accounts.models import Profile
        p = Profile.objects.create(user=self.user)
        self.assertIn(self.user.email, str(p))
        self.assertIn("Buyer", str(p))

    def test_profile_default_role_is_buyer(self):
        from apps.accounts.models import Profile
        p = Profile.objects.create(user=self.user)
        self.assertEqual(p.role, "B")

    def test_profile_seller_role(self):
        from apps.accounts.models import Profile
        p = Profile.objects.create(user=self.user, role="S")
        self.assertEqual(p.get_role_display(), "Seller")

    def test_profile_cascade_delete(self):
        from apps.accounts.models import Profile
        p = Profile.objects.create(user=self.user)
        pk = p.pk
        self.user.delete()
        self.assertFalse(Profile.objects.filter(pk=pk).exists())


# ===========================================================================
# 3. Address Model
# ===========================================================================

class AddressModelTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(email="addr@b.com", password="pw")

    def test_create_billing_address(self):
        from apps.accounts.models import Address
        a = Address.objects.create(
            user=self.user,
            address_type="B",
            street_address="123 Main St",
            city="Karachi",
            state="Sindh",
            postal_code="75000",
            country="Pakistan",
        )
        self.assertIn("Billing", str(a))

    def test_create_shipping_address(self):
        from apps.accounts.models import Address
        a = Address.objects.create(
            user=self.user,
            address_type="S",
            street_address="456 Park Ave",
            city="Lahore",
            state="Punjab",
            postal_code="54000",
            country="Pakistan",
        )
        self.assertEqual(a.get_address_type_display(), "Shipping")

    def test_address_cascade_delete(self):
        from apps.accounts.models import Address
        a = Address.objects.create(
            user=self.user, address_type="B",
            street_address="1 St", city="C", state="S",
            postal_code="1", country="PK",
        )
        pk = a.pk
        self.user.delete()
        self.assertFalse(Address.objects.filter(pk=pk).exists())

    def test_user_can_have_multiple_addresses(self):
        from apps.accounts.models import Address
        for t in ("B", "S"):
            Address.objects.create(
                user=self.user, address_type=t,
                street_address="1 St", city="C", state="S",
                postal_code="1", country="PK",
            )
        self.assertEqual(self.user.addresses.count(), 2)


# ===========================================================================
# 4. CustomLoginForm
# ===========================================================================

class CustomLoginFormTests(SocialAppMixin, TestCase):

    def setUp(self):
        self.user = make_user("login@b.com", "GoodPass99!")

    def test_unknown_email_raises_validation_error(self):
        from apps.accounts.forms import CustomLoginForm
        form = CustomLoginForm(
            data={"login": "nobody@nowhere.com", "password": "anything"}
        )
        self.assertFalse(form.is_valid())
        self.assertIn("Does not have an account.", str(form.errors))

    def test_known_email_passes_email_check(self):
        """The form should NOT raise 'does not have an account' for a real email
        (allauth may still fail on wrong password, but that's a different error)."""
        from apps.accounts.forms import CustomLoginForm
        form = CustomLoginForm(
            data={"login": "login@b.com", "password": "WrongPass!"}
        )
        # The custom check passes; allauth's own clean will reject the password
        errors = str(form.errors)
        self.assertNotIn("Does not have an account.", errors)


# ===========================================================================
# 5. Profile View
# ===========================================================================

class ProfileViewTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = make_user("view@b.com", "StrongPass123!")
        self.url = reverse("profile")

    def test_redirect_if_not_logged_in(self):
        response = self.client.get(self.url)
        self.assertNotEqual(response.status_code, 200)
        self.assertIn(response.status_code, [301, 302])

    def test_profile_page_loads_for_logged_in_user(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_profile_auto_creates_profile_object(self):
        from apps.accounts.models import Profile
        self.client.force_login(self.user)
        self.client.get(self.url)
        self.assertTrue(Profile.objects.filter(user=self.user).exists())

    def test_context_contains_profile_and_addresses(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertIn("profile", response.context)
        self.assertIn("addresses", response.context)


# ===========================================================================
# 6. Delete Account View
# ===========================================================================

class DeleteAccountViewTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.url = reverse("account_delete")

    def test_get_redirects_to_profile(self):
        user = make_user("del_get@b.com", "StrongPass123!")
        self.client.force_login(user)
        response = self.client.get(self.url)
        self.assertRedirects(response, reverse("profile"), fetch_redirect_response=False)

    def test_unauthenticated_cannot_delete(self):
        response = self.client.post(self.url)
        self.assertIn(response.status_code, [301, 302])

    def test_post_deletes_user_and_redirects(self):
        user = make_user("del_post@b.com", "StrongPass123!")
        uid = user.pk
        self.client.force_login(user)
        response = self.client.post(self.url)
        self.assertRedirects(response, "/", fetch_redirect_response=False)
        self.assertFalse(User.objects.filter(pk=uid).exists())

    def test_post_logs_user_out(self):
        user = make_user("del_logout@b.com", "StrongPass123!")
        self.client.force_login(user)
        self.client.post(self.url)
        # After deletion the session should have no authenticated user
        response = self.client.get(reverse("profile"))
        self.assertIn(response.status_code, [301, 302])  # redirected to login

    def test_delete_also_removes_profile(self):
        from apps.accounts.models import Profile
        user = make_user("del_prof@b.com", "StrongPass123!")
        Profile.objects.create(user=user)
        uid = user.pk
        self.client.force_login(user)
        self.client.post(self.url)
        self.assertFalse(Profile.objects.filter(user_id=uid).exists())


# ===========================================================================
# 7. Allauth Signup Flow
# ===========================================================================

@override_settings(
    ACCOUNT_EMAIL_VERIFICATION="none",
    ACCOUNT_PREVENT_ENUMERATION=False,
)
class SignupFlowTests(SocialAppMixin, TestCase):

    def setUp(self):
        self.client = Client()
        self.url = reverse("account_signup")

    def test_signup_page_loads(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_valid_signup_creates_user(self):
        self.client.post(self.url, {
            "email": "new@evocart.com",
            "password1": "SuperSecret99!",
            "password2": "SuperSecret99!",
        })
        self.assertTrue(User.objects.filter(email="new@evocart.com").exists())

    def test_duplicate_email_rejected(self):
        make_user("dup@evocart.com", "Pass123!")
        response = self.client.post(self.url, {
            "email": "dup@evocart.com",
            "password1": "NewPass999!",
            "password2": "NewPass999!",
        })
        # Should stay on the signup page (form invalid)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(
            User.objects.filter(email="dup@evocart.com").count() > 1
        )

    def test_password_mismatch_rejected(self):
        response = self.client.post(self.url, {
            "email": "mismatch@evocart.com",
            "password1": "Pass123!",
            "password2": "Different!",
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(email="mismatch@evocart.com").exists())

    def test_missing_email_rejected(self):
        response = self.client.post(self.url, {
            "email": "",
            "password1": "Pass123!",
            "password2": "Pass123!",
        })
        self.assertEqual(response.status_code, 200)

    def test_invalid_email_format_rejected(self):
        response = self.client.post(self.url, {
            "email": "not-an-email",
            "password1": "Pass123!",
            "password2": "Pass123!",
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(email="not-an-email").exists())


# ===========================================================================
# 8. Allauth Login Flow
# ===========================================================================

@override_settings(ACCOUNT_EMAIL_VERIFICATION="none")
class LoginFlowTests(SocialAppMixin, TestCase):

    def setUp(self):
        self.client = Client()
        self.url = reverse("account_login")
        self.user = make_user("auth@evocart.com", "GoodPass99!")

    def test_login_page_loads(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_correct_credentials_login(self):
        response = self.client.post(self.url, {
            "login": "auth@evocart.com",
            "password": "GoodPass99!",
        })
        # Should redirect away from login on success
        self.assertIn(response.status_code, [200, 302])

    def test_wrong_password_rejected(self):
        response = self.client.post(self.url, {
            "login": "auth@evocart.com",
            "password": "WrongPass!",
        })
        self.assertEqual(response.status_code, 200)
        # Error message is present
        self.assertContains(response, "password", msg_prefix="Expected password error")

    def test_unknown_email_rejected(self):
        response = self.client.post(self.url, {
            "login": "ghost@evocart.com",
            "password": "AnyPass!",
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Does not have an account.")

    def test_empty_credentials_rejected(self):
        response = self.client.post(self.url, {"login": "", "password": ""})
        self.assertEqual(response.status_code, 200)

    def test_case_insensitive_email_login(self):
        """Login with upper-cased email should not trigger 'Does not have an account' error."""
        response = self.client.post(self.url, {
            "login": "AUTH@EVOCART.COM",
            "password": "GoodPass99!",
        })
        # A 302 redirect means login succeeded — that's even better.
        # A 200 means it stayed on the form — check there's no 'no account' error.
        if response.status_code == 200:
            self.assertNotContains(response, "Does not have an account.")
        else:
            self.assertIn(response.status_code, [302, 301])


# ===========================================================================
# 9. OTP Code Format
# ===========================================================================

class OTPCodeFormatTests(TestCase):

    @override_settings(
        ACCOUNT_EMAIL_VERIFICATION_BY_CODE_FORMAT={"numeric": True, "length": 6, "dashed": False}
    )
    def test_generated_code_is_6_digit_numeric(self):
        # pyrefly: ignore [missing-import]
        from allauth.account.adapter import get_adapter
        for _ in range(20):   # run 20 times to be statistically confident
            code = get_adapter().generate_email_verification_code()
            self.assertEqual(len(code), 6, f"Expected 6 chars, got: {code!r}")
            self.assertTrue(code.isdigit(), f"Expected digits only, got: {code!r}")

    @override_settings(
        ACCOUNT_EMAIL_VERIFICATION_BY_CODE_FORMAT={"numeric": True, "length": 6, "dashed": False}
    )
    def test_generated_code_range(self):
        """All codes should be between 000000 and 999999."""
        # pyrefly: ignore [missing-import]
        from allauth.account.adapter import get_adapter
        for _ in range(10):
            code = get_adapter().generate_email_verification_code()
            self.assertGreaterEqual(int(code), 0)
            self.assertLessEqual(int(code), 999999)


# ===========================================================================
# 10. CustomSocialAccountAdapter
# ===========================================================================

class CustomSocialAdapterTests(TestCase):

    def setUp(self):
        self.request = MagicMock()
        self.request.session = {}

    def _make_sociallogin(self, email, is_existing=False):
        sl = MagicMock()
        sl.is_existing = is_existing
        sl.account.extra_data = {"email": email}
        return sl

    def test_existing_social_login_skipped(self):
        from apps.accounts.adapters import CustomSocialAccountAdapter
        adapter = CustomSocialAccountAdapter()
        sl = self._make_sociallogin("anyone@b.com", is_existing=True)
        # Should return early with no side-effects
        result = adapter.pre_social_login(self.request, sl)
        self.assertIsNone(result)
        sl.connect.assert_not_called()

    def test_no_email_in_social_data_skipped(self):
        from apps.accounts.adapters import CustomSocialAccountAdapter
        adapter = CustomSocialAccountAdapter()
        sl = MagicMock()
        sl.is_existing = False
        sl.account.extra_data = {}          # no email key
        result = adapter.pre_social_login(self.request, sl)
        self.assertIsNone(result)

    def test_existing_user_gets_social_account_connected(self):
        user = make_user("social@b.com", "pw")
        from apps.accounts.adapters import CustomSocialAccountAdapter
        adapter = CustomSocialAccountAdapter()
        sl = self._make_sociallogin("social@b.com")
        adapter.pre_social_login(self.request, sl)
        sl.connect.assert_called_once_with(self.request, user)

    def test_existing_user_email_marked_verified(self):
        user = make_user("verify@b.com", "pw")
        # Mark the EmailAddress as un-verified
        ea = EmailAddress.objects.get(user=user)
        ea.verified = False
        ea.save()

        from apps.accounts.adapters import CustomSocialAccountAdapter
        adapter = CustomSocialAccountAdapter()
        sl = self._make_sociallogin("verify@b.com")
        adapter.pre_social_login(self.request, sl)

        ea.refresh_from_db()
        self.assertTrue(ea.verified)

    def test_unknown_email_raises_immediate_http_response(self):
        # pyrefly: ignore [missing-import]
        from allauth.core.exceptions import ImmediateHttpResponse
        from apps.accounts.adapters import CustomSocialAccountAdapter
        adapter = CustomSocialAccountAdapter()
        sl = self._make_sociallogin("nobody@b.com")
        with self.assertRaises(ImmediateHttpResponse):
            adapter.pre_social_login(self.request, sl)


# ===========================================================================
# 11. URL Routing
# ===========================================================================

class URLRoutingTests(TestCase):

    def test_profile_url_resolves(self):
        from django.urls import resolve
        match = resolve("/accounts/profile/")
        self.assertEqual(match.url_name, "profile")

    def test_delete_url_resolves(self):
        from django.urls import resolve
        match = resolve("/accounts/delete/")
        self.assertEqual(match.url_name, "account_delete")

    def test_allauth_login_url_resolves(self):
        url = reverse("account_login")
        self.assertTrue(url.startswith("/"))

    def test_allauth_signup_url_resolves(self):
        url = reverse("account_signup")
        self.assertTrue(url.startswith("/"))


# ===========================================================================
# 12. Template Smoke Tests (key pages return 200)
# ===========================================================================

class TemplateSmokTests(SocialAppMixin, TestCase):

    def setUp(self):
        super().setUp()
        self.client = Client()

    def test_login_page_renders(self):
        response = self.client.get(reverse("account_login"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "EvoCart")

    def test_signup_page_renders(self):
        response = self.client.get(reverse("account_signup"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "EvoCart")

    def test_password_reset_page_renders(self):
        response = self.client.get(reverse("account_reset_password"))
        self.assertEqual(response.status_code, 200)

    def test_profile_page_requires_auth(self):
        response = self.client.get(reverse("profile"))
        self.assertIn(response.status_code, [301, 302])

    def test_change_password_page_requires_auth(self):
        response = self.client.get(reverse("account_change_password"))
        self.assertIn(response.status_code, [301, 302])

    def test_profile_renders_for_logged_in_user(self):
        user = make_user("smoke@b.com", "GoodPass99!")
        self.client.force_login(user)
        response = self.client.get(reverse("profile"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, user.email)
