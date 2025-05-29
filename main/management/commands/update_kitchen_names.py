import json

from django.core.management.base import BaseCommand
from django.db import transaction

from main.models import FurnitureCategory, FurnitureItem


class Command(BaseCommand):
    help = "Update kitchen furniture names based on a JSON mapping"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be updated without making changes",
        )

    def handle(self, *args, **options):
        dry_run = options.get("dry_run", False)
        
        # Get the kitchen category
        try:
            kitchen_category = FurnitureCategory.objects.get(name="Кухни")
            self.stdout.write(
                self.style.SUCCESS(f"Found kitchen category: {kitchen_category}")
            )
        except FurnitureCategory.DoesNotExist:
            self.stdout.write(self.style.ERROR("Kitchen category not found!"))
            return

        # Load the name mapping
        name_mapping = self.get_name_mapping()
        if not name_mapping:
            self.stdout.write(self.style.ERROR("No name mapping available"))
            return

        # Update furniture names
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN - No changes will be made"))
            
        self.update_furniture_names(kitchen_category, name_mapping, dry_run)

    def get_name_mapping(self):
        """Define the mapping from old IDs/names to new names."""
        mapping = {
            "10": "Дымчатый Минимал",
            "11": "Светлый Рельеф",
            "12": "Графитовая Ночь",
            "13": "Лесной Уют",
            "14": "Арктик Вуд",
            "15": "Серый Монолит",
            "17": "Лофт Акцент",
            "18": "Венге Элеганс",
            "19": "Нордик Контраст",
            "20": "Солнечный Шпон",
            "21": "Темный Орех",
            "22": "Пыльная Роза",
            "23": "Графит Спейс",
            "24": "Антрацит Лайн",
            "25": "Черный Бархат",
            "26": "Альпийская Свежесть",
            "27": "Кантри Модерн",
            "28": "Нуар Марбл",
            "29": "Индустриальный Шик",
            "30": "Мраморный Акцент",
            "31": "Белоснежный Глянец",
            "32": "Студио Лайт",
            "33": "Кремовый Бриз",
            "34": "Синий Горизонт",
            "35": "Урбан Вуд",
            "36": "Компакт Свет",
            "37": "Неоклассика Беж",
            "38": "Версаль Крем",
            "39": "Дуэт Текстур",
            "4": "Биколор Модерн",
            "40": "Серенити Грей",
            "41": "Монохром Грей",
            "42": "Классика Латте",
            "43": "Элеганс Лайн",
            "44": "Контраст Вуд",
            "45": "Арктик Блэк",
            "46": "Золотой Штрих",
            "47": "Стоун Найт",
            "48": "Винтаж Лофт",
            "49": "Капучино Мист",
            "5": "Сканди Грейвуд",
            "50": "Белая Волна",
            "51": "Аристократ Марбл",
            "8": "Графит Уайт",
            "9": "Жемчужный Минимал",
            "kuhnya 2": "Урбан Грей Лайт",
            "kuhnya1": "Престиж Лайн",
            "Кухня 1": "Бейсик Беж",
            "kuhnya3": "Контраст Стоун",
            "Кухни 3": "Модерн Графит"
        }
        
        return mapping

    @transaction.atomic
    def update_furniture_names(self, kitchen_category, name_mapping, dry_run=False):
        """Update furniture names for items in the kitchen category."""
        # Get all furniture items in the kitchen category
        kitchen_items = FurnitureItem.objects.filter(category=kitchen_category)
        
        updated_count = 0
        not_found_ids = set()
        
        # First pass: try exact matches on IDs/names
        for old_id, new_name in name_mapping.items():
            # Try to find items with exact name match
            matching_items = kitchen_items.filter(name=old_id)
            
            # If no exact match, try to find items containing the ID
            if not matching_items.exists():
                matching_items = kitchen_items.filter(name__contains=old_id)
            
            if matching_items.exists():
                for item in matching_items:
                    old_name = item.name
                    if not dry_run:
                        item.name = new_name
                        # Generate a new slug based on the new name
                        item.slug = None  # Will be auto-generated on save
                        item.save()
                    
                    self.stdout.write(
                        f"{'Would update' if dry_run else 'Updated'}: {old_name} → {new_name}"
                    )
                    updated_count += 1
            else:
                not_found_ids.add(old_id)
        
        # Summary
        self.stdout.write(
            self.style.SUCCESS(
                f"{'Would update' if dry_run else 'Updated'} {updated_count} furniture items"
            )
        )
        
        if not_found_ids:
            self.stdout.write(
                self.style.WARNING(
                    f"Could not find {len(not_found_ids)} items: {', '.join(not_found_ids)}"
                )
            )
