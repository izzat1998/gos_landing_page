"""Django management command: run Telegram bot for QR‑code statistics.

Place this file inside an application folder, e.g. `main/management/commands/run_qr_stats_bot.py`.
Run with:
    python manage.py run_qr_stats_bot
"""

from __future__ import annotations

import datetime as _dt
import logging
import traceback
from enum import Enum
from functools import wraps
from typing import Callable, Iterable

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

# ────────────────────────────────────────────────────────────────────────────────
#  Configuration
# ────────────────────────────────────────────────────────────────────────────────

ADMIN_USERNAMES: set[str] = {"Iforce706", "subanovsh"}


class Range(str, Enum):
    TODAY = "today"
    YESTERDAY = "yesterday"
    WEEK = "7d"
    MONTH = "30d"
    ALL = "all"

    @classmethod
    def to_days(cls, label: str) -> int:
        mapping = {
            cls.TODAY.value: 0,
            cls.YESTERDAY.value: 1,
            cls.WEEK.value: 7,
            cls.MONTH.value: 30,
            cls.ALL.value: 10 * 365,  # proxy for “all time”
        }
        return mapping.get(label, 30)


# ────────────────────────────────────────────────────────────────────────────────
#  Decorators
# ────────────────────────────────────────────────────────────────────────────────


def admin_only(func: Callable):  # type: ignore[override]
    """Block access to a handler for non‑admin users."""

    @wraps(func)
    async def _wrapped(
        self: "QRStatsBot", update: Update, context: ContextTypes.DEFAULT_TYPE
    ):  # noqa: D401,E501
        user = update.effective_user
        if user is None or user.username not in ADMIN_USERNAMES:
            await update.effective_message.reply_text("⛔ Недостаточно прав.")
            return
        return await func(self, update, context)

    return _wrapped


# ────────────────────────────────────────────────────────────────────────────────
#  Core bot class
# ────────────────────────────────────────────────────────────────────────────────


class QRStatsBot:
    """Encapsulated Telegram bot logic."""

    TOKEN = settings.TELEGRAM_BOT_TOKEN

    def __init__(self) -> None:
        self.app = ApplicationBuilder().token(self.TOKEN).build()
        self._register_handlers()

    # ─── Handler registration ────────────────────────────────────────────────

    def _register_handlers(self) -> None:
        self.app.add_handler(CommandHandler("start", self.cmd_start))
        self.app.add_handler(CommandHandler("help", self.cmd_help))
        self.app.add_handler(CommandHandler("stats", self.cmd_stats))
        self.app.add_handler(CommandHandler("allstats", self.cmd_allstats))
        self.app.add_handler(CommandHandler("compare", self.cmd_compare))
        self.app.add_handler(CommandHandler("dashboard", self.cmd_dashboard))
        self.app.add_handler(CallbackQueryHandler(self.cb_handler))
        self.app.add_error_handler(self.error_handler)

    # ─── Command handlers ────────────────────────────────────────────────────

    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        is_admin = user and user.username in ADMIN_USERNAMES
        msg = (
            "👋 Добро пожаловать!\n\n"
            "/stats [d] — статистика (d дней, 30 по умолчанию)\n"
            "/help — список команд"
        )
        if is_admin:
            msg += (
                "\n\n🔐 *Admin*\n"
                "/allstats [d] — по всем локациям\n"
                "/compare — сравнить локации\n"
                "/dashboard — интерактивная панель"
            )
        await update.message.reply_text(msg, parse_mode="Markdown")

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
    async def cmd_compare(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self._send_compare(update)

    @admin_only
    async def cmd_dashboard(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        kb = self._dashboard_keyboard()
        await update.message.reply_text(
            "📊 *Панель статистики* — выберите диапазон:",
            reply_markup=InlineKeyboardMarkup(kb),
            parse_mode="Markdown",
        )

    # ─── Callback queries ────────────────────────────────────────────────────

    async def cb_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        if not query or not query.data:
            return
        cmd, *arg = query.data.split(":")
        if cmd == "range":
            days = Range.to_days(arg[0])
            await self._send_stats(update, days, admin_scope=True, edit=True)
        elif cmd == "compare":
            await self._send_compare(update, edit=True)
        elif cmd == "back":
            await self.cmd_dashboard(update, context)
        await query.answer()

    # ─── Internal helpers ────────────────────────────────────────────────────

    async def _send_stats(
        self,
        update: Update,
        days: int,
        *,
        admin_scope: bool,
        edit: bool = False,
    ) -> None:
        start = timezone.now().date() - _dt.timedelta(days=days)
        total = QRCodeScan.objects.filter(timestamp__date__gte=start).count()
        lines: list[str] = [
            f"📊 *Статистика за {days} дней*",
            f"Всего сканирований: {total}",
        ]
        if admin_scope:
            for loc in Location.objects.all():
                cnt = loc.scans.filter(timestamp__date__gte=start).count()
                pct = (cnt / total * 100) if total else 0
                lines.append(f"*{loc.name}*: {cnt}  ({pct:.1f}% )")
        await self._reply(update, "\n".join(lines), edit=edit)

    async def _send_compare(self, update: Update, *, edit: bool = False):
        today = timezone.now().date()
        locs = Location.objects.all()
        sections: list[str] = ["📊 *Сравнение локаций*\n"]
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

    def _dashboard_keyboard(self) -> list[list[InlineKeyboardButton]]:
        btns = [
            ("Сегодня", Range.TODAY),
            ("Вчера", Range.YESTERDAY),
            ("7 дней", Range.WEEK),
            ("30 дней", Range.MONTH),
            ("Все время", Range.ALL),
        ]
        rows = [
            [InlineKeyboardButton(t, callback_data=f"range:{r.value}")] for t, r in btns
        ]
        rows.append(
            [InlineKeyboardButton("Сравнить локации", callback_data="compare:")]
        )
        return rows

    async def _reply(self, update: Update, text: str, *, edit: bool = False):
        if edit and update.callback_query:
            await update.callback_query.edit_message_text(text, parse_mode="Markdown")
        else:
            await update.effective_message.reply_text(text, parse_mode="Markdown")

    # ─── Global error handler ────────────────────────────────────────────────

    async def error_handler(self, update: object, context: ContextTypes.DEFAULT_TYPE):  # noqa: D401,E501
        logger.error("Exception caught:")
        logger.error(context.error)
        logger.error("\n" + traceback.format_exc())
        if isinstance(update, Update) and update.effective_message:
            await update.effective_message.reply_text(
                "Произошла ошибка. Администратор уведомлен."
            )

    # ─── Entrypoint ──────────────────────────────────────────────────────────

    def run(self) -> None:
        logger.info("QRStats bot starting…")
        self.app.run_polling()


# ────────────────────────────────────────────────────────────────────────────────
#  Django management wrapper
# ────────────────────────────────────────────────────────────────────────────────


class Command(BaseCommand):
    help = "Запускает Telegram‑бот для статистики QR‑кодов."

    def handle(self, *args, **options):  # noqa: D401
        QRStatsBot().run()
