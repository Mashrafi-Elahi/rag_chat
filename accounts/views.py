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

### Request Body

- email: Unique user email
- password: Minimum 8 characters
- full_name: Optional user name

### Returns

- Created user information
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
Authenticate user with email and password.

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
            }
        )


class MeView(APIView):
    """
    Current authenticated user.
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
            serializer.data
        )