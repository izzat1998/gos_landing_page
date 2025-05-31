import json
import os

from django.core.management.base import BaseCommand
from django.utils.text import slugify

from main.models import FurnitureCategory, FurnitureItem


class Command(BaseCommand):
    help = "Update furniture items with new names and descriptions from JSON file"

    def handle(self, *args, **options):
        # Path to the JSON file
        json_file_path = os.path.join(
            os.path.dirname(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            ),
            "all_files.json",
        )

        self.stdout.write(self.style.SUCCESS(f"Reading data from {json_file_path}"))

        try:
            with open(json_file_path, "r", encoding="utf-8") as file:
                data = json.load(file)

            # Process each category
            for category_name, items in data.items():
                self.stdout.write(f"Processing category: {category_name}")

                # Generate a valid slug for the category
                category_slug = slugify(category_name)
                if not category_slug:
                    # If slugify produces an empty string (e.g., for non-Latin characters),
                    # create a slug based on a transliteration or a default value
                    if category_name == "Детская мебель":
                        category_slug = "kids-furniture"
                    elif category_name == "Офисная мебель":
                        category_slug = "office-furniture"
                    else:
                        category_slug = f"category-{len(category_name)}-{hash(category_name) % 10000}"

                # Find or create the category
                category, created = FurnitureCategory.objects.get_or_create(
                    name=category_name,
                    defaults={
                        "slug": category_slug,
                        "description": f"Collection of {category_name.lower()}",
                        "order": 0,
                        "is_active": True,
                    },
                )

                # If the category exists but has an empty slug, update it
                if not created and not category.slug:
                    category.slug = category_slug
                    category.save()

                if created:
                    self.stdout.write(
                        self.style.SUCCESS(f"Created new category: {category_name}")
                    )

                # Process each item in the category
                for item_data in items:
                    old_name = item_data.get("oldName", "")
                    new_name = item_data.get("newName", "")
                    description = item_data.get("description", "")

                    if not old_name or not new_name:
                        self.stdout.write(
                            self.style.WARNING(
                                f"Skipping item with missing name data: {item_data}"
                            )
                        )
                        continue

                    # Try to find the item by old name first
                    items = FurnitureItem.objects.filter(
                        name__icontains=old_name, category=category
                    )

                    if not items.exists():
                        # If not found by old name, try to find by new name
                        items = FurnitureItem.objects.filter(
                            name__icontains=new_name, category=category
                        )

                    if items.exists():
                        # Update existing items
                        for item in items:
                            item.name = new_name
                            item.description = description
                            # Ensure slug is never empty
                            new_slug = slugify(new_name)
                            if not new_slug:
                                # If slugify produces an empty string (e.g., for non-Latin characters),
                                # create a slug based on the item ID
                                new_slug = f"furniture-item-{item.id}"
                            item.slug = new_slug
                            item.save()
                            self.stdout.write(
                                self.style.SUCCESS(
                                    f"Updated item: {old_name} → {new_name}"
                                )
                            )
                    else:
                        self.stdout.write(
                            self.style.WARNING(
                                f"Item not found: {old_name} / {new_name}"
                            )
                        )

            # Fix any existing items with empty slugs
            self.stdout.write("Checking for items with empty slugs...")
            items_with_empty_slugs = FurnitureItem.objects.filter(slug="")
            for item in items_with_empty_slugs:
                item.slug = f"furniture-item-{item.id}"
                item.save()
                self.stdout.write(
                    self.style.SUCCESS(f"Fixed empty slug for item: {item.name}")
                )

            # Fix any existing categories with empty slugs
            categories_with_empty_slugs = FurnitureCategory.objects.filter(slug="")
            for category in categories_with_empty_slugs:
                if category.name == "Детская мебель":
                    category.slug = "kids-furniture"
                elif category.name == "Офисная мебель":
                    category.slug = "office-furniture"
                else:
                    category.slug = f"category-{category.id}"
                category.save()
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Fixed empty slug for category: {category.name}"
                    )
                )

            self.stdout.write(
                self.style.SUCCESS("Furniture data update completed successfully!")
            )

        except FileNotFoundError:
            self.stdout.write(
                self.style.ERROR(f"JSON file not found at {json_file_path}")
            )
        except json.JSONDecodeError:
            self.stdout.write(self.style.ERROR("Invalid JSON format in the file"))
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Error updating furniture data: {str(e)}")
            )
