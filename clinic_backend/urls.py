from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from users.views import (
    CustomTokenView, register_view, logout_view, FacultyViewSet, 
    admin_add_personnel, UserViewSet, google_auth_view, check_availability_view,
    forgot_password_request_otp, forgot_password_verify_otp, forgot_password_reset_password
)
from appointments.views import AppointmentViewSet, verify_slip_view, verify_meeting_report_view


# API router for automatic ViewSet URL routing
router = DefaultRouter()
router.register(r'appointments', AppointmentViewSet, basename='appointment')
router.register(r'faculty', FacultyViewSet, basename='faculty') 
router.register(r'users', UserViewSet, basename='user')

urlpatterns = [
    path('admin/', admin.site.urls),

    # Authentication endpoints
    path('api/login/', CustomTokenView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/google-auth/', google_auth_view, name='google_auth'),

    # User authentication actions
    path('api/register/', register_view, name='register'),
    path('api/check-availability/', check_availability_view, name='check_availability'),
    path('api/logout/', logout_view, name='logout'),
    path('api/admin/add-personnel/', admin_add_personnel, name='admin_add_personnel'),

    # Forgot password actions
    path('api/forgot-password/request-otp/', forgot_password_request_otp, name='forgot_password_request_otp'),
    path('api/forgot-password/verify-otp/', forgot_password_verify_otp, name='forgot_password_verify_otp'),
    path('api/forgot-password/reset-password/', forgot_password_reset_password, name='forgot_password_reset_password'),

     # API routes for appointments and faculty
    path('api/', include(router.urls)),

    path('verify-slip/<int:appointment_id>/', verify_slip_view, name='verify_slip'),
    path('verify-meeting-report/<int:appointment_id>/', verify_meeting_report_view, name='verify_meeting_report'),
]
