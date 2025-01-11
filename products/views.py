from django.views.generic import DetailView
from django.http import JsonResponse
from django.template.loader import render_to_string
from django.core.paginator import Paginator

from products.models import Category, Product

# Create your views here.
class CategoryDetailView(DetailView):
    model = Category
    template_name = 'category_detail.html'
    context_object_name = 'category'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Get all products for this category
        context['products'] = self.object.products.all()
        return context

class ProductDetailView(DetailView):
    model = Product
    template_name = 'products/product_detail.html'
    context_object_name = 'product'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Get all images for this product
        context['images'] = self.object.images.all()
        # Get related products from same category
        context['related_products'] = Product.objects.filter(
            category=self.object.category
        ).exclude(id=self.object.id)[:4]
        return context

def get_new_cards(request):
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        # Get random categories or products to display
        categories = Category.objects.order_by('?')[:3]  # Get 3 random categories
        html = render_to_string('partials/category_cards.html', {'categories': categories})
        return JsonResponse({'html': html})
    return JsonResponse({'error': 'Invalid request'}, status=400)

def get_category_products(request):
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        category_id = request.GET.get('category_id')
        page_number = request.GET.get('page', 1)
        
        try:
            category = Category.objects.get(pk=category_id)
            products = category.products.all().prefetch_related('images')
            
            # Create paginator
            paginator = Paginator(products, 10)  # Show 10 products per page
            page_obj = paginator.get_page(page_number)
            
            html = render_to_string('partials/product_cards.html', {
                'products': page_obj,
                'category': category
            })
            
            return JsonResponse({
                'html': html,
                'has_next': page_obj.has_next(),
                'has_prev': page_obj.has_previous(),
                'total_pages': paginator.num_pages,
                'current_page': page_obj.number
            })
            
        except Category.DoesNotExist:
            return JsonResponse({'error': 'Category not found'}, status=404)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
            
    return JsonResponse({'error': 'Invalid request'}, status=400)