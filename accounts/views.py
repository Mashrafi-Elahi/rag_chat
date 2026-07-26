from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiResponse,
    extend_schema,
)
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from .serializers import (
    AuthResponseSerializer,
    ChangePasswordSerializer,
    ForgotPasswordSerializer,
    LoginSerializer,
    LogoutSerializer,
    MessageResponseSerializer,
    ProfileUpdateSerializer,
    SignupSerializer,
    UserSerializer,
)


class SignupView(APIView):
    """Create a user and return JWT access/refresh tokens."""

    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Authentication"],
        summary="Register a user",
        description="Create an account using email, password, and an optional full name.",
        request=SignupSerializer,
        responses={
            201: AuthResponseSerializer,
            400: OpenApiResponse(description="Validation error."),
        },
        examples=[
            OpenApiExample(
                "Register request",
                value={
                    "email": "user@example.com",
                    "password": "StrongPassword123!",
                    "full_name": "Example User",
                },
                request_only=True,
            ),
            OpenApiExample(
                "Register response",
                value={
                    "message": "Account created successfully.",
                    "user": {
                        "id": 1,
                        "email": "user@example.com",
                        "full_name": "Example User",
                        "date_joined": "2026-07-26T07:36:06Z",
                    },
                    "tokens": {
                        "refresh": "jwt-refresh-token",
                        "access": "jwt-access-token",
                    },
                },
                response_only=True,
                status_codes=["201"],
            ),
        ],
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
                    "refresh": str(refresh),
                    "access": str(refresh.access_token),
                },
            },
            status=status.HTTP_201_CREATED,
        )


class LoginView(APIView):
    """Authenticate a user using email and password."""

    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Authentication"],
        summary="Login",
        description="Authenticate using email and password and return JWT tokens.",
        request=LoginSerializer,
        responses={
            200: AuthResponseSerializer,
            400: OpenApiResponse(description="Invalid credentials or invalid request."),
        },
        examples=[
            OpenApiExample(
                "Login request",
                value={
                    "email": "user@example.com",
                    "password": "StrongPassword123!",
                },
                request_only=True,
            ),
        ],
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
                    "refresh": str(refresh),
                    "access": str(refresh.access_token),
                },
            },
            status=status.HTTP_200_OK,
        )


class ForgotPasswordView(APIView):
    """Accept a password-reset request without revealing account existence."""

    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Authentication"],
        summary="Request a password reset",
        description=(
            "Accept a password-reset request. The same response is returned whether "
            "or not the email exists, preventing account discovery. Email delivery "
            "can be connected later without changing this API contract."
        ),
        request=ForgotPasswordSerializer,
        responses={
            200: MessageResponseSerializer,
            400: OpenApiResponse(description="Invalid request body."),
        },
        examples=[
            OpenApiExample(
                "Forgot-password request",
                value={"email": "user@example.com"},
                request_only=True,
            ),
            OpenApiExample(
                "Forgot-password response",
                value={
                    "message": (
                        "If an account exists for this email, password reset "
                        "instructions will be sent."
                    )
                },
                response_only=True,
                status_codes=["200"],
            ),
        ],
    )
    def post(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Intentionally return a generic response. Email delivery is not wired here
        # because this task is restricted to the accounts app and api.json.
        return Response(
            {
                "message": (
                    "If an account exists for this email, password reset "
                    "instructions will be sent."
                )
            },
            status=status.HTTP_200_OK,
        )


class ChangePasswordView(APIView):
    """Change the authenticated user's password."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Authentication"],
        summary="Change password",
        description="Requires a valid Bearer access token and the current password.",
        request=ChangePasswordSerializer,
        responses={
            200: MessageResponseSerializer,
            400: OpenApiResponse(description="Old password or new password is invalid."),
            401: OpenApiResponse(description="Authentication required."),
        },
        examples=[
            OpenApiExample(
                "Change-password request",
                value={
                    "old_password": "StrongPassword123!",
                    "new_password": "NewStrongPassword456!",
                },
                request_only=True,
            ),
        ],
    )
    def post(self, request):
        serializer = ChangePasswordSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)

        request.user.set_password(
            serializer.validated_data["new_password"]
        )
        request.user.save(update_fields=["password"])

        return Response(
            {"message": "Password changed successfully."},
            status=status.HTTP_200_OK,
        )


class ProfileView(APIView):
    """Read, update, or delete the authenticated user's account."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["User Profile"],
        summary="Get profile",
        responses={
            200: UserSerializer,
            401: OpenApiResponse(description="Authentication required."),
        },
    )
    def get(self, request):
        return Response(
            UserSerializer(request.user).data,
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        tags=["User Profile"],
        summary="Update profile",
        description="Currently only full_name may be updated.",
        request=ProfileUpdateSerializer,
        responses={
            200: UserSerializer,
            400: OpenApiResponse(description="Validation error."),
            401: OpenApiResponse(description="Authentication required."),
        },
        examples=[
            OpenApiExample(
                "Profile update request",
                value={"full_name": "Updated Name"},
                request_only=True,
            ),
        ],
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

    @extend_schema(
        tags=["User Profile"],
        summary="Delete account",
        request=None,
        responses={
            200: MessageResponseSerializer,
            401: OpenApiResponse(description="Authentication required."),
        },
    )
    def delete(self, request):
        request.user.delete()

        return Response(
            {"message": "Account deleted successfully."},
            status=status.HTTP_200_OK,
        )


class LogoutView(APIView):
    """Validate logout ownership and instruct the client to clear JWT tokens."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Authentication"],
        summary="Logout",
        description=(
            "Validates that the refresh token belongs to the authenticated user. "
            "The client must then delete its access and refresh tokens. Server-side "
            "blacklisting is not used because no settings changes are allowed."
        ),
        request=LogoutSerializer,
        responses={
            200: MessageResponseSerializer,
            400: OpenApiResponse(description="Invalid refresh token."),
            401: OpenApiResponse(description="Authentication required."),
        },
    )
    def post(self, request):
        serializer = LogoutSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)

        return Response(
            {
                "message": (
                    "Logout successful. Remove the access and refresh tokens "
                    "from the client."
                )
            },
            status=status.HTTP_200_OK,
        )
