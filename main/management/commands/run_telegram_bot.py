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

from main.models import Location, QRCodeScan  # pylint: disable=import-error

logger = logging.getLogger(__name__)

ADMIN_USERNAMES: set[str] = {"Iforce706", "subanovsh"}


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

        # callback queries
        self.app.add_handler(CallbackQueryHandler(self.cb_handler))
        # global error handler
        self.app.add_error_handler(self.error_handler)

    # ─── Commands ─────────────────────────────────────────────────────────────

    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        is_admin = user and user.username in ADMIN_USERNAMES
        text = (
            "👋 Добро пожаловать!\n\n"
            "/stats [d] — статистика по вашей локации (d дней, 30 по умол.)\n"
            "/help — доступные команды"
        )
        if is_admin:
            text += (
                "\n\n🔐 *Admin*\n"
                "/allstats [d] — статистика по всем локациям\n"
                "/compare — сравнить локации"
            )
        await update.message.reply_text(text, parse_mode="Markdown")

    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self.cmd_start(update, context)

    async def cmd_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        days = (
            int(context.args[0]) if context.args and context.args[0].isdigit() else 30
        )
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

    async def _send_stats(
        self,
        update: Update,
        days: int,
        *,
        admin_scope: bool,
        edit: bool = False,
    ) -> None:
        """Fetches statistics and sends/edits message."""
        try:
            # Calculate date range
            today = timezone.now().date()
            start = today - _dt.timedelta(days=days)
            date_range = f"{start.strftime('%d.%m.%Y')} — {today.strftime('%d.%m.%Y')}"

            # Get data using sync_to_async
            get_locations = sync_to_async(self._get_locations)
            count_scans = sync_to_async(self._count_scans)
            count_location_scans = sync_to_async(self._count_location_scans)

            # Fetch data asynchronously
            total_scans = await count_scans(start)

            # Start building the message with a clear header
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
            ]

            # Add location stats if admin
            if admin_scope and total_scans > 0:
                locations = await get_locations()

                # Add a section header for locations
                parts.append("\n🗺️ *СТАТИСТИКА ПО ЛОКАЦИЯМ:*")

                # Sort locations by scan count (descending)
                loc_stats = []
                for loc in locations:
                    loc_scans = await count_location_scans(loc.id, start)
                    share = (loc_scans / total_scans * 100) if total_scans > 0 else 0
                    loc_stats.append((loc.name, loc_scans, share))

                # Sort by scan count (descending)
                loc_stats.sort(key=lambda x: x[1], reverse=True)

                # Add each location with a visual indicator of its share
                for i, (name, scans, share) in enumerate(loc_stats, 1):
                    # Create a visual bar based on percentage (each ■ = ~10%)
                    bar_count = max(1, round(share / 10))
                    bar = "■" * bar_count

                    # Format with ranking number
                    parts.append(f"{i}. *{name}*: {scans} ({share:.1f}%)\n   {bar}")

            # Join all parts and send
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
