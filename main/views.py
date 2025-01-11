from django.views.generic import ListView, DetailView

from django.db.models import Prefetch

from products.models import Category, Product


class LandingPageView(ListView):
    model = Category
    template_name = 'main.html'
    context_object_name = 'categories'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Get featured categories with their products and images preloaded
        context['featured_categories'] = Category.objects.prefetch_related(
            Prefetch(
                'products',
                queryset=Product.objects.prefetch_related('images')
            )
        ).all()
        return context

