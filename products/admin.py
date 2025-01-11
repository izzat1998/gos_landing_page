from django.contrib import admin
from .models import Product, Category, ProductImage

# Register your models here.
class ProductImageAdmin(admin.TabularInline):
    model = ProductImage

class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'category')
    inlines = [ProductImageAdmin]

class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')


admin.site.register(Product, ProductAdmin)
admin.site.register(Category, CategoryAdmin)
admin.site.register(ProductImage)