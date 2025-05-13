from django.views.generic import TemplateView, DetailView, RedirectView, ListView
from django.http import HttpResponse
from django.db.models import Count, Q
from django.contrib.admin.views.decorators import staff_member_required
from django.utils.decorators import method_decorator
from django.utils import timezone
import datetime
import qrcode
from io import BytesIO

from .models import Location, QRCodeScan
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated


class LandingPageView(TemplateView):
    template_name = "main.html"


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
        try:
            location = Location.objects.get(id=location_id)
            
            # Record the visit
            QRCodeScan.objects.create(
                location=location,
                ip_address=self.request.META.get('REMOTE_ADDR'),
                user_agent=self.request.META.get('HTTP_USER_AGENT', '')
            )
            
        except Location.DoesNotExist:
            pass
            
        # Redirect to the homepage
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
