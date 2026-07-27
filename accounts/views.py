from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from .serializers import (
    ChangePasswordSerializer,
    ForgotPasswordSerializer,
    LoginSerializer,
    LogoutSerializer,
    ProfileUpdateSerializer,
    SignupSerializer,
    UserSerializer,
)

# ---------------------------------------------------------------------------
# Reusable Swagger response schemas
# ---------------------------------------------------------------------------
_token_schema = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        "access": openapi.Schema(type=openapi.TYPE_STRING, description="JWT access token"),
        "refresh": openapi.Schema(type=openapi.TYPE_STRING, description="JWT refresh token"),
    },
)

_user_schema = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        "id": openapi.Schema(type=openapi.TYPE_INTEGER),
        "email": openapi.Schema(type=openapi.TYPE_STRING, format="email"),
        "full_name": openapi.Schema(type=openapi.TYPE_STRING),
        "date_joined": openapi.Schema(type=openapi.TYPE_STRING, format="date-time"),
    },
)

_auth_response_schema = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        "message": openapi.Schema(type=openapi.TYPE_STRING),
        "user": _user_schema,
        "tokens": _token_schema,
    },
)

_message_schema = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        "message": openapi.Schema(type=openapi.TYPE_STRING),
    },
)

_401_response = openapi.Response(
    description="Authentication required. Include `Authorization: Bearer <access_token>`.",
)
_400_response = openapi.Response(description="Validation error.")


# ---------------------------------------------------------------------------
# Authentication APIs
# ---------------------------------------------------------------------------

class SignupView(APIView):
    """
    POST /api/accounts/register/

    Create a new user account with email, password, and optional full_name.
    Returns JWT access and refresh tokens on success.
    """

    permission_classes = [AllowAny]

    @swagger_auto_schema(
        tags=["Authentication"],
        operation_id="auth_register",
        operation_summary="Register a new user",
        operation_description=(
            "Create an account with **email**, **password**, and an optional **full_name**.\n\n"
            "On success, returns the created user data along with JWT `access` and `refresh` tokens.\n\n"
            "No `Authorization` header is required for this endpoint."
        ),
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["email", "password"],
            properties={
                "email": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    format="email",
                    example="user@gmail.com",
                ),
                "password": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    format="password",
                    minLength=8,
                    example="Password123!",
                ),
                "full_name": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    example="Test User",
                ),
            },
        ),
        responses={
            201: openapi.Response(
                description="Account created successfully.",
                schema=_auth_response_schema,
                examples={
                    "application/json": {
                        "message": "Account created successfully.",
                        "user": {
                            "id": 1,
                            "email": "user@gmail.com",
                            "full_name": "Test User",
                            "date_joined": "2026-07-26T07:36:06Z",
                        },
                        "tokens": {
                            "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                            "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                        },
                    }
                },
            ),
            400: _400_response,
        },
        security=[],  # public — no auth required
    )
    def post(self, request):
        serializer = SignupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        refresh = RefreshToken.for_user(user)

        return Response(
            {
                "message": "Account created successfully.",
                "user": UserSerializer(user).data,
                "tokens": {
                    "access": str(refresh.access_token),
                    "refresh": str(refresh),
                },
            },
            status=status.HTTP_201_CREATED,
        )


class LoginView(APIView):
    """
    POST /api/accounts/login/

    Authenticate a user using email and password.
    Returns JWT access and refresh tokens on success.
    """

    permission_classes = [AllowAny]

    @swagger_auto_schema(
        tags=["Authentication"],
        operation_id="auth_login",
        operation_summary="Login",
        operation_description=(
            "Authenticate using **email** and **password**.\n\n"
            "Returns JWT `access` and `refresh` tokens.\n\n"
            "Use the `access` token in the `Authorization: Bearer <access_token>` header "
            "for all protected endpoints.\n\n"
            "No `Authorization` header is required for this endpoint."
        ),
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["email", "password"],
            properties={
                "email": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    format="email",
                    example="user@gmail.com",
                ),
                "password": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    format="password",
                    example="Password123!",
                ),
            },
        ),
        responses={
            200: openapi.Response(
                description="Login successful.",
                schema=_auth_response_schema,
                examples={
                    "application/json": {
                        "message": "Login successful.",
                        "user": {
                            "id": 1,
                            "email": "user@gmail.com",
                            "full_name": "Test User",
                            "date_joined": "2026-07-26T07:36:06Z",
                        },
                        "tokens": {
                            "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                            "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                        },
                    }
                },
            ),
            400: openapi.Response(description="Invalid email or password."),
        },
        security=[],  # public — no auth required
    )
    def post(self, request):
        serializer = LoginSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]

        refresh = RefreshToken.for_user(user)

        return Response(
            {
                "message": "Login successful.",
                "user": UserSerializer(user).data,
                "tokens": {
                    "access": str(refresh.access_token),
                    "refresh": str(refresh),
                },
            },
            status=status.HTTP_200_OK,
        )


