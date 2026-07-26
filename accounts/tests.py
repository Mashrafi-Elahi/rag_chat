from django.test import TestCase

# Create your tests here.
from rest_framework import status
from rest_framework.test import APITestCase

from .models import User


class AccountsApiSmokeTests(APITestCase):
    register_url = "/api/accounts/register/"
    login_url = "/api/accounts/login/"
    forgot_password_url = "/api/accounts/forgot-password/"
    change_password_url = "/api/accounts/change-password/"
    profile_url = "/api/accounts/profile/"
    logout_url = "/api/accounts/logout/"

    email = "smoke@example.com"
    password = "StrongPassword123!"
    new_password = "NewStrongPassword456!"

    def create_user(self):
        return User.objects.create_user(
            email=self.email,
            password=self.password,
            full_name="Smoke User",
        )

    def login(self, password=None):
        response = self.client.post(
            self.login_url,
            {
                "email": self.email,
                "password": password or self.password,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        return response.data["tokens"]

    def authenticate(self, access_token):
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {access_token}"
        )

    def test_register(self):
        response = self.client.post(
            self.register_url,
            {
                "email": self.email,
                "password": self.password,
                "full_name": "Smoke User",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.filter(email=self.email).exists())
        self.assertIn("access", response.data["tokens"])
        self.assertIn("refresh", response.data["tokens"])

    def test_duplicate_registration_is_rejected(self):
        self.create_user()

        response = self.client.post(
            self.register_url,
            {
                "email": self.email.upper(),
                "password": self.password,
                "full_name": "Duplicate User",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_and_invalid_login(self):
        self.create_user()

        valid_response = self.client.post(
            self.login_url,
            {"email": self.email, "password": self.password},
            format="json",
        )
        invalid_response = self.client.post(
            self.login_url,
            {"email": self.email, "password": "WrongPassword123!"},
            format="json",
        )

        self.assertEqual(valid_response.status_code, status.HTTP_200_OK)
        self.assertEqual(invalid_response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_forgot_password_has_generic_response(self):
        response = self.client.post(
            self.forgot_password_url,
            {"email": "unknown@example.com"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("message", response.data)

    def test_change_password(self):
        user = self.create_user()
        tokens = self.login()
        self.authenticate(tokens["access"])

        response = self.client.post(
            self.change_password_url,
            {
                "old_password": self.password,
                "new_password": self.new_password,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        user.refresh_from_db()
        self.assertTrue(user.check_password(self.new_password))
        self.assertFalse(user.check_password(self.password))

    def test_profile_get_and_patch(self):
        self.create_user()
        tokens = self.login()
        self.authenticate(tokens["access"])

        get_response = self.client.get(self.profile_url)
        patch_response = self.client.patch(
            self.profile_url,
            {"full_name": "Updated Smoke User"},
            format="json",
        )

        self.assertEqual(get_response.status_code, status.HTTP_200_OK)
        self.assertEqual(patch_response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            patch_response.data["full_name"],
            "Updated Smoke User",
        )

    def test_logout(self):
        self.create_user()
        tokens = self.login()
        self.authenticate(tokens["access"])

        response = self.client.post(
            self.logout_url,
            {"refresh": tokens["refresh"]},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_delete_account(self):
        self.create_user()
        tokens = self.login()
        self.authenticate(tokens["access"])

        response = self.client.delete(self.profile_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(User.objects.filter(email=self.email).exists())