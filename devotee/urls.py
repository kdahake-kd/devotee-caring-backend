# from django.urls import path, include
# from rest_framework.routers import DefaultRouter
# from .views import DevoteeProgressTrackingViewSet
#
# router = DefaultRouter()
# router.register('devotee-progress', DevoteeProgressTrackingViewSet, basename='devotee-progress')
#
# urlpatterns = [
#     path('', include(router.urls)),
# ]
#


from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import DailyActivityViewSet, MonthlyActivityViewSet, validate_qr_token, submit_quick_entry

router = DefaultRouter()
router.register(r'daily-activity', DailyActivityViewSet, basename='daily-activity')
router.register(r'monthly-activity', MonthlyActivityViewSet, basename='monthly-activity')

urlpatterns = [
    path('', include(router.urls)),
    # QR Code quick entry endpoints (public, no auth required)
    path('quick-entry/validate/<str:token>/', validate_qr_token, name='validate-qr-token'),
    path('quick-entry/submit/<str:token>/', submit_quick_entry, name='submit-quick-entry'),
]
