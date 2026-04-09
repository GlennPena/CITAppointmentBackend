from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AppointmentViewSet


# Routes for appointment API
router = DefaultRouter()
router.register(r'appointments', AppointmentViewSet, basename='appointment')

urlpatterns = [
    path('', include(router.urls)),
]