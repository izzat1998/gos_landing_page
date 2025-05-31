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

                # Find or create the category
                category, created = FurnitureCategory.objects.get_or_create(
                    name=category_name,
                    defaults={
                        "slug": slugify(category_name),
                        "description": f"Collection of {category_name.lower()}",
                        "order": 0,
                        "is_active": True,
                    },
                )

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
                            item.slug = slugify(new_name)
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
