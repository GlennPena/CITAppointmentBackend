from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import viewsets, status
from rest_framework.exceptions import PermissionDenied
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from django.conf import settings

import random
from django.core.mail import send_mail
from django.utils import timezone
from datetime import timedelta
from .models import User, PasswordResetOTP
from .serializers import UserSerializer, CustomTokenSerializer, FacultyListSerializer


class CustomTokenView(TokenObtainPairView):
    """ Uses custom serializer to include extra user data in JWT response """
    serializer_class = CustomTokenSerializer


@api_view(['POST'])
@permission_classes([AllowAny])
def register_view(request):
    print("REQUEST DATA:", request.data)
    """ Registers a new user and returns JWT tokens with basic user info """
    serializer = UserSerializer(data=request.data, context={'request': request})

    if serializer.is_valid():
        user = serializer.save()
        
        refresh = RefreshToken.for_user(user)
        
        return Response({
            "message": "Registration successful",
            "tokens": {
                "refresh": str(refresh),
                "access": str(refresh.access_token),
            },
            "user": {
                "id": user.id,
                "username": user.username,
                "role": user.role,
                "first_name": user.first_name,
                "last_name": user.last_name
            }
        }, status=status.HTTP_201_CREATED)
        
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([AllowAny])
def check_availability_view(request):
    username = request.data.get('username')
    email = request.data.get('email')
    
    errors = {}
    if username and User.objects.filter(username=username).exists():
        errors['username'] = "Username is already taken."
    if email and User.objects.filter(email=email).exists():
        errors['email'] = "Email is already registered."
        
    if errors:
        return Response(errors, status=status.HTTP_400_BAD_REQUEST)
        
    return Response({"message": "Available"}, status=status.HTTP_200_OK)

