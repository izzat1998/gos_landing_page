import json
import os

from django.core.management.base import BaseCommand
from django.utils.text import slugify

from main.models import FurnitureCategory, FurnitureItem

# Category mapping from JSON file to database categories
CATEGORY_MAPPING = {
    "Детская мебель": "Детская мебель",
    "Офисная мебель": "Офисная Мебель",
    # Add other mappings if needed
}


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

                # Map to the correct database category name if it exists
                db_category_name = CATEGORY_MAPPING.get(category_name, category_name)

                # Try to find the existing category
                try:
                    category = FurnitureCategory.objects.get(name=db_category_name)
                    self.stdout.write(f"Found existing category: {db_category_name}")
                except FurnitureCategory.DoesNotExist:
                    # If category doesn't exist, create a new one with a proper slug
                    category_slug = ""

                    # Determine the slug based on what we see in the database
                    if db_category_name == "Детская мебель":
                        category_slug = "detskaya-mebel"
                    elif db_category_name == "Офисная Мебель":
                        category_slug = "ofisnaya-mebel"
                    elif db_category_name == "Кухни":
                        category_slug = "kuhni"
                    elif db_category_name == "Мягкая Мебель":
                        category_slug = "myahkii-mebel"
                    elif db_category_name == "Под ТВ":
                        category_slug = "gostinye"
                    elif db_category_name == "Спальни":
                        category_slug = "spalni"
                    elif db_category_name == "Шкафы":
                        category_slug = "shkaf"
                    else:
                        # Fallback for any new categories
                        category_slug = (
                            slugify(db_category_name)
                            or f"category-{hash(db_category_name) % 10000}"
                        )

                    category = FurnitureCategory.objects.create(
                        name=db_category_name,
                        slug=category_slug,
                        description=f"Collection of {db_category_name.lower()}",
                        order=0,
                        is_active=True,
                    )
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"Created new category: {db_category_name} with slug: {category_slug}"
                        )
                    )

                # Ensure the category has a valid slug
                if not category.slug:
                    if db_category_name == "Детская мебель":
                        category.slug = "detskaya-mebel"
                    elif db_category_name == "Офисная Мебель":
                        category.slug = "ofisnaya-mebel"
                    else:
                        category.slug = f"category-{category.id}"
                    category.save()
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"Updated empty slug for category: {category.name}"
                        )
                    )

                # This section is now handled in the try/except block above

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
                        # Create a new item
                        # Generate a valid slug
                        new_slug = slugify(new_name)
                        if not new_slug:
                            # Create a unique slug if slugify produces an empty string
                            new_slug = f"item-{hash(new_name) % 10000}"

                        # Create the new item
                        FurnitureItem.objects.create(
                            name=new_name,
                            slug=new_slug,
                            description=description,
                            category=category,
                            is_featured=False,
                            is_active=True,
                            dimensions="",  # Empty dimensions
                            materials="",  # Empty materials
                        )
                        self.stdout.write(
                            self.style.SUCCESS(
                                f"Created new item: {new_name} (from {old_name})"
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
