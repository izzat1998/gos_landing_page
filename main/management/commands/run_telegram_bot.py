import datetime
import logging

import requests
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db.models import Count
from django.utils import timezone
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
)

from main.models import Location, QRCodeScan

User = get_user_model()
logger = logging.getLogger(__name__)

# Список имен пользователей администраторов, которые могут получить доступ к командам администратора
ADMIN_USERNAMES = [
    "Iforce706",
    "subanovsh",
]  # Добавьте сюда имена пользователей Telegram администраторов


class Command(BaseCommand):
    help = "Запускает Telegram бота для статистики QR-кодов"

    def handle(self, *args, **kwargs):
        # Настройка логирования
        logging.basicConfig(
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            level=logging.INFO,
        )

        # Создание приложения
        application = ApplicationBuilder().token(settings.TELEGRAM_BOT_TOKEN).build()

        # Добавление обработчиков команд
        application.add_handler(CommandHandler("start", self.start_command))
        application.add_handler(CommandHandler("stats", self.stats_command))
        application.add_handler(CommandHandler("help", self.help_command))
        application.add_handler(CommandHandler("admin", self.admin_command))
        application.add_handler(CommandHandler("allstats", self.all_stats_command))
        application.add_handler(CommandHandler("compare", self.compare_command))
        application.add_handler(CommandHandler("dashboard", self.dashboard_command))

        # Добавление обработчика запросов обратного вызова для встроенных кнопок
        application.add_handler(CallbackQueryHandler(self.button_callback))

        self.stdout.write("Запуск Telegram бота...")
        application.run_polling()

    def is_admin(self, username):
        """Проверяет, находится ли имя пользователя в списке администраторов"""
        return username in ADMIN_USERNAMES

    # For the start_command
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Отправляет приветственное сообщение при вызове команды /start."""
        user = update.effective_user
        is_admin = self.is_admin(user.username)

        print(
            f"[DEBUG] start_command called by user: {user.username} (first_name: {user.first_name})"
        )
        print(f"[DEBUG] User admin status: {is_admin}")

        # Rest of the function remains the same

    # For the help_command
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Отправляет справочное сообщение при вызове команды /help."""
        user = update.effective_user
        is_admin = self.is_admin(user.username)

        print(
            f"[DEBUG] help_command called by user: {user.username} (first_name: {user.first_name})"
        )
        print(f"[DEBUG] User admin status: {is_admin}")

        # Rest of the function remains the same

    # For the admin_command
    async def admin_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показывает команды администратора"""
        user = update.effective_user

        print(
            f"[DEBUG] admin_command called by user: {user.username} (first_name: {user.first_name})"
        )
        print(f"[DEBUG] User admin status: {self.is_admin(user.username)}")

        if not self.is_admin(user.username):
            print(
                f"[DEBUG] Access denied for user: {user.username} - not in admin list"
            )
            await update.message.reply_text(
                "⛔ У вас нет разрешения на использование команд администратора."
            )
            return

        # Rest of the function remains the same

    # For the stats_command
    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Получает и отображает статистику QR-кодов."""
        user = update.effective_user
        print(
            f"[DEBUG] stats_command called by user: {user.username} (first_name: {user.first_name})"
        )

        # Получаем параметр дней, если он указан (по умолчанию: 30)
        days = 30
        if context.args and context.args[0].isdigit():
            days = int(context.args[0])

        print(f"[DEBUG] Stats requested for last {days} days")

        # Получаем статистику из API
        api_url = f"{settings.SITE_URL}/api/location-stats/?days={days}"
        headers = {"Authorization": f"Token {settings.API_TOKEN}"}

        # Выводим отладочную информацию
        print(f"[DEBUG] Connecting to API URL: {api_url}")
        print(f"[DEBUG] Using API token starting with: {settings.API_TOKEN[:5]}...")
        logger.info(f"Attempting to connect to API at: {api_url}")
        logger.info(f"Using API token: {settings.API_TOKEN[:5]}...")

        try:
            # Проверяем настройки
            if not settings.SITE_URL or settings.SITE_URL == "http://localhost:8000":
                print(
                    f"[DEBUG] Configuration error: SITE_URL not properly configured: {settings.SITE_URL}"
                )
                logger.error(
                    f"SITE_URL is not properly configured: {settings.SITE_URL}"
                )
                await update.message.reply_text(
                    "Ошибка конфигурации: SITE_URL не настроен правильно. Обратитесь к администратору."
                )
                return

            if not settings.API_TOKEN or settings.API_TOKEN == "your_api_token_here":
                print(f"[DEBUG] Configuration error: API_TOKEN not properly configured")
                logger.error("API_TOKEN is not properly configured")
                await update.message.reply_text(
                    "Ошибка конфигурации: API_TOKEN не настроен. Запустите 'python manage.py create_api_token admin' и обновите .env файл."
                )
                return

            # Пробуем получить данные
            print(f"[DEBUG] Sending GET request to API with timeout of 10 seconds")
            response = requests.get(api_url, headers=headers, timeout=10)

            print(f"[DEBUG] API response status code: {response.status_code}")

            # Проверяем статус ответа
            if response.status_code != 200:
                print(
                    f"[DEBUG] API error: Status {response.status_code}, Response body: {response.text}"
                )
                logger.error(
                    f"API returned status code: {response.status_code}, Response: {response.text}"
                )
                await update.message.reply_text(
                    f"Ошибка API: Статус {response.status_code}. Убедитесь, что сервер запущен и API доступен."
                )
                return

            data = response.json()
            print(
                f"[DEBUG] Successfully parsed API response: {len(data)} location(s) found"
            )

            if not data:
                print(f"[DEBUG] No QR code scan data available")
                await update.message.reply_text(
                    "Данные о сканированиях QR-кодов пока отсутствуют."
                )
                return

            # Формируем сообщение
            message = "📊 Статистика QR-кодов (Последние {} дней)\n\n".format(days)

            for location in data:
                print(
                    f"[DEBUG] Location: {location['name']} - Total scans: {location['total_scans']}, Recent scans: {location['recent_scans']}"
                )
                message += f"*{location['name']}*\n"
                message += f"Всего сканирований: {location['total_scans']}\n"
                message += f"Недавние сканирования ({days} дней): {location['recent_scans']}\n\n"

            print(f"[DEBUG] Sending stats message with {len(data)} locations")
            await update.message.reply_text(message, parse_mode="Markdown")
        except requests.exceptions.ConnectionError as e:
            print(f"[DEBUG] Connection error: {str(e)}")
            logger.error(f"Connection error: {str(e)}")
            await update.message.reply_text(
                "Ошибка подключения к API. Убедитесь, что сервер Django запущен и доступен."
            )
        except requests.exceptions.Timeout as e:
            print(f"[DEBUG] Timeout error: {str(e)}")
            logger.error(f"Timeout error: {str(e)}")
            await update.message.reply_text(
                "Превышено время ожидания ответа от API. Сервер может быть перегружен."
            )
        except Exception as e:
            print(f"[DEBUG] Unexpected error: {str(e)}")
            print(f"[DEBUG] Error type: {type(e).__name__}")
            import traceback

            print(f"[DEBUG] Traceback: {traceback.format_exc()}")
            logger.error(f"Error fetching statistics: {str(e)}")
            await update.message.reply_text(
                f"Ошибка при получении статистики: {str(e)}. Пожалуйста, попробуйте позже."
            )

    # For the all_stats_command
    async def all_stats_command(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Получает и отображает статистику по всем локациям (только для администраторов)"""
        user = update.effective_user
        print(
            f"[DEBUG] all_stats_command called by user: {user.username} (first_name: {user.first_name})"
        )
        print(f"[DEBUG] User admin status: {self.is_admin(user.username)}")

        if not self.is_admin(user.username):
            print(
                f"[DEBUG] Access denied for user: {user.username} - not in admin list"
            )
            await update.message.reply_text(
                "⛔ У вас нет разрешения на использование этой команды."
            )
            return

        # Получаем параметр дней, если он указан (по умолчанию: 30)
        days = 30
        if context.args and context.args[0].isdigit():
            days = int(context.args[0])

        print(f"[DEBUG] All stats requested for last {days} days")

        # Рассчитываем диапазоны дат
        today = timezone.now().date()
        start_date = today - datetime.timedelta(days=days)
        print(f"[DEBUG] Date range: from {start_date} to {today}")

        try:
            # Получаем все локации
            locations = Location.objects.all()
            print(f"[DEBUG] Found {locations.count()} locations in database")

            if not locations.exists():
                print(f"[DEBUG] No locations found in database")
                await update.message.reply_text("В базе данных не найдено локаций.")
                return

            # Рассчитываем общее количество сканирований по всем локациям
            total_scans = QRCodeScan.objects.count()
            recent_scans = QRCodeScan.objects.filter(
                timestamp__date__gte=start_date
            ).count()

            print(f"[DEBUG] Total scans across all locations: {total_scans}")
            print(f"[DEBUG] Recent scans (last {days} days): {recent_scans}")

            # Формируем сообщение
            message = (
                f"📊 *Статистика QR-кодов - Все локации (Последние {days} дней)*\n\n"
            )
            message += f"*Всего сканирований по всем локациям: {total_scans}*\n"
            message += (
                f"*Недавние сканирования (Последние {days} дней): {recent_scans}*\n\n"
            )
            message += "*Разбивка по локациям:*\n\n"

            # Добавляем статистику для каждой локации
            for location in locations:
                location_total = location.scans.count()
                location_recent = location.scans.filter(
                    timestamp__date__gte=start_date
                ).count()

                percentage = 0
                if total_scans > 0:
                    percentage = (location_total / total_scans) * 100

                print(
                    f"[DEBUG] Location: {location.name} - Total: {location_total}, Recent: {location_recent}, Percentage: {percentage:.1f}%"
                )

                message += f"*{location.name}*\n"
                message += f"Всего сканирований: {location_total}\n"
                message += f"Недавние сканирования ({days} дней): {location_recent}\n"

                # Рассчитываем процент от общего числа сканирований
                if total_scans > 0:
                    message += f"Процент от общего числа: {percentage:.1f}%\n"

                message += "\n"

            print(
                f"[DEBUG] Sending all stats message with {locations.count()} locations"
            )
            await update.message.reply_text(message, parse_mode="Markdown")
        except Exception as e:
            print(f"[DEBUG] Unexpected error in all_stats_command: {str(e)}")
            print(f"[DEBUG] Error type: {type(e).__name__}")
            import traceback

            print(f"[DEBUG] Traceback: {traceback.format_exc()}")
            logger.error(f"Error fetching all statistics: {str(e)}")
            await update.message.reply_text(
                f"Ошибка при получении статистики. Пожалуйста, попробуйте позже."
            )

    # For the compare_command
    async def compare_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Сравнивает статистику между локациями (только для администраторов)"""
        user = update.effective_user
        print(
            f"[DEBUG] compare_command called by user: {user.username} (first_name: {user.first_name})"
        )
        print(f"[DEBUG] User admin status: {self.is_admin(user.username)}")

        if not self.is_admin(user.username):
            print(
                f"[DEBUG] Access denied for user: {user.username} - not in admin list"
            )
            await update.message.reply_text(
                "⛔ У вас нет разрешения на использование этой команды."
            )
            return

        try:
            # Получаем все локации
            locations = Location.objects.all()
            print(f"[DEBUG] Found {locations.count()} locations in database")

            if not locations.exists() or locations.count() < 2:
                print(
                    f"[DEBUG] Insufficient locations for comparison: {locations.count()} found, need at least 2"
                )
                await update.message.reply_text(
                    "Необходимо минимум две локации для сравнения."
                )
                return

            # Рассчитываем периоды времени
            today = timezone.now().date()
            yesterday = today - datetime.timedelta(days=1)
            last_week = today - datetime.timedelta(days=7)
            last_month = today - datetime.timedelta(days=30)

            print(f"[DEBUG] Date ranges for comparison:")
            print(f"[DEBUG] Today: {today}")
            print(f"[DEBUG] Yesterday: {yesterday}")
            print(f"[DEBUG] Last week from: {last_week}")
            print(f"[DEBUG] Last month from: {last_month}")

            # Формируем сообщение
            message = "📊 *Сравнение локаций*\n\n"

            # Сканирования за сегодня
            message += "*Сканирования за сегодня:*\n"
            print(f"[DEBUG] Calculating scans for today")
            for location in locations:
                today_count = location.scans.filter(timestamp__date=today).count()
                print(
                    f"[DEBUG] Location: {location.name} - Today's scans: {today_count}"
                )
                message += f"{location.name}: {today_count}\n"

            # Сканирования за вчера
            message += "\n*Сканирования за вчера:*\n"
            print(f"[DEBUG] Calculating scans for yesterday")
            for location in locations:
                yesterday_count = location.scans.filter(
                    timestamp__date=yesterday
                ).count()
                print(
                    f"[DEBUG] Location: {location.name} - Yesterday's scans: {yesterday_count}"
                )
                message += f"{location.name}: {yesterday_count}\n"

            # Последние 7 дней
            message += "\n*Последние 7 дней:*\n"
            print(f"[DEBUG] Calculating scans for last 7 days")
            for location in locations:
                week_count = location.scans.filter(
                    timestamp__date__gte=last_week
                ).count()
                print(
                    f"[DEBUG] Location: {location.name} - Last 7 days scans: {week_count}"
                )
                message += f"{location.name}: {week_count}\n"

            # Последние 30 дней
            message += "\n*Последние 30 дней:*\n"
            print(f"[DEBUG] Calculating scans for last 30 days")
            for location in locations:
                month_count = location.scans.filter(
                    timestamp__date__gte=last_month
                ).count()
                print(
                    f"[DEBUG] Location: {location.name} - Last 30 days scans: {month_count}"
                )
                message += f"{location.name}: {month_count}\n"

            # Все время
            message += "\n*Все время:*\n"
            print(f"[DEBUG] Calculating all-time scans")
            for location in locations:
                total_count = location.scans.count()
                print(
                    f"[DEBUG] Location: {location.name} - All time scans: {total_count}"
                )
                message += f"{location.name}: {total_count}\n"

            print(
                f"[DEBUG] Sending comparison message with {locations.count()} locations"
            )
            await update.message.reply_text(message, parse_mode="Markdown")
        except Exception as e:
            print(f"[DEBUG] Unexpected error in compare_command: {str(e)}")
            print(f"[DEBUG] Error type: {type(e).__name__}")
            import traceback

            print(f"[DEBUG] Traceback: {traceback.format_exc()}")
            logger.error(f"Error comparing locations: {str(e)}")
            await update.message.reply_text(
                f"Ошибка при сравнении локаций. Пожалуйста, попробуйте позже."
            )

    # For the dashboard_command
    async def dashboard_command(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Отображает интерактивную панель с кнопками (только для администраторов)"""
        user = update.effective_user
        print(
            f"[DEBUG] dashboard_command called by user: {user.username} (first_name: {user.first_name})"
        )
        print(f"[DEBUG] User admin status: {self.is_admin(user.username)}")

        if not self.is_admin(user.username):
            print(
                f"[DEBUG] Access denied for user: {user.username} - not in admin list"
            )
            await update.message.reply_text(
                "⛔ У вас нет разрешения на использование этой команды."
            )
            return

        try:
            print(f"[DEBUG] Creating dashboard inline keyboard")
            # Создаем встроенную клавиатуру с опциями
            keyboard = [
                [
                    InlineKeyboardButton(
                        "Статистика за сегодня", callback_data="stats_today"
                    ),
                    InlineKeyboardButton(
                        "Статистика за вчера", callback_data="stats_yesterday"
                    ),
                ],
                [
                    InlineKeyboardButton(
                        "Последние 7 дней", callback_data="stats_7days"
                    ),
                    InlineKeyboardButton(
                        "Последние 30 дней", callback_data="stats_30days"
                    ),
                ],
                [
                    InlineKeyboardButton(
                        "Статистика за все время", callback_data="stats_alltime"
                    ),
                    InlineKeyboardButton(
                        "Сравнить локации", callback_data="compare_locations"
                    ),
                ],
            ]

            reply_markup = InlineKeyboardMarkup(keyboard)
            print(f"[DEBUG] Inline keyboard created with 6 buttons in 3 rows")

            print(f"[DEBUG] Sending dashboard message")
            await update.message.reply_text(
                "📊 *Панель статистики QR-кодов*\n\n"
                "Выберите опцию для просмотра статистики:",
                reply_markup=reply_markup,
                parse_mode="Markdown",
            )
        except Exception as e:
            print(f"[DEBUG] Unexpected error in dashboard_command: {str(e)}")
            print(f"[DEBUG] Error type: {type(e).__name__}")
            import traceback

            print(f"[DEBUG] Traceback: {traceback.format_exc()}")
            logger.error(f"Error displaying dashboard: {str(e)}")
            await update.message.reply_text(
                f"Ошибка при отображении панели. Пожалуйста, попробуйте позже."
            )

    # For the button_callback
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обрабатывает обратные вызовы кнопок с панели"""
        query = update.callback_query
        await query.answer()

        callback_data = query.data
        user = update.effective_user

        print(f"[DEBUG] Button callback received from user: {user.username}")
        print(f"[DEBUG] Callback data: {callback_data}")
        print(f"[DEBUG] User admin status: {self.is_admin(user.username)}")

        if not self.is_admin(user.username):
            print(
                f"[DEBUG] Access denied for user: {user.username} - not in admin list"
            )
            await query.edit_message_text(
                "⛔ У вас нет разрешения на использование этой функции."
            )
            return

        try:
            if callback_data == "stats_today":
                print(f"[DEBUG] Processing stats_today callback")
                # Получаем статистику за сегодня
                today = timezone.now().date()
                locations = Location.objects.all()
                print(f"[DEBUG] Today's date: {today}")
                print(f"[DEBUG] Found {locations.count()} locations")

                message = "\ud83d\udcca *Статистика за сегодня*\n\n"
                total_today = QRCodeScan.objects.filter(timestamp__date=today).count()
                print(f"[DEBUG] Total scans today across all locations: {total_today}")
                message += f"*Всего сканирований сегодня: {total_today}*\n\n"

                for location in locations:
                    today_count = location.scans.filter(timestamp__date=today).count()
                    print(
                        f"[DEBUG] Location: {location.name} - Today's scans: {today_count}"
                    )
                    message += f"*{location.name}*: {today_count} сканирований\n"

                # Добавляем кнопку возврата
                keyboard = [
                    [
                        InlineKeyboardButton(
                            "Вернуться к панели", callback_data="back_to_dashboard"
                        )
                    ]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                print(f"[DEBUG] Created back button for return to dashboard")

                print(f"[DEBUG] Sending today's stats message")
                await query.edit_message_text(
                    message, reply_markup=reply_markup, parse_mode="Markdown"
                )

            elif callback_data == "stats_yesterday":
                print(f"[DEBUG] Processing stats_yesterday callback")
                # Получаем статистику за вчера
                today = timezone.now().date()
                yesterday = today - datetime.timedelta(days=1)
                locations = Location.objects.all()
                print(f"[DEBUG] Yesterday's date: {yesterday}")
                print(f"[DEBUG] Found {locations.count()} locations")

                message = "\ud83d\udcca *Статистика за вчера*\n\n"
                total_yesterday = QRCodeScan.objects.filter(
                    timestamp__date=yesterday
                ).count()
                print(
                    f"[DEBUG] Total scans yesterday across all locations: {total_yesterday}"
                )
                message += f"*Всего сканирований вчера: {total_yesterday}*\n\n"

                for location in locations:
                    yesterday_count = location.scans.filter(
                        timestamp__date=yesterday
                    ).count()
                    print(
                        f"[DEBUG] Location: {location.name} - Yesterday's scans: {yesterday_count}"
                    )
                    message += f"*{location.name}*: {yesterday_count} сканирований\n"

                # Добавляем кнопку возврата
                keyboard = [
                    [
                        InlineKeyboardButton(
                            "Вернуться к панели", callback_data="back_to_dashboard"
                        )
                    ]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                print(f"[DEBUG] Created back button for return to dashboard")

                print(f"[DEBUG] Sending yesterday's stats message")
                await query.edit_message_text(
                    message, reply_markup=reply_markup, parse_mode="Markdown"
                )

            # Similar debug prints should be added to the remaining elif blocks

            elif callback_data == "stats_7days":
                print(f"[DEBUG] Processing stats_7days callback")
                # Debug the rest of this branch...

            elif callback_data == "stats_30days":
                print(f"[DEBUG] Processing stats_30days callback")
                # Debug the rest of this branch...

            elif callback_data == "stats_alltime":
                print(f"[DEBUG] Processing stats_alltime callback")
                # Debug the rest of this branch...

            elif callback_data == "compare_locations":
                print(f"[DEBUG] Processing compare_locations callback")
                # Debug the rest of this branch...

            elif callback_data == "back_to_dashboard":
                print(f"[DEBUG] Processing back_to_dashboard callback")
                # Debug the rest of this branch...

        except Exception as e:
            print(f"[DEBUG] Unexpected error in button_callback: {str(e)}")
            print(f"[DEBUG] Error type: {type(e).__name__}")
            print(f"[DEBUG] Callback data that caused error: {callback_data}")
            import traceback

            print(f"[DEBUG] Traceback: {traceback.format_exc()}")
            logger.error(f"Error handling button callback: {str(e)}")
            await query.edit_message_text(
                f"Ошибка при обработке запроса. Пожалуйста, попробуйте позже."
            )

    # For the handle method (initialization)
    def handle(self, *args, **kwargs):
        print(f"[DEBUG] Starting Telegram bot...")
        print(f"[DEBUG] SITE_URL: {settings.SITE_URL}")
        print(
            f"[DEBUG] API_TOKEN (first 5 chars): {settings.API_TOKEN[:5] if settings.API_TOKEN else 'Not set'}"
        )
        print(
            f"[DEBUG] TELEGRAM_BOT_TOKEN (first 5 chars): {settings.TELEGRAM_BOT_TOKEN[:5] if settings.TELEGRAM_BOT_TOKEN else 'Not set'}"
        )
        print(f"[DEBUG] ADMIN_USERNAMES: {ADMIN_USERNAMES}")

        # Rest of the method remains the same

    # Utility method to log database stats
    def log_database_stats(self):
        """Utility method to log database statistics for debugging"""
        try:
            location_count = Location.objects.count()
            scan_count = QRCodeScan.objects.count()
            user_count = User.objects.count()

            print(f"[DEBUG] Database statistics:")
            print(f"[DEBUG] - Locations: {location_count}")
            print(f"[DEBUG] - QR Code Scans: {scan_count}")
            print(f"[DEBUG] - Users: {user_count}")

            # Get most active locations
            locations_with_counts = Location.objects.annotate(
                scan_count=Count("scans")
            ).order_by("-scan_count")
            print(f"[DEBUG] Top locations by scan count:")
            for loc in locations_with_counts[:5]:  # Show top 5
                print(f"[DEBUG] - {loc.name}: {loc.scan_count} scans")

            # Get recent activity
            today = timezone.now().date()
            yesterday = today - datetime.timedelta(days=1)
            today_scans = QRCodeScan.objects.filter(timestamp__date=today).count()
            yesterday_scans = QRCodeScan.objects.filter(
                timestamp__date=yesterday
            ).count()

            print(f"[DEBUG] Recent activity:")
            print(f"[DEBUG] - Today ({today}): {today_scans} scans")
            print(f"[DEBUG] - Yesterday ({yesterday}): {yesterday_scans} scans")

        except Exception as e:
            print(f"[DEBUG] Error logging database stats: {str(e)}")
