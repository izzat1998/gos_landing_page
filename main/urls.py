from django.urls import path
from rest_framework.authtoken.views import obtain_auth_token

from .views import (
    CatalogView,
    CategoryDetailView,
    FurnitureDetailView,
    LandingPageView,
    LocationQRCodeListView,
    LocationQRCodeView,
    LocationStatsAPIView,
    LocationVisitView,
    RecordPhoneClickView,
    SeeItInYourRoomView,
)

urlpatterns = [
    path("see-it-in-your-room/", SeeItInYourRoomView.as_view(), name="see_it_in_your_room"),
    path("", LandingPageView.as_view(), name="main_page"),
    path("qrcode/<int:pk>/", LocationQRCodeView.as_view(), name="location_qrcode"),
    path(
        "visit/<int:location_id>/", LocationVisitView.as_view(), name="location_visit"
    ),
    path("qrcodes/", LocationQRCodeListView.as_view(), name="qrcode_list"),
    path(
        "api/location-stats/", LocationStatsAPIView.as_view(), name="location_stats_api"
    ),
    path("api/token/", obtain_auth_token, name="api_token"),
    path(
        "api/record-phone-click/",
        RecordPhoneClickView.as_view(),
        name="record_phone_click",
    ),
    # Furniture catalog URLs
    path("catalog/", CatalogView.as_view(), name="catalog"),
    path(
        "catalog/<slug:category_slug>/",
        CategoryDetailView.as_view(),
        name="category_detail",
    ),
    path(
        "catalog/<slug:category_slug>/<slug:item_slug>/",
        FurnitureDetailView.as_view(),
        name="furniture_detail",
    ),
]
