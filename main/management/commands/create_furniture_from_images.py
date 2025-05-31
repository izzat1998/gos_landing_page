import os
import shutil
import time

from django.core.management.base import BaseCommand
from django.utils.text import slugify

from main.models import FurnitureCategory, FurnitureItem


class Command(BaseCommand):
    help = "Create furniture items from images in a directory with sequential naming"

    def add_arguments(self, parser):
        parser.add_argument(
            "--directory",
            type=str,
            help="Directory containing images to use for furniture items",
            default="/var/www/gos_landing_page/pod_tv",
        )
        parser.add_argument(
            "--category",
            type=str,
            help="Category name for the furniture items",
            default="Под ТВ",
        )
        parser.add_argument(
            "--prefix",
            type=str,
            help="Prefix for the sequential naming",
            default="pod_tv",
        )

    def handle(self, *args, **options):
        directory = options["directory"]
        category_name = options["category"]
        prefix = options["prefix"]

        # Check if directory exists
        if not os.path.exists(directory):
            self.stdout.write(self.style.ERROR(f"Directory {directory} does not exist"))
            return

        # Get the category
        try:
            category = FurnitureCategory.objects.get(name=category_name)
            self.stdout.write(self.style.SUCCESS(f"Found category: {category_name}"))
        except FurnitureCategory.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f"Category {category_name} does not exist")
            )
            return

        # Get all image files from the directory
        image_files = []
        for file in os.listdir(directory):
            if file.lower().endswith((".jpg", ".jpeg", ".png", ".gif")):
                image_files.append(file)

        if not image_files:
            self.stdout.write(self.style.ERROR(f"No image files found in {directory}"))
            return

        # Create media directory if it doesn't exist
        media_root = os.path.join(os.path.dirname(directory), "media")
        furniture_media_dir = os.path.join(media_root, "furniture_images")
        os.makedirs(furniture_media_dir, exist_ok=True)

        # Create furniture items with sequential naming
        timestamp = int(time.time())
        for i, image_file in enumerate(image_files, 1):
            # Generate name and description
            name = f"{prefix}_{i}"
            description = f"Description for {prefix}_{i}"
            # Use timestamp in slug to ensure uniqueness
            slug = f"{slugify(name)}_{timestamp}"

            # Create the furniture item
            furniture_item = FurnitureItem.objects.create(
                name=name,
                slug=slug,
                description=description,
                category=category,
                is_featured=False,
                is_active=True,
                dimensions="",
                materials="",
            )

            # Copy the image file to media directory
            source_path = os.path.join(directory, image_file)

            # Get file extension
            _, ext = os.path.splitext(image_file)

            # Create a unique filename to avoid conflicts, ensure it's not too long
            # Django's FileField typically has a max_length of 100 characters
            max_filename_length = 80  # Leave some room for the relative path
            base_filename = f"{slug}_{i}{ext}"

            # Truncate if necessary
            if len(base_filename) > max_filename_length:
                base_filename = f"{slug[:30]}_{i}{ext}"  # Truncate the slug part

            dest_filename = base_filename
            dest_path = os.path.join(furniture_media_dir, dest_filename)

            try:
                # Copy the file
                shutil.copy2(source_path, dest_path)

                # Set the main_image field on the furniture item
                relative_path = os.path.join("furniture_images", dest_filename)
                furniture_item.main_image = relative_path
                furniture_item.save()

                self.stdout.write(
                    self.style.SUCCESS(
                        f"Created item {name} with image {dest_filename}"
                    )
                )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"Error copying image {image_file}: {str(e)}")
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully created {len(image_files)} furniture items"
            )
        )
