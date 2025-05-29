from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils.text import slugify
from main.models import FurnitureItem

class Command(BaseCommand):
    help = 'Fix empty or invalid slugs for all furniture items'

    def handle(self, *args, **options):
        fixed_count = 0
        
        # Get all furniture items
        items = FurnitureItem.objects.all()
        
        for item in items:
            needs_update = False
            
            # Check if slug is empty or None
            if not item.slug:
                needs_update = True
                # Generate slug from name or use item ID as fallback
                base_slug = slugify(item.name) if item.name else f"item-{item.pk}"
                if not base_slug:
                    base_slug = f"item-{item.pk}"
                item.slug = base_slug
            
            # Check for duplicate slugs
            if FurnitureItem.objects.filter(~Q(pk=item.pk), slug=item.slug).exists():
                needs_update = True
                base_slug = item.slug
                counter = 1
                while FurnitureItem.objects.filter(~Q(pk=item.pk), slug=item.slug).exists():
                    item.slug = f"{base_slug}-{counter}"
                    counter += 1
            
            if needs_update:
                item.save(update_fields=['slug'])
                self.stdout.write(f"Fixed slug for item {item.id}: {item.slug}")
                fixed_count += 1
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully fixed {fixed_count} furniture item slugs')
        )
