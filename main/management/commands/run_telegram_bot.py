import datetime
import logging
import traceback

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

# Import debugging utilities
from .debug_log import get_log_file_path, log_api_request, log_function_call

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

        # Display log file location
        log_path = get_log_file_path()
        self.stdout.write(f"Debug logs will be written to: {log_path}")

        # Log key configuration settings
        logger.info(f"SITE_URL: {settings.SITE_URL}")
        logger.info(
            f"TELEGRAM_BOT_TOKEN configured: {'Yes' if settings.TELEGRAM_BOT_TOKEN else 'No'}"
        )
        logger.info(f"API_TOKEN configured: {'Yes' if settings.API_TOKEN else 'No'}")

        try:
            # Создание приложения
            application = (
                ApplicationBuilder().token(settings.TELEGRAM_BOT_TOKEN).build()
            )

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

            # Add error handler
            application.add_error_handler(self.error_handler)

            self.stdout.write("Запуск Telegram бота...")
            application.run_polling()
        except Exception as e:
            logger.error(f"Error initializing bot: {str(e)}")
            logger.error(traceback.format_exc())
            self.stdout.write(self.style.ERROR(f"Failed to start bot: {str(e)}"))

    async def error_handler(self, update, context):
        """Global error handler for all update types"""
        # Log the error
        logger.error(f"Exception while handling an update: {context.error}")
        logger.error(traceback.format_exc())

        # Log update info if available
        if update:
            if update.effective_user:
                user_id = update.effective_user.id
                username = update.effective_user.username
                logger.error(f"Update from user {user_id} (@{username})")

            if update.effective_message:
                logger.error(f"Message text: {update.effective_message.text}")

        # Notify user
        try:
            if update and update.effective_message:
                await update.effective_message.reply_text(
                    "Произошла ошибка при обработке запроса. Администратор уведомлен."
                )
        except Exception as e:
            logger.error(f"Error sending error message: {str(e)}")

    def is_admin(self, username):
        """Проверяет, находится ли имя пользователя в списке администраторов"""
        return username in ADMIN_USERNAMES

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Отправляет приветственное сообщение при вызове команды /start."""
        user = update.effective_user
        is_admin = self.is_admin(user.username)

        welcome_message = (
            f"👋 Добро пожаловать в бот статистики QR-кодов GOS Furniture, {user.first_name}!\n\n"
            "Используйте /stats для просмотра статистики сканирований QR-кодов\n"
            "Используйте /help для просмотра доступных команд"
        )

        if is_admin:
            welcome_message += "\n\n🔐 *Команды администратора*\n"
            welcome_message += "/admin - Показать команды администратора\n"
            welcome_message += "/allstats - Просмотр статистики по всем локациям\n"
            welcome_message += "/compare - Сравнить статистику между локациями\n"
            welcome_message += "/dashboard - Просмотр интерактивной панели"

        await update.message.reply_text(welcome_message, parse_mode="Markdown")

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Отправляет справочное сообщение при вызове команды /help."""
        user = update.effective_user
        is_admin = self.is_admin(user.username)

        help_message = (
            "Доступные команды:\n\n"
            "/stats - Просмотр статистики сканирований QR-кодов\n"
            "/stats 7 - Просмотр статистики за последние 7 дней\n"
            "/help - Показать это справочное сообщение"
        )

        if is_admin:
            help_message += "\n\n🔐 *Команды администратора*\n"
            help_message += "/admin - Показать команды администратора\n"
            help_message += "/allstats - Просмотр статистики по всем локациям\n"
            help_message += (
                "/allstats 7 - Просмотр всей статистики за последние 7 дней\n"
            )
            help_message += "/compare - Сравнить статистику между локациями\n"
            help_message += "/dashboard - Просмотр интерактивной панели"

        await update.message.reply_text(help_message, parse_mode="Markdown")

    async def admin_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показывает команды администратора"""
        user = update.effective_user

        if not self.is_admin(user.username):
            await update.message.reply_text(
                "⛔ У вас нет разрешения на использование команд администратора."
            )
            return

        admin_message = (
            "🔐 *Команды администратора*\n\n"
            "/allstats - Просмотр статистики по всем локациям\n"
            "/allstats 7 - Просмотр всей статистики за последние 7 дней\n"
            "/compare - Сравнить статистику между локациями\n"
            "/dashboard - Просмотр интерактивной панели с кнопками"
        )

        await update.message.reply_text(admin_message, parse_mode="Markdown")

    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Получает и отображает статистику QR-кодов."""
        user = update.effective_user
        log_function_call("stats_command", user.id, user.username)

        # Получаем параметр дней, если он указан (по умолчанию: 30)
        days = 30
        if context.args and context.args[0].isdigit():
            days = int(context.args[0])
            log_function_call("stats_command", user.id, user.username, f"days={days}")

        # Получаем статистику из API
        api_url = f"{settings.SITE_URL}/api/location-stats/?days={days}"
        headers = {"Authorization": f"Token {settings.API_TOKEN}"}

        # Выводим отладочную информацию
        logger.info(f"Attempting to connect to API at: {api_url}")
        logger.info(f"Using API token: {settings.API_TOKEN[:5]}...")

        try:
            # Проверяем настройки
            if not settings.SITE_URL or settings.SITE_URL == "http://localhost:8000":
                logger.error(
                    f"SITE_URL is not properly configured: {settings.SITE_URL}"
                )
                await update.message.reply_text(
                    "Ошибка конфигурации: SITE_URL не настроен правильно. Обратитесь к администратору."
                )
                return

            if not settings.API_TOKEN or settings.API_TOKEN == "your_api_token_here":
                logger.error("API_TOKEN is not properly configured")
                await update.message.reply_text(
                    "Ошибка конфигурации: API_TOKEN не настроен. Запустите 'python manage.py create_api_token admin' и обновите .env файл."
                )
                return

            # Пробуем получить данные
            try:
                response = requests.get(api_url, headers=headers, timeout=10)
                log_api_request(api_url, response.status_code, response.text[:200])
            except requests.exceptions.RequestException as req_err:
                log_api_request(api_url, error=str(req_err))
                raise

            # Проверяем статус ответа
            if response.status_code != 200:
                logger.error(
                    f"API returned status code: {response.status_code}, Response: {response.text}"
                )
                await update.message.reply_text(
                    f"Ошибка API: Статус {response.status_code}. Убедитесь, что сервер запущен и API доступен."
                )
                return

            data = response.json()

            if not data:
                await update.message.reply_text(
                    "Данные о сканированиях QR-кодов пока отсутствуют."
                )
                return

            # Формируем сообщение
            message = "📊 Статистика QR-кодов (Последние {} дней)\n\n".format(days)

            for location in data:
                message += f"*{location['name']}*\n"
                message += f"Всего сканирований: {location['total_scans']}\n"
                message += f"Недавние сканирования ({days} дней): {location['recent_scans']}\n\n"

            await update.message.reply_text(message, parse_mode="Markdown")
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Connection error: {str(e)}")
            logger.error(traceback.format_exc())
            log_function_call(
                "stats_command",
                user.id,
                user.username,
                error=f"Connection error: {str(e)}",
            )
            await update.message.reply_text(
                "Ошибка подключения к API. Убедитесь, что сервер Django запущен и доступен."
            )
        except requests.exceptions.Timeout as e:
            logger.error(f"Timeout error: {str(e)}")
            logger.error(traceback.format_exc())
            log_function_call(
                "stats_command",
                user.id,
                user.username,
                error=f"Timeout error: {str(e)}",
            )
            await update.message.reply_text(
                "Превышено время ожидания ответа от API. Сервер может быть перегружен."
            )
        except Exception as e:
            logger.error(f"Error fetching statistics: {str(e)}")
            logger.error(traceback.format_exc())
            log_function_call(
                "stats_command",
                user.id,
                user.username,
                error=f"General error: {str(e)}",
            )
            await update.message.reply_text(
                f"Ошибка при получении статистики: {str(e)}. Пожалуйста, попробуйте позже."
            )

    async def all_stats_command(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Получает и отображает статистику по всем локациям (только для администраторов)"""
        user = update.effective_user
        logger.info(
            f"all_stats_command called by user: {user.username} (ID: {user.id})"
        )

        # Check admin permissions
        if not self.is_admin(user.username):
            logger.warning(
                f"User {user.username} attempted to access admin command without permission"
            )
            await update.message.reply_text(
                "⛔ У вас нет разрешения на использование этой команды."
            )
            return

        # Get days parameter
        days = 30
        try:
            if context.args and context.args[0].isdigit():
                days = int(context.args[0])
                logger.info(f"Using custom days parameter: {days}")
        except Exception as e:
            logger.error(f"Error parsing days parameter: {str(e)}")
            # Continue with default value

        # Calculate date ranges
        try:
            today = timezone.now().date()
            start_date = today - datetime.timedelta(days=days)
            logger.info(f"Date range: {start_date} to {today}")
        except Exception as e:
            logger.error(f"Error calculating date range: {str(e)}")
            await update.message.reply_text(
                "Ошибка при расчете диапазона дат. Пожалуйста, попробуйте позже."
            )
            return

        # Send typing action to show the bot is processing
        await update.message.chat.send_action(action="typing")

        try:
            # Get all locations with safer query approach
            try:
                # First check if we can connect to the database at all
                from django.db import connection

                cursor = connection.cursor()
                cursor.execute("SELECT 1")
                cursor.fetchone()
                cursor.close()
                logger.info("Database connection test successful")

                # Use a simpler query first to test if Location model is accessible
                location_count = Location.objects.count()
                logger.info(f"Location count: {location_count}")

                if location_count == 0:
                    logger.warning("No locations found in database")
                    await update.message.reply_text("В базе данных не найдено локаций.")
                    return

                # Now fetch the locations
                locations = list(Location.objects.all())
                logger.info(f"Successfully fetched {len(locations)} locations")

            except Exception as db_err:
                logger.error(f"Database error fetching locations: {str(db_err)}")
                logger.error(traceback.format_exc())
                await update.message.reply_text(
                    "Ошибка при получении данных о локациях. Пожалуйста, попробуйте позже."
                )
                return

            # Calculate total scans
            try:
                total_scans = QRCodeScan.objects.count()
                recent_scans = QRCodeScan.objects.filter(
                    timestamp__date__gte=start_date
                ).count()
                logger.info(f"Total scans: {total_scans}, Recent scans: {recent_scans}")
            except Exception as db_err:
                logger.error(f"Database error counting scans: {str(db_err)}")
                logger.error(traceback.format_exc())
                await update.message.reply_text(
                    "Ошибка при подсчете сканирований. Пожалуйста, попробуйте позже."
                )
                return

            # Format message
            try:
                message = f"📊 *Статистика QR-кодов - Все локации (Последние {days} дней)*\n\n"
                message += f"*Всего сканирований по всем локациям: {total_scans}*\n"
                message += f"*Недавние сканирования (Последние {days} дней): {recent_scans}*\n\n"
                message += "*Разбивка по локациям:*\n\n"

                # Check if message is getting too long
                if (
                    len(message) > 3000
                ):  # Telegram has a 4096 char limit, leaving room for location data
                    logger.warning(
                        "Message is getting too long, might exceed Telegram limits"
                    )
            except Exception as fmt_err:
                logger.error(f"Error formatting message header: {str(fmt_err)}")
                logger.error(traceback.format_exc())
                await update.message.reply_text(
                    "Ошибка при форматировании сообщения. Пожалуйста, попробуйте позже."
                )
                return

            # Add statistics for each location
            location_errors = 0
            for location in locations:
                try:
                    location_name = location.name
                    logger.info(f"Processing location: {location_name}")

                    location_total = location.scans.count()
                    location_recent = location.scans.filter(
                        timestamp__date__gte=start_date
                    ).count()

                    logger.info(
                        f"Location {location_name}: Total={location_total}, Recent={location_recent}"
                    )

                    message += f"*{location_name}*\n"
                    message += f"Всего сканирований: {location_total}\n"
                    message += (
                        f"Недавние сканирования ({days} дней): {location_recent}\n"
                    )

                    # Calculate percentage
                    if total_scans > 0:
                        percentage = (location_total / total_scans) * 100
                        message += f"Процент от общего числа: {percentage:.1f}%\n"

                    message += "\n"

                    # Check if message is getting too long
                    if len(message) > 3800:  # Getting close to Telegram's limit
                        logger.warning("Message exceeds safe length, truncating")
                        message += (
                            "*Сообщение слишком длинное, показаны не все локации*\n"
                        )
                        break

                except Exception as loc_err:
                    logger.error(
                        f"Error processing location {getattr(location, 'name', 'unknown')}: {str(loc_err)}"
                    )
                    location_errors += 1
                    continue

            if location_errors > 0:
                logger.warning(f"Encountered errors with {location_errors} locations")
                message += f"\n*Примечание: Не удалось получить данные для {location_errors} локаций*\n"

            # Send the message
            logger.info(f"Sending all_stats message, length: {len(message)} characters")
            try:
                await update.message.reply_text(message, parse_mode="Markdown")
                logger.info("All stats message sent successfully")
            except Exception as send_err:
                logger.error(f"Error sending message: {str(send_err)}")
                logger.error(traceback.format_exc())

                # Try sending without markdown if that might be the issue
                if "can't parse entities" in str(send_err).lower():
                    logger.info("Attempting to send message without Markdown")
                    await update.message.reply_text(
                        "Ошибка форматирования. Отправка статистики без форматирования:"
                    )
                    # Strip markdown characters
                    plain_message = message.replace("*", "").replace("_", "")
                    await update.message.reply_text(plain_message)
                else:
                    await update.message.reply_text(
                        "Ошибка при отправке сообщения. Пожалуйста, попробуйте позже."
                    )

        except Exception as e:
            logger.error(f"Unexpected error in all_stats_command: {str(e)}")
            logger.error(traceback.format_exc())
            await update.message.reply_text(
                f"Ошибка при получении статистики: {str(e)}. Пожалуйста, попробуйте позже."
            )

    async def compare_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Сравнивает статистику между локациями (только для администраторов)"""
        user = update.effective_user

        if not self.is_admin(user.username):
            await update.message.reply_text(
                "⛔ У вас нет разрешения на использование этой команды."
            )
            return

        try:
            # Получаем все локации
            locations = Location.objects.all()

            if not locations.exists() or locations.count() < 2:
                await update.message.reply_text(
                    "Необходимо минимум две локации для сравнения."
                )
                return

            # Рассчитываем периоды времени
            today = timezone.now().date()
            yesterday = today - datetime.timedelta(days=1)
            last_week = today - datetime.timedelta(days=7)
            last_month = today - datetime.timedelta(days=30)

            # Формируем сообщение
            message = "📊 *Сравнение локаций*\n\n"

            # Сканирования за сегодня
            message += "*Сканирования за сегодня:*\n"
            for location in locations:
                today_count = location.scans.filter(timestamp__date=today).count()
                message += f"{location.name}: {today_count}\n"

            # Сканирования за вчера
            message += "\n*Сканирования за вчера:*\n"
            for location in locations:
                yesterday_count = location.scans.filter(
                    timestamp__date=yesterday
                ).count()
                message += f"{location.name}: {yesterday_count}\n"

            # Последние 7 дней
            message += "\n*Последние 7 дней:*\n"
            for location in locations:
                week_count = location.scans.filter(
                    timestamp__date__gte=last_week
                ).count()
                message += f"{location.name}: {week_count}\n"

            # Последние 30 дней
            message += "\n*Последние 30 дней:*\n"
            for location in locations:
                month_count = location.scans.filter(
                    timestamp__date__gte=last_month
                ).count()
                message += f"{location.name}: {month_count}\n"

            # Все время
            message += "\n*Все время:*\n"
            for location in locations:
                total_count = location.scans.count()
                message += f"{location.name}: {total_count}\n"

            await update.message.reply_text(message, parse_mode="Markdown")
        except Exception as e:
            logger.error(f"Error comparing locations: {str(e)}")
            await update.message.reply_text(
                f"Ошибка при сравнении локаций. Пожалуйста, попробуйте позже."
            )

    async def dashboard_command(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Отображает интерактивную панель с кнопками (только для администраторов)"""
        user = update.effective_user

        if not self.is_admin(user.username):
            await update.message.reply_text(
                "⛔ У вас нет разрешения на использование этой команды."
            )
            return

        try:
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

            await update.message.reply_text(
                "📊 *Панель статистики QR-кодов*\n\n"
                "Выберите опцию для просмотра статистики:",
                reply_markup=reply_markup,
                parse_mode="Markdown",
            )
        except Exception as e:
            logger.error(f"Error displaying dashboard: {str(e)}")
            await update.message.reply_text(
                f"Ошибка при отображении панели. Пожалуйста, попробуйте позже."
            )

    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обрабатывает обратные вызовы кнопок с панели"""
        if not update or not update.callback_query:
            logger.error(
                "Button callback received invalid update without callback_query"
            )
            return

        query = update.callback_query
        user = update.effective_user

        # Safely get callback data
        try:
            callback_data = query.data
            logger.info(
                f"Processing callback: {callback_data} from user {user.username}"
            )
        except Exception as e:
            logger.error(f"Error getting callback data: {str(e)}")
            return

        # Answer the callback query to prevent the "loading" state in Telegram
        try:
            await query.answer()
        except Exception as e:
            logger.error(f"Error answering callback query: {str(e)}")
            # Continue execution even if answering fails

        # Check admin permissions
        if not self.is_admin(user.username):
            try:
                await query.edit_message_text(
                    "⛔ У вас нет разрешения на использование этой функции."
                )
            except Exception as e:
                logger.error(f"Error editing message for non-admin: {str(e)}")
            return

        try:
            logger.info(f"Processing callback action: {callback_data}")

            if callback_data == "stats_today":
                try:
                    # Получаем статистику за сегодня
                    today = timezone.now().date()
                    logger.info(f"Fetching statistics for today: {today}")

                    # Safely query the database
                    try:
                        locations = Location.objects.all()
                        logger.info(f"Found {locations.count()} locations")
                    except Exception as db_err:
                        logger.error(
                            f"Database error fetching locations: {str(db_err)}"
                        )
                        await query.edit_message_text(
                            "Ошибка при получении данных о локациях."
                        )
                        return

                    message = "\ud83d\udcca *Статистика за сегодня*\n\n"

                    # Safely get total scans
                    try:
                        total_today = QRCodeScan.objects.filter(
                            timestamp__date=today
                        ).count()
                        message += f"*Всего сканирований сегодня: {total_today}*\n\n"
                    except Exception as db_err:
                        logger.error(f"Database error counting scans: {str(db_err)}")
                        total_today = 0
                        message += (
                            "*Ошибка при подсчете общего количества сканирований*\n\n"
                        )

                    # Process each location
                    for location in locations:
                        try:
                            today_count = location.scans.filter(
                                timestamp__date=today
                            ).count()
                            message += (
                                f"*{location.name}*: {today_count} сканирований\n"
                            )
                        except Exception as loc_err:
                            logger.error(
                                f"Error counting scans for location {location.name}: {str(loc_err)}"
                            )
                            message += f"*{location.name}*: Ошибка подсчета\n"

                    # Добавляем кнопку возврата
                    keyboard = [
                        [
                            InlineKeyboardButton(
                                "Вернуться к панели", callback_data="back_to_dashboard"
                            )
                        ]
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)

                    # Send the message
                    logger.info("Sending today's stats message")
                    await query.edit_message_text(
                        message, reply_markup=reply_markup, parse_mode="Markdown"
                    )
                    logger.info("Today's stats message sent successfully")

                except Exception as e:
                    logger.error(f"Error processing stats_today: {str(e)}")
                    logger.error(traceback.format_exc())
                    await query.edit_message_text(
                        "Ошибка при получении статистики за сегодня. Пожалуйста, попробуйте позже."
                    )

            elif callback_data == "stats_yesterday":
                # Получаем статистику за вчера
                today = timezone.now().date()
                yesterday = today - datetime.timedelta(days=1)
                locations = Location.objects.all()

                message = "\ud83d\udcca *Статистика за вчера*\n\n"
                total_yesterday = QRCodeScan.objects.filter(
                    timestamp__date=yesterday
                ).count()
                message += f"*Всего сканирований вчера: {total_yesterday}*\n\n"

                for location in locations:
                    yesterday_count = location.scans.filter(
                        timestamp__date=yesterday
                    ).count()
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

                await query.edit_message_text(
                    message, reply_markup=reply_markup, parse_mode="Markdown"
                )

            elif callback_data == "stats_7days":
                # Получаем статистику за последние 7 дней
                today = timezone.now().date()
                last_week = today - datetime.timedelta(days=7)
                locations = Location.objects.all()

                message = "\ud83d\udcca *Статистика за последние 7 дней*\n\n"
                total_week = QRCodeScan.objects.filter(
                    timestamp__date__gte=last_week
                ).count()
                message += f"*Всего сканирований (последние 7 дней): {total_week}*\n\n"

                for location in locations:
                    week_count = location.scans.filter(
                        timestamp__date__gte=last_week
                    ).count()
                    message += f"*{location.name}*: {week_count} сканирований\n"

                # Добавляем кнопку возврата
                keyboard = [
                    [
                        InlineKeyboardButton(
                            "Вернуться к панели", callback_data="back_to_dashboard"
                        )
                    ]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)

                await query.edit_message_text(
                    message, reply_markup=reply_markup, parse_mode="Markdown"
                )

            elif callback_data == "stats_30days":
                # Получаем статистику за последние 30 дней
                today = timezone.now().date()
                last_month = today - datetime.timedelta(days=30)
                locations = Location.objects.all()

                message = "\ud83d\udcca *Статистика за последние 30 дней*\n\n"
                total_month = QRCodeScan.objects.filter(
                    timestamp__date__gte=last_month
                ).count()
                message += (
                    f"*Всего сканирований (последние 30 дней): {total_month}*\n\n"
                )

                for location in locations:
                    month_count = location.scans.filter(
                        timestamp__date__gte=last_month
                    ).count()
                    message += f"*{location.name}*: {month_count} сканирований\n"

                # Добавляем кнопку возврата
                keyboard = [
                    [
                        InlineKeyboardButton(
                            "Вернуться к панели", callback_data="back_to_dashboard"
                        )
                    ]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)

                await query.edit_message_text(
                    message, reply_markup=reply_markup, parse_mode="Markdown"
                )

            elif callback_data == "stats_alltime":
                # Получаем статистику за все время
                locations = Location.objects.all()

                message = "\ud83d\udcca *Статистика за все время*\n\n"
                total_all = QRCodeScan.objects.count()
                message += f"*Всего сканирований (за все время): {total_all}*\n\n"

                for location in locations:
                    all_count = location.scans.count()
                    percentage = 0
                    if total_all > 0:
                        percentage = (all_count / total_all) * 100
                    message += f"*{location.name}*: {all_count} сканирований ({percentage:.1f}%)\n"

                # Добавляем кнопку возврата
                keyboard = [
                    [
                        InlineKeyboardButton(
                            "Вернуться к панели", callback_data="back_to_dashboard"
                        )
                    ]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)

                await query.edit_message_text(
                    message, reply_markup=reply_markup, parse_mode="Markdown"
                )

            elif callback_data == "compare_locations":
                # Сравниваем локации
                locations = Location.objects.all()

                if not locations.exists() or locations.count() < 2:
                    await query.edit_message_text(
                        "Необходимо минимум две локации для сравнения."
                    )
                    return

                # Рассчитываем периоды времени
                today = timezone.now().date()
                yesterday = today - datetime.timedelta(days=1)
                last_week = today - datetime.timedelta(days=7)
                last_month = today - datetime.timedelta(days=30)

                # Формируем сообщение
                message = "📊 *Сравнение локаций*\n\n"

                # Сканирования за сегодня
                message += "*Сканирования за сегодня:*\n"
                for location in locations:
                    today_count = location.scans.filter(timestamp__date=today).count()
                    message += f"{location.name}: {today_count}\n"

                # Сканирования за вчера
                message += "\n*Сканирования за вчера:*\n"
                for location in locations:
                    yesterday_count = location.scans.filter(
                        timestamp__date=yesterday
                    ).count()
                    message += f"{location.name}: {yesterday_count}\n"

                # Последние 7 дней
                message += "\n*Последние 7 дней:*\n"
                for location in locations:
                    week_count = location.scans.filter(
                        timestamp__date__gte=last_week
                    ).count()
                    message += f"{location.name}: {week_count}\n"

                # Последние 30 дней
                message += "\n*Последние 30 дней:*\n"
                for location in locations:
                    month_count = location.scans.filter(
                        timestamp__date__gte=last_month
                    ).count()
                    message += f"{location.name}: {month_count}\n"

                # Все время
                message += "\n*Все время:*\n"
                for location in locations:
                    total_count = location.scans.count()
                    message += f"{location.name}: {total_count}\n"

                # Добавляем кнопку возврата
                keyboard = [
                    [
                        InlineKeyboardButton(
                            "Вернуться к панели", callback_data="back_to_dashboard"
                        )
                    ]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)

                await query.edit_message_text(
                    message, reply_markup=reply_markup, parse_mode="Markdown"
                )

            elif callback_data == "back_to_dashboard":
                # Возвращаемся к панели
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

                await query.edit_message_text(
                    "📊 *Панель статистики QR-кодов*\n\n"
                    "Выберите опцию для просмотра статистики:",
                    reply_markup=reply_markup,
                    parse_mode="Markdown",
                )

        except Exception as e:
            logger.error(f"Error handling button callback: {str(e)}")
            logger.error(traceback.format_exc())
            log_function_call(
                "button_callback",
                user.id,
                user.username,
                error=f"Error handling callback: {str(e)}",
            )
            try:
                await query.edit_message_text(
                    f"Ошибка при обработке запроса. Пожалуйста, попробуйте позже."
                )
            except Exception as edit_err:
                logger.error(f"Failed to send error message: {str(edit_err)}")
