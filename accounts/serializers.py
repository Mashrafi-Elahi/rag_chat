from django.contrib.auth import authenticate, password_validation
from rest_framework import serializers
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from .models import User


class UserSerializer(serializers.ModelSerializer):
    """Public fields returned for the authenticated user."""

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "full_name",
            "date_joined",
        ]
        read_only_fields = [
            "id",
            "email",
            "date_joined",
        ]


class ProfileUpdateSerializer(serializers.ModelSerializer):
    """Fields that an authenticated user may update."""

    class Meta:
        model = User
        fields = ["full_name"]


class SignupSerializer(serializers.ModelSerializer):
    """Request body for registering a user."""

    password = serializers.CharField(
        write_only=True,
        min_length=8,
        trim_whitespace=False,
    )

    class Meta:
        model = User
        fields = [
            "email",
            "password",
            "full_name",
        ]

    def validate_email(self, value):
        email = User.objects.normalize_email(value).lower()

        if User.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError(
                "A user with this email already exists."
            )

        return email

    def validate(self, attrs):
        candidate_user = User(
            email=attrs.get("email", ""),
            full_name=attrs.get("full_name", ""),
        )
        password_validation.validate_password(
            attrs["password"],
            user=candidate_user,
        )
        return attrs

    def create(self, validated_data):
        return User.objects.create_user(
            email=validated_data["email"],
            password=validated_data["password"],
            full_name=validated_data.get("full_name", ""),
        )


class LoginSerializer(serializers.Serializer):
    """Request body for email/password login."""

    email = serializers.EmailField(
        help_text="Registered email address",
    )
    password = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
        help_text="Account password",
    )

    def validate(self, attrs):
        email = User.objects.normalize_email(attrs["email"]).lower()
        user = authenticate(
            request=self.context.get("request"),
            email=email,
            password=attrs["password"],
        )

        if user is None:
            raise serializers.ValidationError(
                "Invalid email or password."
            )

        if not user.is_active:
            raise serializers.ValidationError(
                "This account is disabled."
            )

        attrs["user"] = user
        return attrs


class ForgotPasswordSerializer(serializers.Serializer):
    """Request body for a password-reset request."""

    email = serializers.EmailField()

    def validate_email(self, value):
        return User.objects.normalize_email(value).lower()


class ChangePasswordSerializer(serializers.Serializer):
    """Request body for changing the authenticated user's password."""

    old_password = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
    )
    new_password = serializers.CharField(
        write_only=True,
        min_length=8,
        trim_whitespace=False,
    )

    def validate_new_password(self, value):
        user = self.context["request"].user
        password_validation.validate_password(value, user=user)
        return value

    def validate(self, attrs):
        user = self.context["request"].user

        if not user.check_password(attrs["old_password"]):
            raise serializers.ValidationError(
                {"old_password": "Incorrect old password."}
            )

        if attrs["old_password"] == attrs["new_password"]:
            raise serializers.ValidationError(
                {"new_password": "New password must be different."}
            )

        return attrs


class LogoutSerializer(serializers.Serializer):
    """Validate that a refresh token belongs to the current user."""

    refresh = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
    )

    def validate_refresh(self, value):
        try:
            token = RefreshToken(value)
        except TokenError as exc:
            raise serializers.ValidationError(
                "Invalid or expired refresh token."
            ) from exc

        request = self.context["request"]
        token_user_id = str(token.get("user_id", ""))

        if token_user_id != str(request.user.pk):
            raise serializers.ValidationError(
                "This refresh token does not belong to the authenticated user."
            )

        return value


class TokenResponseSerializer(serializers.Serializer):
    """JWT token pair returned by register and login."""

    refresh = serializers.CharField()
    access = serializers.CharField()


class AuthResponseSerializer(serializers.Serializer):
    """Successful register/login response."""

    message = serializers.CharField()
    user = UserSerializer()
    tokens = TokenResponseSerializer()


class MessageResponseSerializer(serializers.Serializer):
    """Standard successful message response."""

    message = serializers.CharField()
