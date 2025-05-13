from django.urls import path
from rest_framework.authtoken.views import obtain_auth_token

from .views import (
    LandingPageView,
    LocationQRCodeView,
    LocationVisitView,
    LocationQRCodeListView,
    LocationStatsAPIView
)

urlpatterns = [
    path("", LandingPageView.as_view(), name="main_page"),
    path("qrcode/<int:pk>/", LocationQRCodeView.as_view(), name="location_qrcode"),
    path("visit/<int:location_id>/", LocationVisitView.as_view(), name="location_visit"),
    path("qrcodes/", LocationQRCodeListView.as_view(), name="qrcode_list"),
    path("api/location-stats/", LocationStatsAPIView.as_view(), name="location_stats_api"),
    path("api/token/", obtain_auth_token, name="api_token"),
]
