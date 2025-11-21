from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import UserAuthenticationViewSet, AdminViewSet

router = DefaultRouter()
router.register(r'', UserAuthenticationViewSet, basename='auth')
router.register(r'admin', AdminViewSet, basename='admin')

urlpatterns = [
    path('', include(router.urls)),
]
