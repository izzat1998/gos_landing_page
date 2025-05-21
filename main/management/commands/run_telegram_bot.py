"""TeleGram QR statistics bot — refactored & condensed version.

Key changes
-----------
* Single `QRStatsBot` class encapsulating configuration, handlers and helpers.
* DRY helpers for date‑range calculation, message formatting and keyboard creation.
* Callback queries use a structured payload (`<action>:<arg>`), reducing `if/elif` blocks.
* Centralised admin‑check decorator.
* Extensive type hints + docstrings.
"""

from __future__ import annotations

import datetime as _dt
import logging
import traceback
from enum import Enum
from functools import wraps
from typing import Callable, List, Optional

import requests

# Import models directly
from asgiref.sync import sync_to_async
from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
)

from main.models import Location, QRCodeScan, PhoneClick  # pylint: disable=import-error
from users.models import CustomUser  # <-- Import user model

logger = logging.getLogger(__name__)

ADMIN_USERNAMES: set[str] = {"Iforce706", "subanovsh", "umurzakova8686"}


class Range(str, Enum):
    TODAY = "today"
    YESTERDAY = "yesterday"
    WEEK = "7d"
    MONTH = "30d"
    ALL = "all"

    @classmethod
    def list(cls) -> list[str]:
        return [m.value for m in cls]  # type: ignore[arg-type]


# ────────────────────────────────────────────────────────────────────────────────
#  Utilities
# ────────────────────────────────────────────────────────────────────────────────


def admin_only(func: Callable):  # type: ignore[override]
    """Decorator blocking non‑admin users."""

    @wraps(func)
    async def _wrapper(
        self: "QRStatsBot", update: Update, context: ContextTypes.DEFAULT_TYPE
    ):  # noqa: D401,E501
        user = update.effective_user
        if user is None or user.username not in ADMIN_USERNAMES:
            await update.effective_message.reply_text("⛔ Недостаточно прав.")
            return
        return await func(self, update, context)

    return _wrapper


# ────────────────────────────────────────────────────────────────────────────────
#  Core bot
# ────────────────────────────────────────────────────────────────────────────────


