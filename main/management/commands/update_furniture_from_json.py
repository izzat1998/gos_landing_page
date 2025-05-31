import json
import os

from django.core.management.base import BaseCommand
from django.utils.text import slugify

from main.models import FurnitureCategory, FurnitureItem


class Command(BaseCommand):
    help = "Update furniture items from JSON file using old_name to find items and update with new_name and description"

    def add_arguments(self, parser):
        parser.add_argument(
            "--json-file",
            type=str,
            help="Path to JSON file with furniture data",
            default="/home/izzat/Tohir aka/gos-landing-page/all_files.json",
        )

    def handle(self, *args, **options):
        json_file_path = options["json_file"]

        # Check if file exists
        if not os.path.exists(json_file_path):
            self.stdout.write(self.style.ERROR(f"File {json_file_path} does not exist"))
            return

        # Read the JSON data
        self.stdout.write(f"Reading data from {json_file_path}")
        with open(json_file_path, "r", encoding="utf-8") as file:
            data = json.load(file)

        # Track statistics
        stats = {
            "updated": 0,
            "not_found": 0,
            "categories_processed": 0,
        }

        # Process each category
        for category_name, items in data.items():
            stats["categories_processed"] += 1
            self.stdout.write(f"Processing category: {category_name}")

            # Try to find the category
            try:
                category = FurnitureCategory.objects.get(name=category_name)
                self.stdout.write(
                    self.style.SUCCESS(f"Found category: {category_name}")
                )
            except FurnitureCategory.DoesNotExist:
                self.stdout.write(
                    self.style.WARNING(
                        f"Category {category_name} not found. Skipping items in this category."
                    )
                )
                continue

            # Process each item in the category
            for item_data in items:
                old_name = item_data.get("old_name", "")
                new_name = item_data.get("new_name", "")
                description = item_data.get("description", "")

                if not old_name or not new_name:
                    self.stdout.write(
                        self.style.WARNING(
                            f"Skipping item with missing old_name or new_name: {item_data}"
                        )
                    )
                    continue

                # Try to find the item by old_name
                try:
                    item = FurnitureItem.objects.get(name=old_name, category=category)

                    # Update the item
                    item.name = new_name
                    item.description = description

                    # Update slug if needed
                    new_slug = slugify(new_name)
                    if not new_slug:
                        # If slugify produces an empty string (e.g., for non-Latin characters),
                        # create a slug based on the item ID
                        new_slug = f"item-{item.id}"

                    item.slug = new_slug
                    item.save()

                    stats["updated"] += 1
                    self.stdout.write(
                        self.style.SUCCESS(f"Updated item: {old_name} → {new_name}")
                    )
                except FurnitureItem.DoesNotExist:
                    stats["not_found"] += 1
                    self.stdout.write(
                        self.style.WARNING(
                            f"Item not found: {old_name} in category {category_name}"
                        )
                    )

        # Print summary
        self.stdout.write(
            self.style.SUCCESS(
                f"Furniture update completed! "
                f"Categories processed: {stats['categories_processed']}, "
                f"Items updated: {stats['updated']}, "
                f"Items not found: {stats['not_found']}"
            )
        )
