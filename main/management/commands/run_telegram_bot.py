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
DEBUG = True

ADMIN_USERNAMES = ["Iforce706", "subanovsh"]


class Command(BaseCommand):
    help = "Запускает Telegram бота для статистики QR-кодов"

    def handle(self, *args, **kwargs):
        logging.basicConfig(
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            level=logging.INFO,
        )

        application = ApplicationBuilder().token(settings.TELEGRAM_BOT_TOKEN).build()
        application.add_handler(CommandHandler("start", self.start_command))
        application.add_handler(CommandHandler("stats", self.stats_command))
        application.add_handler(CommandHandler("help", self.help_command))
        application.add_handler(CommandHandler("admin", self.admin_command))
        application.add_handler(CommandHandler("allstats", self.all_stats_command))
        application.add_handler(CommandHandler("compare", self.compare_command))
        application.add_handler(CommandHandler("dashboard", self.dashboard_command))
        application.add_handler(CallbackQueryHandler(self.button_callback))

        self.stdout.write("Запуск Telegram бота...")
        if DEBUG:
            print("Bot started successfully")
        logger.info("Telegram bot polling started")
        application.run_polling()

    def is_admin(self, username):
        is_admin = username in ADMIN_USERNAMES
        if DEBUG:
            print(f"Checking admin for {username}: {is_admin}")
        return is_admin

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        if DEBUG:
            print(f"Received /start from {user.username}")
        is_admin = self.is_admin(user.username)

        welcome_message = (
            f"👋 Добро пожаловать, {user.first_name}!\n\n"
            "Используйте /stats для статистики\n"
            "Используйте /help для списка команд"
        )

        if is_admin:
            welcome_message += "\n\n🔐 *Команды администратора*\n/admin\n/allstats\n/compare\n/dashboard"

        await update.message.reply_text(welcome_message, parse_mode="Markdown")

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        if DEBUG:
            print(f"Received /help from {user.username}")
        is_admin = self.is_admin(user.username)

        help_message = (
            "/stats - Статистика\n/stats 7 - За последние 7 дней\n/help - Помощь"
        )

        if is_admin:
            help_message += "\n\n🔐 *Команды администратора*\n/admin\n/allstats\n/compare\n/dashboard"

        await update.message.reply_text(help_message, parse_mode="Markdown")

    async def admin_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        if DEBUG:
            print(f"Received /admin from {user.username}")
        if not self.is_admin(user.username):
            await update.message.reply_text("⛔ Нет доступа к админ-командам")
            return

        await update.message.reply_text(
            "🔐 *Команды администратора*\n/allstats\n/compare\n/dashboard",
            parse_mode="Markdown",
        )

    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        if DEBUG:
            print(f"Received /stats from {user.username}")

        days = 30
        if context.args and context.args[0].isdigit():
            days = int(context.args[0])

        api_url = f"{settings.SITE_URL}/api/location-stats/?days={days}"
        headers = {"Authorization": f"Token {settings.API_TOKEN}"}

        if DEBUG:
            print(f"Calling API: {api_url}")
            print(f"Headers: {headers}")

        try:
            response = requests.get(api_url, headers=headers, timeout=10)

            if response.status_code != 200:
                if DEBUG:
                    print(f"API Error {response.status_code}: {response.text}")
                await update.message.reply_text("Ошибка API. Проверьте настройки.")
                return

            data = response.json()
            if DEBUG:
                print("Data received:", data)

            if not data:
                await update.message.reply_text("Нет данных по сканированиям")
                return

            message = f"📊 Статистика за последние {days} дней\n\n"
            for loc in data:
                message += f"*{loc['name']}*\nВсего: {loc['total_scans']}\nНедавние: {loc['recent_scans']}\n\n"

            await update.message.reply_text(message, parse_mode="Markdown")

        except requests.exceptions.RequestException as e:
            logger.error(f"API call failed: {str(e)}")
            if DEBUG:
                print(f"API Exception: {str(e)}")
            await update.message.reply_text("Ошибка запроса к серверу")

    async def all_stats_command(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        user = update.effective_user
        if DEBUG:
            print(f"Received /allstats from {user.username}")
        if not self.is_admin(user.username):
            await update.message.reply_text("⛔ Нет доступа")
            return

        days = 30
        if context.args and context.args[0].isdigit():
            days = int(context.args[0])

        today = timezone.now().date()
        start_date = today - datetime.timedelta(days=days)
        locations = Location.objects.all()

        total_scans = QRCodeScan.objects.count()
        recent_scans = QRCodeScan.objects.filter(
            timestamp__date__gte=start_date
        ).count()

        if DEBUG:
            print(f"Total scans: {total_scans}, Recent scans: {recent_scans}")

        message = f"📊 Все локации (за {days} дней)\n\nВсего: {total_scans}\nНедавние: {recent_scans}\n\n"
        for loc in locations:
            total = loc.scans.count()
            recent = loc.scans.filter(timestamp__date__gte=start_date).count()
            percent = (total / total_scans * 100) if total_scans else 0
            message += f"*{loc.name}*\nВсего: {total}\nНедавние: {recent}\n{percent:.1f}% от общего\n\n"

        await update.message.reply_text(message, parse_mode="Markdown")

    async def compare_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        if DEBUG:
            print(f"Received /compare from {user.username}")
        if not self.is_admin(user.username):
            await update.message.reply_text("⛔ Нет доступа")
            return

        today = timezone.now().date()
        locations = Location.objects.all()

        message = "📊 Сравнение локаций\n\n"
        for label, delta in [
            ("Сегодня", 0),
            ("Вчера", 1),
            ("7 дней", 7),
            ("30 дней", 30),
        ]:
            message += f"*{label}:*\n"
            day = today - datetime.timedelta(days=delta)
            for loc in locations:
                count = loc.scans.filter(timestamp__date__gte=day).count()
                message += f"{loc.name}: {count}\n"
            message += "\n"

        await update.message.reply_text(message, parse_mode="Markdown")

    async def dashboard_command(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        user = update.effective_user
        if DEBUG:
            print(f"Received /dashboard from {user.username}")
        if not self.is_admin(user.username):
            await update.message.reply_text("⛔ Нет доступа")
            return

        keyboard = [
            [
                InlineKeyboardButton("Сегодня", callback_data="stats_today"),
                InlineKeyboardButton("Вчера", callback_data="stats_yesterday"),
            ],
            [
                InlineKeyboardButton("7 дней", callback_data="stats_7days"),
                InlineKeyboardButton("30 дней", callback_data="stats_30days"),
            ],
            [
                InlineKeyboardButton("Все время", callback_data="stats_alltime"),
                InlineKeyboardButton("Сравнение", callback_data="compare_locations"),
            ],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "📊 Панель статистики QR-кодов\nВыберите опцию:",
            reply_markup=reply_markup,
            parse_mode="Markdown",
        )

    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        user = update.effective_user
        if DEBUG:
            print(f"Button pressed: {query.data} by {user.username}")
        # The rest of this method would mirror the logic of `compare_command` and others
