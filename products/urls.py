from .views import CategoryDetailView, ProductDetailView, get_new_cards, get_category_products
from django.urls import path

app_name = 'products'

urlpatterns = [
    path('categories/<int:pk>/', CategoryDetailView.as_view(), name='category-detail'),
    path('products/<int:pk>/', ProductDetailView.as_view(), name='product-detail'),
    path('api/get-new-cards/', get_new_cards, name='get-new-cards'),
    path('api/get-category-products/', get_category_products, name='get-category-products'),
]