class QRStatsBot:
    """Encapsulated bot instance."""

    def __init__(self) -> None:
        self.site_url = settings.SITE_URL.rstrip("/")
        self.api_token = settings.API_TOKEN
        self.app = ApplicationBuilder().token(settings.TELEGRAM_BOT_TOKEN).build()
        self._register_handlers()

    # ─── Handlers registration ────────────────────────────────────────────────

    def _register_handlers(self) -> None:
        self.app.add_handler(CommandHandler("start", self.cmd_start))
        self.app.add_handler(CommandHandler("help", self.cmd_help))
        self.app.add_handler(CommandHandler("stats", self.cmd_stats))
        self.app.add_handler(CommandHandler("allstats", self.cmd_allstats))

        from telegram.ext import MessageHandler, filters

        self.app.add_handler(MessageHandler(filters.CONTACT, self.contact_handler))

        # callback queries
        self.app.add_handler(CallbackQueryHandler(self.cb_handler))
        # global error handler
        self.app.add_error_handler(self.error_handler)

    # ─── Commands ─────────────────────────────────────────────────────────────

    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        telegram_id = str(user.id)
        # Check registration by telegram_id
        db_user = await sync_to_async(
            lambda: CustomUser.objects.filter(telegram_id=telegram_id).first()
        )()
        if db_user:
            # Registered: show confirmation and available locations
            await update.message.reply_text(
                "✅ Вы зарегистрированы!\n\nИспользуйте команду /stats для просмотра статистики по вашим локациям.",
                parse_mode="Markdown",
            )
            # Show user's locations
            locations = await sync_to_async(
                lambda: list(Location.objects.filter(user=db_user))
            )()
            if locations:
                loc_list = "\n".join(f"- {loc.name}" for loc in locations)
                await update.message.reply_text(f"Ваши локации:\n{loc_list}")
            else:
                await update.message.reply_text("У вас пока нет связанных локаций.")
        else:
            # Not registered: ask for phone number
            from telegram import KeyboardButton, ReplyKeyboardMarkup

            kb = [
                [KeyboardButton(text="Отправить номер телефона", request_contact=True)]
            ]
            await update.message.reply_text(
                "Пожалуйста, отправьте свой номер телефона для регистрации:",
                reply_markup=ReplyKeyboardMarkup(
                    kb, one_time_keyboard=True, resize_keyboard=True
                ),
            )

    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self.cmd_start(update, context)

    async def cmd_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        telegram_id = str(user.id)
        db_user = await sync_to_async(
            lambda: CustomUser.objects.filter(telegram_id=telegram_id).first()
        )()
        if not db_user:
            await update.message.reply_text(
                "⛔ Сначала зарегистрируйтесь через /start."
            )
            return
        days = (
            int(context.args[0]) if context.args and context.args[0].isdigit() else 30
        )
        # Only show stats for this user's locations
        await self._send_stats(update, days, admin_scope=False)

    @admin_only
    async def cmd_allstats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        days = (
            int(context.args[0]) if context.args and context.args[0].isdigit() else 30
        )
        await self._send_stats(update, days, admin_scope=True)

    @admin_only
    async def cmd_dashboard(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        kb = self._build_dashboard_kb()
        await update.message.reply_text(
            "📊 *Панель статистики* — выберите диапазон:",
            reply_markup=InlineKeyboardMarkup(kb),
            parse_mode="Markdown",
        )

    # ─── Contact registration handler ─────────────────────────────────────────

    async def contact_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        contact = update.effective_message.contact
        telegram_user = update.effective_user
        if not contact or not contact.phone_number:
            await update.message.reply_text(
                "Не удалось получить номер телефона. Попробуйте ещё раз."
            )
            return
        # Normalize phone number (remove spaces, +, etc.)
        phone = contact.phone_number.replace(" ", "").replace("+", "")
        db_user = await sync_to_async(
            lambda: CustomUser.objects.filter(phone_number__endswith=phone[-9:]).first()
        )()
        if db_user:
            # Update telegram_id
            db_user.telegram_id = str(telegram_user.id)
            await sync_to_async(db_user.save)()
            await update.message.reply_text(
                "✅ Вы успешно зарегистрированы! Теперь вы можете использовать /stats."
            )
            # Show user's locations
            locations = await sync_to_async(
                lambda: list(Location.objects.filter(user=db_user))
            )()
            if locations:
                loc_list = "\n".join(f"- {loc.name}" for loc in locations)
                await update.message.reply_text(f"Ваши локации:\n{loc_list}")
            else:
                await update.message.reply_text("У вас пока нет связанных локаций.")
        else:
            await update.message.reply_text(
                "⛔ Ваш номер не найден в базе. Обратитесь к администратору."
            )

    # ─── Callback queries ─────────────────────────────────────────────────────

    async def cb_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        if not query or not query.data:
            return
        action, *arg = query.data.split(":")
        if action == "range":
            await self._send_stats(
                update, self._range_to_days(arg[0]), admin_scope=True, edit=True
            )
        elif action == "back":
            await self.cmd_dashboard(update, context)
        await query.answer()

    # ─── Shared helpers ───────────────────────────────────────────────────────

    # Database helper functions that will be wrapped with sync_to_async
    def _get_locations(self) -> List[Location]:
        """Get all locations from database."""
        try:
            return list(Location.objects.all())
        except Exception as e:
            logger.error(f"Error in _get_locations: {str(e)}")
            return []

    def _count_scans(self, start_date=None) -> int:
        """Count all scans, optionally filtered by date."""
        try:
            qs = QRCodeScan.objects
            if start_date:
                qs = qs.filter(timestamp__date__gte=start_date)
            return qs.count()
        except Exception as e:
            logger.error(f"Error in _count_scans: {str(e)}")
            return 0

    def _count_location_scans(self, location_id: int, start_date=None) -> int:
        """Count scans for a specific location."""
        try:
            qs = QRCodeScan.objects.filter(location_id=location_id)
            if start_date:
                qs = qs.filter(timestamp__date__gte=start_date)
            return qs.count()
        except Exception as e:
            logger.error(f"Error in _count_location_scans: {str(e)}")
            return 0

    def _count_scans_for_date(self, date) -> int:
        """Count scans for a specific date."""
        try:
            return QRCodeScan.objects.filter(timestamp__date=date).count()
        except Exception as e:
            logger.error(f"Error in _count_scans_for_date: {str(e)}")
            return 0

    def _count_location_scans_for_date(self, location_id: int, date) -> int:
        """Count scans for a specific location on a specific date."""
        try:
            return QRCodeScan.objects.filter(
                location_id=location_id, timestamp__date=date
            ).count()
        except Exception as e:
            logger.error(f"Error in _count_location_scans_for_date: {str(e)}")
            return 0

    def _count_location_phone_clicks(self, location_id: int, start_date=None) -> int:
        """Count phone clicks for a specific location."""
        try:
            qs = PhoneClick.objects.filter(scan__location_id=location_id)
            if start_date:
                qs = qs.filter(scan__timestamp__date__gte=start_date)
            return qs.count()
        except Exception as e:
            logger.error(f"Error in _count_location_phone_clicks: {str(e)}")
            return 0

    async def _send_stats(
        self, update: Update, days: int, *, admin_scope: bool, edit: bool = False
    ):
        try:
            user = update.effective_user
            today = timezone.now().date()
            start = today - _dt.timedelta(days=days)
            date_range = f"{start.strftime('%d.%m.%Y')} — {today.strftime('%d.%m.%Y')}"

            get_locations = sync_to_async(self._get_locations)
            count_scans = sync_to_async(self._count_scans)
            count_location_scans = sync_to_async(self._count_location_scans)
            count_location_phone_clicks = sync_to_async(self._count_location_phone_clicks)

            total_phone_clicks_overall = 0

            if admin_scope:
                total_scans = await count_scans(start)
                locations = await get_locations()
                # Simpler way for admin scope overall total phone clicks
                total_phone_clicks_overall = await sync_to_async(
                    lambda: PhoneClick.objects.filter(scan__timestamp__date__gte=start).count()
                    if start_date # In this context, start_date is 'start'
                    else PhoneClick.objects.count()
                )()
            else:
                # Fetch user's location based on telegram_id
                telegram_id = str(user.id)
                db_user = await sync_to_async(
                    lambda: CustomUser.objects.filter(telegram_id=telegram_id).first()
                )()
                if not db_user:
                    await update.effective_message.reply_text(
                        "⛔ Сначала зарегистрируйтесь через /start."
                    )
                    return

                user_locations = await sync_to_async(
                    lambda: list(Location.objects.filter(user=db_user))
                )()
                if not user_locations:
                    await update.effective_message.reply_text(
                        "⛔ У вас нет доступной локации."
                    )
                    return
                locations = user_locations
                total_scans = 0
                for loc in locations:
                    total_scans += await count_location_scans(loc.id, start)
                    total_phone_clicks_overall += await count_location_phone_clicks(loc.id, start)


            # Header
            if days == 0:
                period_text = "сегодня"
            elif days == 1:
                period_text = "за вчера"
            elif days == 7:
                period_text = "за неделю"
            elif days == 30:
                period_text = "за месяц"
            else:
                period_text = f"за {days} дней"

            parts = [
                f"📊 *СТАТИСТИКА {period_text.upper()}*",
                f"Период: {date_range}",
                f"━━━━━━━━━━━━━━━━━━━━━",
                f"📈 *Общее количество сканирований: {total_scans}*",
                f"📱 *Общее количество кликов на телефон: {total_phone_clicks_overall}*",
            ]

            if total_scans > 0 or total_phone_clicks_overall > 0: # Show stats if there's any activity
                parts.append("\n🗺️ *СТАТИСТИКА ПО ЛОКАЦИЯМ:*")
                loc_stats = []
                for loc in locations:
                    loc_scans = await count_location_scans(loc.id, start)
                    loc_phone_clicks = await count_location_phone_clicks(loc.id, start)
                    share = (loc_scans / total_scans * 100) if total_scans > 0 else 0
                    loc_stats.append((loc.name, loc_scans, loc_phone_clicks, share))

                # Sort by total scans primarily, then by phone clicks
                loc_stats.sort(key=lambda x: (x[1], x[2]), reverse=True)

                for i, (name, scans, phone_clicks, share) in enumerate(loc_stats, 1):
                    bar = "■" * max(1, round(share / 10)) if total_scans > 0 else "" # Ensure bar is not generated if no scans
                    parts.append(f"{i}. *{name}*: 📞 {phone_clicks} / 📷 {scans} ({share:.1f}%)\n   {bar if bar else ''}")

            msg = "\n".join(parts)
            await self._reply(update, msg, edit=edit)

        except Exception as e:
            logger.error(f"Error in _send_stats: {str(e)}")
            logger.error(traceback.format_exc())
            await update.effective_message.reply_text(
                "Ошибка при получении статистики. Пожалуйста, попробуйте позже."
            )

    @staticmethod
    def _range_to_days(r: str) -> int:
        mapping = {
            Range.TODAY.value: 0,
            Range.YESTERDAY.value: 1,
            Range.WEEK.value: 7,
            Range.MONTH.value: 30,
            Range.ALL.value: 3650,  # ~10 years as proxy for "all time"
        }
        return mapping.get(r, 30)

    def _build_dashboard_kb(self) -> list[list[InlineKeyboardButton]]:
        buttons = [
            ("Сегодня", Range.TODAY),
            ("Вчера", Range.YESTERDAY),
            ("7 дней", Range.WEEK),
            ("30 дней", Range.MONTH),
            ("Все время", Range.ALL),
        ]
        rows: list[list[InlineKeyboardButton]] = []
        for text, rng in buttons:
            rows.append(
                [InlineKeyboardButton(text, callback_data=f"range:{rng.value}")]
            )
        rows.append(
            [InlineKeyboardButton("Сравнить локации", callback_data="compare:")]
        )
        return rows

    async def _reply(self, update: Update, text: str, *, edit: bool = False):
        if edit and update.callback_query:
            await update.callback_query.edit_message_text(text, parse_mode="Markdown")
        else:
            await update.effective_message.reply_text(text, parse_mode="Markdown")

    # ─── Error handler ────────────────────────────────────────────────────────

    async def error_handler(self, update: object, context: ContextTypes.DEFAULT_TYPE):  # noqa: D401,E501
        logger.error("Exception while handling an update:")
        logger.error(context.error)
        logger.error("\n" + traceback.format_exc())
        if isinstance(update, Update) and update.effective_message:
            await update.effective_message.reply_text(
                "Произошла ошибка. Администратор уведомлен."
            )

    # ─── Entrypoint ───────────────────────────────────────────────────────────

    def run(self) -> None:
        logger.info("Bot starting…")
        self.app.run_polling()


class Command(BaseCommand):
    help = "Run the Telegram QR statistics bot"

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Starting Telegram bot..."))
        bot = QRStatsBot()
        bot.run()


if __name__ == "__main__":
    QRStatsBot().run()