class ForgotPasswordView(APIView):
    """
    POST /api/accounts/forgot-password/

    Request a password-reset link by email.
    Always returns a generic message (does not reveal whether the email exists).
    """

    permission_classes = [AllowAny]

    @swagger_auto_schema(
        tags=["Authentication"],
        operation_id="auth_forgot_password",
        operation_summary="Forgot password",
        operation_description=(
            "Request a password-reset email.\n\n"
            "A **generic response** is always returned — whether or not the email is registered — "
            "to prevent account enumeration.\n\n"
            "Email delivery is a placeholder for now.\n\n"
            "No `Authorization` header is required for this endpoint."
        ),
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["email"],
            properties={
                "email": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    format="email",
                    example="user@gmail.com",
                ),
            },
        ),
        responses={
            200: openapi.Response(
                description="Generic response sent regardless of whether the email exists.",
                schema=_message_schema,
                examples={
                    "application/json": {
                        "message": "Password reset email sent"
                    }
                },
            ),
            400: _400_response,
        },
        security=[],
    )
    def post(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Generic response — never reveal whether the account exists.
        # Wire real email delivery later without changing this API contract.
        return Response(
            {"message": "Password reset email sent"},
            status=status.HTTP_200_OK,
        )


class ChangePasswordView(APIView):
    """
    POST /api/accounts/change-password/

    Change the authenticated user's password.
    Requires a valid Bearer access token.
    """

    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        tags=["Authentication"],
        operation_id="auth_change_password",
        operation_summary="Change password",
        operation_description=(
            "Change the current user's password.\n\n"
            "**Authentication required** — include `Authorization: Bearer <access_token>` in the header.\n\n"
            "The `old_password` must match the current password. "
            "The `new_password` must be different and pass Django's password validators."
        ),
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["old_password", "new_password"],
            properties={
                "old_password": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    format="password",
                    example="Password123!",
                ),
                "new_password": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    format="password",
                    minLength=8,
                    example="NewPassword123!",
                ),
            },
        ),
        responses={
            200: openapi.Response(
                description="Password changed successfully.",
                schema=_message_schema,
                examples={
                    "application/json": {"message": "Password changed successfully"}
                },
            ),
            400: openapi.Response(description="Old password incorrect or new password fails validation."),
            401: _401_response,
        },
    )
    def post(self, request):
        serializer = ChangePasswordSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)

        request.user.set_password(serializer.validated_data["new_password"])
        request.user.save(update_fields=["password"])

        return Response(
            {"message": "Password changed successfully"},
            status=status.HTTP_200_OK,
        )


# ---------------------------------------------------------------------------
# User Profile APIs
# ---------------------------------------------------------------------------

class ProfileView(APIView):
    """
    GET    /api/accounts/profile/  → get current user's profile
    PATCH  /api/accounts/profile/  → update profile (full_name)
    DELETE /api/accounts/profile/  → delete the account permanently
    """

    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        tags=["User Profile"],
        operation_id="profile_get",
        operation_summary="Get profile",
        operation_description=(
            "Return the authenticated user's profile data.\n\n"
            "**Authentication required** — include `Authorization: Bearer <access_token>` in the header."
        ),
        responses={
            200: openapi.Response(
                description="User profile.",
                schema=_user_schema,
                examples={
                    "application/json": {
                        "id": 1,
                        "email": "user@gmail.com",
                        "full_name": "Test User",
                        "date_joined": "2026-07-26T07:36:06Z",
                    }
                },
            ),
            401: _401_response,
        },
    )
    def get(self, request):
        return Response(
            UserSerializer(request.user).data,
            status=status.HTTP_200_OK,
        )

    @swagger_auto_schema(
        tags=["User Profile"],
        operation_id="profile_update",
        operation_summary="Update profile",
        operation_description=(
            "Update the authenticated user's profile. Currently only **full_name** may be changed.\n\n"
            "**Authentication required** — include `Authorization: Bearer <access_token>` in the header."
        ),
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "full_name": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    example="Updated Name",
                ),
            },
        ),
        responses={
            200: openapi.Response(
                description="Profile updated.",
                schema=_user_schema,
                examples={
                    "application/json": {
                        "id": 1,
                        "email": "user@gmail.com",
                        "full_name": "Updated Name",
                        "date_joined": "2026-07-26T07:36:06Z",
                    }
                },
            ),
            400: _400_response,
            401: _401_response,
        },
    )
    def patch(self, request):
        serializer = ProfileUpdateSerializer(
            request.user,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            UserSerializer(request.user).data,
            status=status.HTTP_200_OK,
        )

    @swagger_auto_schema(
        tags=["User Profile"],
        operation_id="profile_delete",
        operation_summary="Delete account",
        operation_description=(
            "Permanently delete the authenticated user's account. **This action is irreversible.**\n\n"
            "**Authentication required** — include `Authorization: Bearer <access_token>` in the header."
        ),
        responses={
            200: openapi.Response(
                description="Account deleted.",
                schema=_message_schema,
                examples={
                    "application/json": {"message": "Account deleted successfully"}
                },
            ),
            401: _401_response,
        },
    )
    def delete(self, request):
        request.user.delete()
        return Response(
            {"message": "Account deleted successfully"},
            status=status.HTTP_200_OK,
        )


# ---------------------------------------------------------------------------
# Logout
# ---------------------------------------------------------------------------

class LogoutView(APIView):
    """
    POST /api/accounts/logout/

    Validate ownership of the refresh token and confirm logout.
    The client must delete its stored tokens after calling this endpoint.
    """

    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        tags=["Authentication"],
        operation_id="auth_logout",
        operation_summary="Logout",
        operation_description=(
            "Validate that the provided refresh token belongs to the current user.\n\n"
            "**Authentication required** — include `Authorization: Bearer <access_token>` in the header.\n\n"
            "After a successful response, the **client must delete** its stored access and refresh tokens. "
            "Server-side blacklisting is not used in this implementation."
        ),
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["refresh"],
            properties={
                "refresh": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="The JWT refresh token to invalidate.",
                    example="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                ),
            },
        ),
        responses={
            200: openapi.Response(
                description="Logout successful.",
                schema=_message_schema,
                examples={
                    "application/json": {"message": "Logout successful"}
                },
            ),
            400: openapi.Response(description="Invalid or expired refresh token."),
            401: _401_response,
        },
    )
    def post(self, request):
        serializer = LogoutSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)

        return Response(
            {"message": "Logout successful"},
            status=status.HTTP_200_OK,
        )
