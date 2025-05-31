from django.views.generic import TemplateView, DetailView, RedirectView, ListView
from django.http import HttpResponse
from django.db.models import Count, Q
from django.contrib.admin.views.decorators import staff_member_required
from django.utils.decorators import method_decorator
from django.utils import timezone
import datetime
import qrcode
from io import BytesIO

from .models import Location, QRCodeScan, PhoneClick, FurnitureCategory, FurnitureItem
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated


class LandingPageView(TemplateView):
    template_name = "main.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        visit_id = self.request.GET.get('visit_id')
        if visit_id:
            context['visit_id'] = visit_id
            
        # Add furniture categories to the context
        context['categories'] = FurnitureCategory.objects.filter(is_active=True).order_by('order', 'name')
        return context


class LocationQRCodeView(DetailView):
    model = Location
    
    def get(self, request, *args, **kwargs):
        location = self.get_object()
        
        # Generate the URL with location parameter
        site_url = request.build_absolute_uri('/').rstrip('/')
        redirect_url = f"{site_url}/visit/{location.id}/"
        
        # Generate QR code
        img = qrcode.make(redirect_url)
        
        # Save QR code to BytesIO object
        buffer = BytesIO()
        img.save(buffer)
        buffer.seek(0)
        
        # Return the QR code as an image
        return HttpResponse(buffer, content_type='image/png')


class LocationVisitView(RedirectView):
    permanent = False
    
    def get_redirect_url(self, *args, **kwargs):
        location_id = kwargs.get('location_id')
        scan = None  # Initialize scan to None
        try:
            location = Location.objects.get(id=location_id)
            
            # Record the visit
            scan = QRCodeScan.objects.create(
                location=location,
                ip_address=self.request.META.get('REMOTE_ADDR'),
                user_agent=self.request.META.get('HTTP_USER_AGENT', '')
            )
            
        except Location.DoesNotExist:
            pass
            
        # Redirect to the homepage with visit_id if available
        if scan and scan.visit_id:
            return f'/?visit_id={scan.visit_id}'
        return '/'


@method_decorator(staff_member_required, name='dispatch')
class LocationQRCodeListView(ListView):
    model = Location
    template_name = 'qrcode_list.html'
    context_object_name = 'locations'


class LocationStatsAPIView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        # Get period from query params (default: last 30 days)
        days = int(request.query_params.get('days', 30))
        start_date = timezone.now() - datetime.timedelta(days=days)
        
        # Get stats for each location
        locations = Location.objects.annotate(
            total_scans=Count('scans'),
            recent_scans=Count('scans', filter=Q(scans__timestamp__gte=start_date))
        ).values('id', 'name', 'total_scans', 'recent_scans')
        
        return Response(locations)


class RecordPhoneClickView(APIView):
    def post(self, request, *args, **kwargs):
        visit_id = request.data.get('visit_id')

        if not visit_id:
            return Response(
                {"error": "visit_id is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            scan = QRCodeScan.objects.get(visit_id=visit_id)
            PhoneClick.objects.create(scan=scan)
            return Response(
                {"status": "success", "message": "Phone click recorded"},
                status=status.HTTP_201_CREATED
            )
        except QRCodeScan.DoesNotExist:
            return Response(
                {"error": "QRCodeScan not found for the provided visit_id"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            # Generic exception handler for unexpected errors
            return Response(
                {"error": "An unexpected error occurred: " + str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class CatalogView(ListView):
    model = FurnitureCategory
    template_name = 'catalog/catalog.html'
    context_object_name = 'categories'

    def get_queryset(self):
        return FurnitureCategory.objects.filter(is_active=True).order_by('order', 'name')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['featured_items'] = FurnitureItem.objects.filter(is_featured=True, is_active=True)[:6]
        return context


class CategoryDetailView(DetailView):
    model = FurnitureCategory
    template_name = 'catalog/category_detail.html'
    context_object_name = 'category'
    slug_url_kwarg = 'category_slug'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        category = self.get_object()
        context['items'] = FurnitureItem.objects.filter(category=category, is_active=True)
        return context


class FurnitureDetailView(DetailView):
    model = FurnitureItem
    template_name = 'catalog/furniture_detail.html'
    context_object_name = 'item'
    slug_url_kwarg = 'item_slug'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        item = self.get_object()
        context['images'] = item.images.all().order_by('order')
        context['related_items'] = FurnitureItem.objects.filter(
            category=item.category, 
            is_active=True
        ).exclude(id=item.id)[:4]
        return context


class SeeItInYourRoomView(TemplateView):
    template_name = "see_it_in_your_room/see_it.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "See it in Your Room"
        return context
