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
from .views import DailyActivityViewSet, MonthlyActivityViewSet

router = DefaultRouter()
router.register(r'daily-activity', DailyActivityViewSet, basename='daily-activity')
router.register(r'monthly-activity', MonthlyActivityViewSet, basename='monthly-activity')

urlpatterns = [
    path('', include(router.urls)),
]
