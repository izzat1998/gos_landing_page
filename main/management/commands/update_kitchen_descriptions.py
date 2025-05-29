import re

from django.core.management.base import BaseCommand
from django.db import transaction

from main.models import FurnitureCategory, FurnitureItem


class Command(BaseCommand):
    help = "Update kitchen furniture descriptions from a text file"

    def handle(self, *args, **options):
        # Get the kitchen category
        try:
            kitchen_category = FurnitureCategory.objects.get(name="Кухни")
            self.stdout.write(
                self.style.SUCCESS(f"Found kitchen category: {kitchen_category}")
            )
        except FurnitureCategory.DoesNotExist:
            self.stdout.write(self.style.ERROR("Kitchen category not found!"))
            return

        # Read and parse the kitchen.txt file
        descriptions = self.parse_kitchen_file()
        if not descriptions:
            self.stdout.write(self.style.ERROR("No descriptions found in kitchen.txt"))
            return

        # Update furniture items
        self.update_furniture_descriptions(kitchen_category, descriptions)

    def parse_kitchen_file(self):
        """Parse the kitchen.txt file to extract furniture IDs and descriptions."""
        descriptions = {}

        try:
            with open("kitchen.txt", "r", encoding="utf-8") as file:
                content = file.read()

            # Split the content by the arrow separator
            items = content.split("➔")

            for item in items:
                if not item.strip():
                    continue

                # Extract the ID (first line) and description (second line)
                lines = item.strip().split("\n")
                if len(lines) >= 2:
                    furniture_id = lines[0].strip()
                    description = lines[1].strip()

                    # Skip the "Цена по запросу" line if present
                    if "Цена по запросу" in description:
                        if len(lines) >= 3:
                            description = lines[1].strip()
                        else:
                            continue

                    descriptions[furniture_id] = description

            self.stdout.write(
                self.style.SUCCESS(
                    f"Parsed {len(descriptions)} descriptions from kitchen.txt"
                )
            )
            return descriptions

        except FileNotFoundError:
            self.stdout.write(self.style.ERROR("kitchen.txt file not found!"))
            return {}
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error parsing kitchen.txt: {e}"))
            return {}

    @transaction.atomic
    def update_furniture_descriptions(self, kitchen_category, descriptions):
        """Update furniture descriptions for items in the kitchen category."""
        # Get all furniture items in the kitchen category
        kitchen_items = FurnitureItem.objects.filter(category=kitchen_category)

        updated_count = 0
        not_found_ids = []

        for furniture_id, description in descriptions.items():
            # Try to find a matching furniture item by name/ID
            matching_items = kitchen_items.filter(name=furniture_id)

            if matching_items.exists():
                for item in matching_items:
                    item.description = description
                    item.save()
                    updated_count += 1
                    self.stdout.write(f"Updated description for: {item.name}")
            else:
                not_found_ids.append(furniture_id)
                

        # Summary
        self.stdout.write(
            self.style.SUCCESS(f"Updated {updated_count} furniture items")
        )

        if not_found_ids:
            self.stdout.write(
                self.style.WARNING(
                    f"Could not find {len(not_found_ids)} items: {', '.join(not_found_ids)}"
                )
            )
