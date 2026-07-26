from django.contrib.auth import authenticate
from rest_framework import serializers

from .models import User


class UserSerializer(serializers.ModelSerializer):
    """
    Serializer for user profile response.
    """

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "full_name",
            "date_joined",
        ]


class SignupSerializer(serializers.ModelSerializer):
    """
    Request body for creating a new account.

    Fields:
    - email: User email address
    - password: Account password
    - full_name: Optional display name
    """

    password = serializers.CharField(
        write_only=True,
        min_length=8
    )

    class Meta:
        model = User
        fields = [
            "email",
            "password",
            "full_name",
        ]

    def create(self, validated_data):
        return User.objects.create_user(
            email=validated_data["email"],
            password=validated_data["password"],
            full_name=validated_data.get(
                "full_name",
                ""
            )
        )


class LoginSerializer(serializers.Serializer):
    """
    Request body for login.
    """

    email = serializers.EmailField(
        help_text="Registered email address"
    )

    password = serializers.CharField(
        write_only=True,
        help_text="Account password"
    )

    def validate(self, attrs):
        user = authenticate(
            request=self.context.get("request"),
            email=attrs["email"],
            password=attrs["password"],
        )

        if not user:
            raise serializers.ValidationError(
                "Invalid email or password."
            )

        attrs["user"] = user
        return attrs


class TokenResponseSerializer(serializers.Serializer):
    """
    JWT token response.
    """

    refresh = serializers.CharField()
    access = serializers.CharField()


class AuthResponseSerializer(serializers.Serializer):
    """
    Common authentication response.
    """

    message = serializers.CharField()

    user = UserSerializer()

    tokens = TokenResponseSerializer()