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
from typing import Callable, Iterable, Optional

import requests
from django.conf import settings
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
    async def _wrapper(self: "QRStatsBot", update: Update, context: ContextTypes.DEFAULT_TYPE):  # noqa: D401,E501
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
        self.app.add_handler(CommandHandler("compare", self.cmd_compare))
        self.app.add_handler(CommandHandler("dashboard", self.cmd_dashboard))
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
                "/compare — сравнить локации\n"
                "/dashboard — интерактивная панель"
            )
        await update.message.reply_text(text, parse_mode="Markdown")

    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self.cmd_start(update, context)

    async def cmd_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        days = int(context.args[0]) if context.args and context.args[0].isdigit() else 30
        await self._send_stats(update, days, admin_scope=False)

    @admin_only
    async def cmd_allstats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        days = int(context.args[0]) if context.args and context.args[0].isdigit() else 30
        await self._send_stats(update, days, admin_scope=True)

    @admin_only
    async def cmd_compare(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self._send_compare(update)

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
            await self._send_stats(update, self._range_to_days(arg[0]), admin_scope=True, edit=True)
        elif action == "compare":
            await self._send_compare(update, edit=True)
        elif action == "back":
            await self.cmd_dashboard(update, context)
        await query.answer()

    # ─── Shared helpers ───────────────────────────────────────────────────────

    async def _send_stats(
        self,
        update: Update,
        days: int,
        *,
        admin_scope: bool,
        edit: bool = False,
    ) -> None:
        """Fetches statistics and sends/edits message."""
        # API call fallback example; here we read DB directly.
        start = timezone.now().date() - _dt.timedelta(days=days)
        locations: Iterable[Location] = Location.objects.all() if admin_scope else []

        total_scans = QRCodeScan.objects.filter(timestamp__date__gte=start).count()
        parts: list[str] = [
            f"📊 *Статистика за {days} дней*\n",
            f"Всего сканирований: {total_scans}\n",
        ]
        if admin_scope:
            for loc in locations:
                cnt = loc.scans.filter(timestamp__date__gte=start).count()
                share = (cnt / total_scans * 100) if total_scans else 0
                parts.append(f"*{loc.name}*: {cnt} ( {share:.1f}% )")
        msg = "\n".join(parts)
        await self._reply(update, msg, edit=edit)

    async def _send_compare(self, update: Update, *, edit: bool = False):
        today = timezone.now().date()
        locs = Location.objects.all()
        sections = ["📊 *Сравнение локаций*\n"]
        for label, delta in (
            ("Сегодня", 0),
            ("Вчера", 1),
            ("7 дней", 7),
            ("30 дней", 30),
        ):
            start = today - _dt.timedelta(days=delta)
            sections.append(f"*{label}*:")
            for loc in locs:
                cnt = (
                    loc.scans.filter(timestamp__date=today).count()
                    if delta == 0
                    else loc.scans.filter(timestamp__date__gte=start).count()
                )
                sections.append(f"{loc.name}: {cnt}")
            sections.append("")
        await self._reply(update, "\n".join(sections), edit=edit)

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
            rows.append([InlineKeyboardButton(text, callback_data=f"range:{rng.value}")])
        rows.append([InlineKeyboardButton("Сравнить локации", callback_data="compare:")])
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
                "Произошла ошибка. Администратор уведомлен.")

    # ─── Entrypoint ───────────────────────────────────────────────────────────

    def run(self) -> None:
        logger.info("Bot starting…")
        self.app.run_polling()


if __name__ == "__main__":
    QRStatsBot().run()
