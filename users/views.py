from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from .models import CustomUser, EmailOTP, CustomerProfile, SellerProfile
from .serializers import RegisterUserSerializer, OTPVerifySerializer, ResendOTPSerializer, SellerProfileSerializer
from .utils import send_otp_to_email
from rest_framework import generics

# 1. Registration view: Create user and send OTP
class RegisterUserView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterUserSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()  # user is created inactive
            # Send OTP email
            send_otp_to_email(user.email)
            return Response(
                {"message": "User registered. Please verify OTP sent to your email."},
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# 2. OTP Verification view: Verify OTP and activate user, create profile accordingly
class VerifyOTPView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = OTPVerifySerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data["email"]
            otp = serializer.validated_data["otp"]
            try:
                user = CustomUser.objects.get(email=email)
            except CustomUser.DoesNotExist:
                return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)

            try:
                otp_obj = EmailOTP.objects.get(email=email)
            except EmailOTP.DoesNotExist:
                return Response({"error": "OTP not found."}, status=status.HTTP_404_NOT_FOUND)

            if not otp_obj.is_valid():
                return Response({"error": "OTP has expired."}, status=status.HTTP_400_BAD_REQUEST)

            if otp_obj.otp != otp:
                return Response({"error": "Invalid OTP."}, status=status.HTTP_400_BAD_REQUEST)

            # OTP is verified - activate user
            user.is_active = True
            user.save()

            # Auto-create profile based on role; if seller upgrade, details may be provided later
            if user.role == CustomUser.CUSTOMER:
                # Create an empty customer profile; user can update later
                CustomerProfile.objects.get_or_create(user=user, defaults={"name": ""})
            elif user.role == CustomUser.SELLER:
                # Create an empty seller profile; upgrade endpoint will update details
                SellerProfile.objects.get_or_create(user=user, defaults={"business_name": "", "business_address": "", "phone": ""})

            # Remove OTP record after successful verification
            otp_obj.delete()

            return Response({"message": "OTP verified. Account activated."})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# 3. Resend OTP view: Generate and send OTP again
class ResendOTPView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ResendOTPSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data["email"]
            try:
                user = CustomUser.objects.get(email=email)
            except CustomUser.DoesNotExist:
                return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)
            
            if user.is_active:
                return Response({"message": "User is already activated."})
            send_otp_to_email(email)
            return Response({"message": "A new OTP has been sent to your email."})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# 4. Seller Upgrade View: (for customers upgrading to seller)
class UpgradeToSellerView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        # Ensure current user is not already a seller
        if request.user.role == CustomUser.SELLER:
            return Response({"error": "You are already a seller."}, status=status.HTTP_400_BAD_REQUEST)
        
        serializer = SellerProfileSerializer(data=request.data)
        if serializer.is_valid():
            # Update user role to seller
            request.user.role = CustomUser.SELLER
            request.user.save()
            # Create a SellerProfile for the user
            SellerProfile.objects.create(user=request.user, **serializer.validated_data)
             
            return Response({"message": "Your details are pending verification; you will receive an email once verified."}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ProfileView(generics.RetrieveUpdateAPIView):
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        # Determine the serializer based on the user's role.
        if self.request.user.role == CustomUser.SELLER:
            return SellerProfileSerializer
        else:
            return CustomerProfileSerializer

    def get_object(self):
        # Retrieve the user's profile based on role.
        if self.request.user.role == CustomUser.SELLER:
            # It will raise a DoesNotExist if SellerProfile hasn't been created. Consider handling that.
            return self.request.user.seller_profile
        else:
            # For CustomerProfile, it's assumed that it was auto-created after OTP verification.
            return self.request.user.customer_profile