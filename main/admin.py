import datetime
from io import BytesIO

import qrcode
from django.contrib import admin
from django.db.models import Count
from django.http import HttpResponse
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils import timezone
from django.utils.html import format_html

from .models import Location, QRCodeScan

# Register your models here.


class QRCodeScanInline(admin.TabularInline):
    model = QRCodeScan
    extra = 0
    readonly_fields = ("timestamp", "ip_address", "user_agent")
    can_delete = False
    max_num = 0
    fields = ("timestamp", "ip_address")

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "created_at",
        "get_scan_count",
        "view_qr_code",
        "view_statistics",
    )
    search_fields = ("name",)
    inlines = [QRCodeScanInline]
    readonly_fields = ("qr_code_preview",)
    fieldsets = (
        (None, {"fields": ("name", "description")}),
        (
            "QR Code",
            {
                "fields": ("qr_code_preview",),
                "classes": ("collapse",),
            },
        ),
    )

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "<int:location_id>/qrcode/",
                self.admin_site.admin_view(self.generate_qrcode),
                name="location-qrcode",
            ),
            path(
                "<int:location_id>/statistics/",
                self.admin_site.admin_view(self.view_statistics_detail),
                name="location-statistics",
            ),
        ]
        return custom_urls + urls

    def get_scan_count(self, obj):
        return obj.scans.count()

    get_scan_count.short_description = "Scans"

    def view_qr_code(self, obj):
        url = reverse("admin:location-qrcode", args=[obj.pk])
        return format_html('<a class="button" href="{}">View QR Code</a>', url)

    view_qr_code.short_description = "QR Code"

    def view_statistics(self, obj):
        url = reverse("admin:location-statistics", args=[obj.pk])
        return format_html('<a class="button" href="{}">View Stats</a>', url)

    view_statistics.short_description = "Statistics"

    def qr_code_preview(self, obj):
        if not obj.pk:  # Don't show preview for new objects
            return "Save first to see QR code"

        url = reverse("admin:location-qrcode", args=[obj.pk])
        return format_html(
            '<img src="{}" width="150" height="150"/><br/><a class="button" href="{}" download="qrcode_{}.png">Download</a>',
            url,
            url,
            obj.name,
        )

    qr_code_preview.short_description = "QR Code Preview"

    def generate_qrcode(self, request, location_id, *args, **kwargs):
        location = self.get_object(request, location_id)
        site_url = request.build_absolute_uri("/").rstrip("/")
        redirect_url = f"{site_url}/visit/{location.id}/"

        # Generate QR code
        img = qrcode.make(redirect_url)

        # Save QR code to BytesIO object
        buffer = BytesIO()
        img.save(buffer)
        buffer.seek(0)

        # Return the QR code as an image
        response = HttpResponse(buffer, content_type="image/png")
        response["Content-Disposition"] = (
            f'inline; filename="qrcode_{location.name}.png"'
        )
        return response

    def view_statistics_detail(self, request, location_id, *args, **kwargs):
        location = self.get_object(request, location_id)

        # Get time periods for statistics
        today = timezone.now().date()
        yesterday = today - datetime.timedelta(days=1)
        last_week = today - datetime.timedelta(days=7)
        last_month = today - datetime.timedelta(days=30)

        # Get scan counts for different time periods
        today_count = location.scans.filter(timestamp__date=today).count()
        yesterday_count = location.scans.filter(timestamp__date=yesterday).count()
        last_week_count = location.scans.filter(timestamp__date__gte=last_week).count()
        last_month_count = location.scans.filter(
            timestamp__date__gte=last_month
        ).count()
        total_count = location.scans.count()

        # Get hourly distribution for today
        hourly_distribution = (
            location.scans.filter(timestamp__date=today)
            .extra({"hour": "EXTRACT(hour FROM timestamp)"})
            .values("hour")
            .annotate(count=Count("id"))
            .order_by("hour")
        )

        # Get site URL for testing QR code
        site_url = request.build_absolute_uri("/").rstrip("/")

        context = {
            "title": f"Statistics for {location.name}",
            "location": location,
            "today_count": today_count,
            "yesterday_count": yesterday_count,
            "last_week_count": last_week_count,
            "last_month_count": last_month_count,
            "total_count": total_count,
            "hourly_distribution": hourly_distribution,
            "opts": self.model._meta,
            "site_url": site_url,
        }

        return TemplateResponse(request, "admin/location_statistics.html", context)


@admin.register(QRCodeScan)
class QRCodeScanAdmin(admin.ModelAdmin):
    list_display = ("location", "timestamp", "ip_address", "user_agent")
    list_filter = ("location", "timestamp")
    date_hierarchy = "timestamp"
    readonly_fields = ("location", "timestamp", "ip_address", "user_agent")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
