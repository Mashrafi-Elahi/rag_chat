from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response

from rest_framework.permissions import (
    AllowAny,
    IsAuthenticated,
)

from rest_framework_simplejwt.tokens import RefreshToken

from drf_spectacular.utils import (
    extend_schema,
    OpenApiResponse,
)

from .serializers import (
    SignupSerializer,
    LoginSerializer,
    UserSerializer,
    AuthResponseSerializer,
    ForgotPasswordSerializer,
    ChangePasswordSerializer,
)


class SignupView(APIView):
    """
    User registration endpoint.
    Creates account and returns JWT tokens.
    """

    permission_classes = [
        AllowAny
    ]

    @extend_schema(
        tags=["Authentication"],
        summary="Create new account",
        description="""
Register a new user using email and password.

Request Body:
- email
- password
- full_name

Returns:
- User information
- JWT access token
- JWT refresh token
        """,
        request=SignupSerializer,
        responses={
            201: AuthResponseSerializer,
            400: OpenApiResponse(
                description="Validation error"
            ),
        },
    )
    def post(self, request):

        serializer = SignupSerializer(
            data=request.data
        )

        serializer.is_valid(
            raise_exception=True
        )

        user = serializer.save()

        refresh = RefreshToken.for_user(user)

        return Response(
            {
                "message": "Account created successfully.",
                "user": UserSerializer(user).data,
                "tokens": {
                    "refresh": str(refresh),
                    "access": str(
                        refresh.access_token
                    ),
                },
            },
            status=status.HTTP_201_CREATED,
        )


class LoginView(APIView):
    """
    Login endpoint.
    """

    permission_classes = [
        AllowAny
    ]

    @extend_schema(
        tags=["Authentication"],
        summary="Login user",
        description="""
Login using email and password.

Returns JWT access and refresh tokens.
        """,
        request=LoginSerializer,
        responses={
            200: AuthResponseSerializer,
            400: OpenApiResponse(
                description="Invalid credentials"
            ),
        },
    )
    def post(self, request):

        serializer = LoginSerializer(
            data=request.data,
            context={
                "request": request
            }
        )

        serializer.is_valid(
            raise_exception=True
        )

        user = serializer.validated_data[
            "user"
        ]

        refresh = RefreshToken.for_user(user)

        return Response(
            {
                "message": "Login successful.",
                "user": UserSerializer(user).data,
                "tokens": {
                    "refresh": str(refresh),
                    "access": str(
                        refresh.access_token
                    ),
                },
            },
            status=status.HTTP_200_OK
        )


class MeView(APIView):
    """
    Current authenticated user endpoint.
    """

    permission_classes = [
        IsAuthenticated
    ]

    @extend_schema(
        tags=["User"],
        summary="Get current user",
        description="""
Returns logged-in user information.

Requires:
Authorization: Bearer <access_token>
        """,
        responses={
            200: UserSerializer,
            401: OpenApiResponse(
                description="Authentication required"
            ),
        },
    )
    def get(self, request):

        serializer = UserSerializer(
            request.user
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK
        )


class ForgotPasswordView(APIView):
    """
    Forgot password endpoint.

    Request:

    {
        "email":"user@example.com"
    }

    Response:

    {
        "message":"Password reset email sent"
    }
    """

    permission_classes = [
        AllowAny
    ]

    @extend_schema(
        tags=["Authentication"],
        summary="Forgot password",
        request=ForgotPasswordSerializer,
        responses={
            200: OpenApiResponse(
                description="Reset email sent"
            ),
            400: OpenApiResponse(
                description="Validation error"
            ),
        },
    )
    def post(self, request):

        serializer = ForgotPasswordSerializer(
            data=request.data
        )

        serializer.is_valid(
            raise_exception=True
        )

        email = serializer.validated_data[
            "email"
        ]

        # Email sending logic will be added later

        return Response(
            {
                "message":
                "Password reset email sent"
            },
            status=status.HTTP_200_OK
        )


class ChangePasswordView(APIView):
    """
    Change password for logged-in user.

    Requires JWT authentication.

    Request:

    {
        "old_password":"oldpass123",
        "new_password":"newpass123"
    }
    """

    permission_classes = [
        IsAuthenticated
    ]

    @extend_schema(
        tags=["Authentication"],
        summary="Change password",
        request=ChangePasswordSerializer,
        responses={
            200: OpenApiResponse(
                description="Password changed successfully"
            ),
            400: OpenApiResponse(
                description="Validation error"
            ),
            401: OpenApiResponse(
                description="Authentication required"
            ),
        },
    )
    def post(self, request):

        serializer = ChangePasswordSerializer(
            data=request.data,
            context={
                "request": request
            }
        )

        serializer.is_valid(
            raise_exception=True
        )

        request.user.set_password(
            serializer.validated_data[
                "new_password"
            ]
        )

        request.user.save()

        return Response(
            {
                "message":
                "Password changed successfully"
            },
            status=status.HTTP_200_OK
        )