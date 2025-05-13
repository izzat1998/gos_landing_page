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
        # Получаем параметр дней, если он указан (по умолчанию: 30)
        days = 30
        if context.args and context.args[0].isdigit():
            days = int(context.args[0])

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
            response = requests.get(api_url, headers=headers, timeout=10)

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
            await update.message.reply_text(
                "Ошибка подключения к API. Убедитесь, что сервер Django запущен и доступен."
            )
        except requests.exceptions.Timeout as e:
            logger.error(f"Timeout error: {str(e)}")
            await update.message.reply_text(
                "Превышено время ожидания ответа от API. Сервер может быть перегружен."
            )
        except Exception as e:
            logger.error(f"Error fetching statistics: {str(e)}")
            await update.message.reply_text(
                f"Ошибка при получении статистики: {str(e)}. Пожалуйста, попробуйте позже."
            )

    async def all_stats_command(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Получает и отображает статистику по всем локациям (только для администраторов)"""
        user = update.effective_user

        if not self.is_admin(user.username):
            await update.message.reply_text(
                "⛔ У вас нет разрешения на использование этой команды."
            )
            return

        # Получаем параметр дней, если он указан (по умолчанию: 30)
        days = 30
        if context.args and context.args[0].isdigit():
            days = int(context.args[0])

        # Рассчитываем диапазоны дат
        today = timezone.now().date()
        start_date = today - datetime.timedelta(days=days)

        try:
            # Получаем все локации
            locations = Location.objects.all()

            if not locations.exists():
                await update.message.reply_text("В базе данных не найдено локаций.")
                return

            # Рассчитываем общее количество сканирований по всем локациям
            total_scans = QRCodeScan.objects.count()
            recent_scans = QRCodeScan.objects.filter(
                timestamp__date__gte=start_date
            ).count()

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

                message += f"*{location.name}*\n"
                message += f"Всего сканирований: {location_total}\n"
                message += f"Недавние сканирования ({days} дней): {location_recent}\n"

                # Рассчитываем процент от общего числа сканирований
                if total_scans > 0:
                    percentage = (location_total / total_scans) * 100
                    message += f"Процент от общего числа: {percentage:.1f}%\n"

                message += "\n"

            await update.message.reply_text(message, parse_mode="Markdown")
        except Exception as e:
            logger.error(f"Error fetching all statistics: {str(e)}")
            await update.message.reply_text(
                f"Ошибка при получении статистики. Пожалуйста, попробуйте позже."
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
        query = update.callback_query
        await query.answer()

        user = update.effective_user
        if not self.is_admin(user.username):
            await query.edit_message_text(
                "⛔ У вас нет разрешения на использование этой функции."
            )
            return

        callback_data = query.data

        try:
            if callback_data == "stats_today":
                # Получаем статистику за сегодня
                today = timezone.now().date()
                locations = Location.objects.all()

                message = "\ud83d\udcca *Статистика за сегодня*\n\n"
                total_today = QRCodeScan.objects.filter(timestamp__date=today).count()
                message += f"*Всего сканирований сегодня: {total_today}*\n\n"

                for location in locations:
                    today_count = location.scans.filter(timestamp__date=today).count()
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

                await query.edit_message_text(
                    message, reply_markup=reply_markup, parse_mode="Markdown"
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
            await query.edit_message_text(
                f"Ошибка при обработке запроса. Пожалуйста, попробуйте позже."
            )
