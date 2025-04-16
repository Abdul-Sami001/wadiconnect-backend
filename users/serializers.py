from djoser.serializers import UserCreateSerializer, UserSerializer
from rest_framework import serializers
from .models import CustomerProfile, SellerProfile, CustomUser, EmailOTP

class CustomUserCreateSerializer(UserCreateSerializer):
    role = serializers.ChoiceField(
        choices=CustomUser.ROLE_CHOICES, default=CustomUser.CUSTOMER
    )

    class Meta(UserCreateSerializer.Meta):
        model = CustomUser
        fields = ("id", "email", "password", "re_password", "role")


class CustomUserSerializer(UserSerializer):
    class Meta(UserSerializer.Meta):
        model = CustomUser
        fields = ("id", "email", "role")



# 🔹 Serializer for user registration
class RegisterUserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    re_password = serializers.CharField(write_only=True)

    # role field is optional; if not sent, it will default to the model default "customer"
    role = serializers.ChoiceField(choices=CustomUser.ROLE_CHOICES, default=CustomUser.CUSTOMER)

    class Meta:
        model = CustomUser
        fields = ("email", "password", "re_password", "role")

    def validate(self, data):
        if data["password"] != data["re_password"]:
            raise serializers.ValidationError("Passwords do not match.")
        return data

    def create(self, validated_data):
        # Remove re_password since it is not needed for creation
        validated_data.pop("re_password")
        password = validated_data.pop("password")
        # Create user. The custom user manager will automatically use the role from validated_data.
        user = CustomUser.objects.create_user(**validated_data)
        user.set_password(password)
        # Mark user inactive until OTP verification completes
        user.is_active = False
        user.save()
        return user


# 🔹 Serializer for OTP verification
class OTPVerifySerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField(max_length=6)

# Serializer for resending OTP (only email is required)
class ResendOTPSerializer(serializers.Serializer):
    email = serializers.EmailField()

class CustomerProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomerProfile
        fields = ["id", "name", "phone", "address", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]        

class SellerProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = SellerProfile
        fields = [
            "id",
            "business_name",
            "profile_picture",
            "business_address",
            "phone",
            "verification_status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "verification_status",
            "created_at",
            "updated_at",
        ]