@api_view(['POST'])
@permission_classes([AllowAny])
def google_auth_view(request):
    token = request.data.get('id_token')
    
    if not token:
        return Response({"error": "ID Token is required"}, status=status.HTTP_400_BAD_REQUEST)

    if settings.DEBUG and token.startswith('mock_token_'):
        email = token.replace('mock_token_', '').lower()
        id_info = {
            'email': email,
            'given_name': email.split('@')[0].split('.')[0].capitalize(),
            'family_name': email.split('@')[0].split('.')[-1].capitalize() if '.' in email.split('@')[0] else ''
        }
    else:
        try:
            id_info = id_token.verify_oauth2_token(
                token, 
                google_requests.Request(), 
                settings.GOOGLE_CLIENT_ID
            )
            email = id_info.get('email').lower()
        except Exception as e:
            return Response({"error": f"Invalid token verification: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)

    if not email.endswith('@ua.edu.ph'):
        return Response(
            {"error": "Only @ua.edu.ph email addresses are allowed."}, 
            status=status.HTTP_403_FORBIDDEN
        )

    user = User.objects.filter(email=email).first()

    if user:
        refresh = RefreshToken.for_user(user)
        return Response({
            "action": "login",
            "tokens": {
                "refresh": str(refresh),
                "access": str(refresh.access_token)
            },
            "user": {
                "id": user.id,
                "email": user.email,
                "role": user.role,
                "first_name": user.first_name,
                "last_name": user.last_name
            }
        }, status=status.HTTP_200_OK)
    
    else:
        return Response({
            "action": "register",
            "google_info": {
                "email": email,
                "first_name": id_info.get('given_name', ''),
                "last_name": id_info.get('family_name', ''),
            }
        }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_view(request):
    """ Logs out the user by blacklisting the refresh token """
    try:
        refresh_token = request.data.get("refresh")
        if not refresh_token:
            return Response({"error": "Refresh token is required"}, status=status.HTTP_400_BAD_REQUEST)
            
        token = RefreshToken(refresh_token)
        token.blacklist() 
        
        return Response({"message": "Successfully logged out"}, status=status.HTTP_205_RESET_CONTENT)
    
    except Exception as e:
        return Response({"error": "Invalid or expired token"}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def admin_add_personnel(request):
    """ Allows admin to add new personnel """
    if request.user.role != 'admin':
        return Response({"error": "Unauthorized"}, status=status.HTTP_403_FORBIDDEN)

    serializer = UserSerializer(data=request.data, context={'request': request})
    if serializer.is_valid():
        user = serializer.save()
        return Response({
            "message": f"{user.role.capitalize()} created successfully",
            "user": {"username": user.username, "role": user.role}
        }, status=status.HTTP_201_CREATED)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserViewSet(viewsets.ModelViewSet):
    """ Provides CRUD operations for users (admin only) """
    permission_classes = [IsAuthenticated]
    serializer_class = UserSerializer

    def get_queryset(self):
        user = self.request.user
        if user.role != 'admin':
            # Non-admin users can only see their own profile
            return User.objects.filter(id=user.id)
        
        # Admin can see all users, with optional role filtering
        role = self.request.query_params.get('role')
        if role:
            return User.objects.filter(role=role)
        return User.objects.all()

    def perform_create(self, serializer):
        if self.request.user.role != 'admin':
            raise PermissionDenied("Only admins can create users")
        serializer.save()

    def perform_update(self, serializer):
        if self.request.user.role != 'admin':
            raise PermissionDenied("Only admins can update users")
        serializer.save()

    def perform_destroy(self, instance):
        if self.request.user.role != 'admin':
            raise PermissionDenied("Only admins can delete users")
        instance.delete()


class FacultyViewSet(viewsets.ReadOnlyModelViewSet):
    """ Provides a read-only endpoint to list all faculty """
    permission_classes = [IsAuthenticated]
    queryset = User.objects.filter(role__in=["faculty", "dean"])
    serializer_class = FacultyListSerializer


@api_view(['POST'])
@permission_classes([AllowAny])
def forgot_password_request_otp(request):
    email = request.data.get('email', '').strip().lower()
    if not email:
        return Response({"error": "Email is required"}, status=status.HTTP_400_BAD_REQUEST)

    # Check if user exists
    user_exists = User.objects.filter(email=email).exists()
    if not user_exists:
        return Response({"error": "No account registered with this email address."}, status=status.HTTP_404_NOT_FOUND)

    # Generate 6-digit OTP
    otp = f"{random.randint(100000, 999999)}"

    # Save to database
    PasswordResetOTP.objects.create(email=email, otp=otp)

    # Send email
    subject = "Your UACIT Password Reset Code"
    message = (
        f"Hello,\n\n"
        f"We received a request to reset the password for your UACIT Appointment System account.\n\n"
        f"Your verification code is:\n\n"
        f"  {otp}\n\n"
        f"This code is valid for 10 minutes.\n\n"
        f"If you did not request a password reset, you can safely ignore this email. "
        f"Your password will not be changed.\n\n"
        f"---\n"
        f"UACIT Appointment System\n"
        f"College of Information Technology\n"
        f"University of the Assumption\n"
    )

    try:
        send_mail(
            subject=subject,
            message=message,
            from_email='UACIT Appointment System <uacitappointment@gmail.com>',
            recipient_list=[email],
            fail_silently=False,
        )
    except Exception as e:
        print("SMTP Error:", e)
        return Response({"error": f"Failed to send email: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    return Response({"message": "Verification code sent successfully to your email."}, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([AllowAny])
def forgot_password_verify_otp(request):
    email = request.data.get('email', '').strip().lower()
    otp = request.data.get('otp', '').strip()

    if not email or not otp:
        return Response({"error": "Email and verification code are required."}, status=status.HTTP_400_BAD_REQUEST)

    # Find the latest unused OTP record
    otp_record = PasswordResetOTP.objects.filter(email=email, otp=otp, is_used=False).order_by('-created_at').first()

    if not otp_record:
        return Response({"error": "Invalid verification code."}, status=status.HTTP_400_BAD_REQUEST)

    # Verify expiration
    time_elapsed = timezone.now() - otp_record.created_at
    if time_elapsed > timedelta(minutes=10):
        return Response({"error": "Verification code has expired. Please request a new one."}, status=status.HTTP_400_BAD_REQUEST)

    return Response({"message": "Verification code verified successfully."}, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([AllowAny])
def forgot_password_reset_password(request):
    email = request.data.get('email', '').strip().lower()
    otp = request.data.get('otp', '').strip()
    new_password = request.data.get('new_password', '')

    if not email or not otp or not new_password:
        return Response({"error": "Email, verification code, and new password are required."}, status=status.HTTP_400_BAD_REQUEST)

    # Find the latest unused OTP record to verify permission
    otp_record = PasswordResetOTP.objects.filter(email=email, otp=otp, is_used=False).order_by('-created_at').first()

    if not otp_record:
        return Response({"error": "Invalid verification code."}, status=status.HTTP_400_BAD_REQUEST)

    # Verify expiration
    time_elapsed = timezone.now() - otp_record.created_at
    if time_elapsed > timedelta(minutes=10):
        return Response({"error": "Verification code has expired. Please request a new one."}, status=status.HTTP_400_BAD_REQUEST)

    # Reset password
    user = User.objects.filter(email=email).first()
    if not user:
        return Response({"error": "User not found."}, status=status.HTTP_444_NOT_FOUND)

    user.set_password(new_password)
    user.save()

    # Mark the OTP as used
    otp_record.is_used = True
    otp_record.save()

    return Response({"message": "Your password has been reset successfully."}, status=status.HTTP_200_OK)
