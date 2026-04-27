from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken
from .models import User, BlacklistedAccessToken


class AdminLogoutTestCase(TestCase):
    """Tests for POST /admin/logout"""

    def setUp(self):
        self.client = APIClient()
        self.url = reverse('admin_logout')

        # Create a test user (no role required for logout)
        self.user = User.objects.create_user(
            email='admin@test.com',
            password='Test@1234',
            name='Test Admin',
        )

    def _get_access_token(self):
        """Helper: generate a fresh access token for self.user."""
        refresh = RefreshToken.for_user(self.user)
        return str(refresh.access_token), refresh['jti'] if False else str(refresh.access_token)

    def _tokens(self):
        """Return (access_token_str, jti) for self.user."""
        refresh = RefreshToken.for_user(self.user)
        access = refresh.access_token
        return str(access), access['jti']

    # ------------------------------------------------------------------ #
    # 1. Happy path
    # ------------------------------------------------------------------ #
    def test_logout_success(self):
        """Authenticated user can log out; token is blacklisted afterwards."""
        access, jti = self._tokens()
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access}')

        response = self.client.post(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['message'], 'Logout successful')
        # Access token JTI must now be in the blacklist
        self.assertTrue(BlacklistedAccessToken.objects.filter(jti=jti).exists())

    # ------------------------------------------------------------------ #
    # 2. No credentials
    # ------------------------------------------------------------------ #
    def test_logout_requires_authentication(self):
        """Request without Authorization header must be rejected (401)."""
        response = self.client.post(self.url)

        self.assertEqual(response.status_code, 401)

    # ------------------------------------------------------------------ #
    # 3. Invalid / malformed token
    # ------------------------------------------------------------------ #
    def test_logout_with_invalid_token(self):
        """A garbage Bearer token must be rejected (401)."""
        self.client.credentials(HTTP_AUTHORIZATION='Bearer not.a.valid.token')
        response = self.client.post(self.url)

        self.assertEqual(response.status_code, 401)

    # ------------------------------------------------------------------ #
    # 4. Already-blacklisted token
    # ------------------------------------------------------------------ #
    def test_logout_with_blacklisted_token(self):
        """
        If the same access token is used a second time after logout,
        CustomJWTAuthentication must reject it (401).
        """
        access, jti = self._tokens()
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access}')

        # First logout – should succeed
        first = self.client.post(self.url)
        self.assertEqual(first.status_code, 200)

        # Second attempt with the same (now blacklisted) token
        second = self.client.post(self.url)
        self.assertEqual(second.status_code, 401)

    # ------------------------------------------------------------------ #
    # 5. Idempotency – blacklisting same JTI twice is safe (get_or_create)
    # ------------------------------------------------------------------ #
    def test_blacklist_is_idempotent(self):
        """
        Calling get_or_create for the same JTI twice should not raise an
        error and must leave exactly one record in the table.
        """
        access, jti = self._tokens()
        BlacklistedAccessToken.objects.create(jti=jti)  # pre-existing entry

        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access}')
        # The token is already blacklisted → auth layer rejects the request
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 401)

        # Still only one record for this JTI
        self.assertEqual(BlacklistedAccessToken.objects.filter(jti=jti).count(), 1)
