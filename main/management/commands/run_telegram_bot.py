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

# List of admin usernames who can access admin commands
ADMIN_USERNAMES = ["admin", "superuser"]  # Add your admin Telegram usernames here


class Command(BaseCommand):
    help = "Runs the Telegram bot for QR code statistics"

    def handle(self, *args, **kwargs):
        # Set up logging
        logging.basicConfig(
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            level=logging.INFO,
        )

        # Create the application
        application = ApplicationBuilder().token(settings.TELEGRAM_BOT_TOKEN).build()

        # Add command handlers
        application.add_handler(CommandHandler("start", self.start_command))
        application.add_handler(CommandHandler("stats", self.stats_command))
        application.add_handler(CommandHandler("help", self.help_command))
        application.add_handler(CommandHandler("admin", self.admin_command))
        application.add_handler(CommandHandler("allstats", self.all_stats_command))
        application.add_handler(CommandHandler("compare", self.compare_command))
        application.add_handler(CommandHandler("dashboard", self.dashboard_command))

        # Add callback query handler for inline buttons
        application.add_handler(CallbackQueryHandler(self.button_callback))

        self.stdout.write("Starting Telegram bot...")
        application.run_polling()

    def is_admin(self, username):
        """Check if the username is in the admin list"""
        return username in ADMIN_USERNAMES

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Send a welcome message when the command /start is issued."""
        user = update.effective_user
        is_admin = self.is_admin(user.username)

        welcome_message = (
            f"👋 Welcome to the GOS Furniture QR Code Statistics Bot, {user.first_name}!\n\n"
            "Use /stats to see QR code scan statistics\n"
            "Use /help to see available commands"
        )

        if is_admin:
            welcome_message += "\n\n🔐 *Admin Commands*\n"
            welcome_message += "/admin - Show admin commands\n"
            welcome_message += "/allstats - View statistics for all locations\n"
            welcome_message += "/compare - Compare statistics between locations\n"
            welcome_message += "/dashboard - View interactive dashboard"

        await update.message.reply_text(welcome_message, parse_mode="Markdown")

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Send a help message when the command /help is issued."""
        user = update.effective_user
        is_admin = self.is_admin(user.username)

        help_message = (
            "Available commands:\n\n"
            "/stats - View QR code scan statistics\n"
            "/stats 7 - View statistics for the last 7 days\n"
            "/help - Show this help message"
        )

        if is_admin:
            help_message += "\n\n🔐 *Admin Commands*\n"
            help_message += "/admin - Show admin commands\n"
            help_message += "/allstats - View statistics for all locations\n"
            help_message += "/allstats 7 - View all stats for last 7 days\n"
            help_message += "/compare - Compare statistics between locations\n"
            help_message += "/dashboard - View interactive dashboard"

        await update.message.reply_text(help_message, parse_mode="Markdown")

    async def admin_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show admin commands"""
        user = update.effective_user

        if not self.is_admin(user.username):
            await update.message.reply_text(
                "⛔ You don't have permission to use admin commands."
            )
            return

        admin_message = (
            "🔐 *Admin Commands*\n\n"
            "/allstats - View statistics for all locations\n"
            "/allstats 7 - View all stats for last 7 days\n"
            "/compare - Compare statistics between locations\n"
            "/dashboard - View interactive dashboard with buttons"
        )

        await update.message.reply_text(admin_message, parse_mode="Markdown")

    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Get and display QR code statistics."""
        # Get days parameter if provided (default: 30)
        days = 30
        if context.args and context.args[0].isdigit():
            days = int(context.args[0])

        # Get stats from API
        api_url = f"{settings.SITE_URL}/api/location-stats/?days={days}"
        headers = {"Authorization": f"Token {settings.API_TOKEN}"}

        try:
            response = requests.get(api_url, headers=headers)
            data = response.json()

            if not data:
                await update.message.reply_text("No QR code scan data available yet.")
                return

            # Format message
            message = "📊 QR Code Statistics (Last {} days)\n\n".format(days)

            for location in data:
                message += f"*{location['name']}*\n"
                message += f"Total scans: {location['total_scans']}\n"
                message += f"Recent scans ({days} days): {location['recent_scans']}\n\n"

            await update.message.reply_text(message, parse_mode="Markdown")
        except Exception as e:
            logger.error(f"Error fetching statistics: {str(e)}")
            await update.message.reply_text(
                f"Error fetching statistics. Please try again later."
            )

    async def all_stats_command(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Get and display statistics for all locations (admin only)"""
        user = update.effective_user

        if not self.is_admin(user.username):
            await update.message.reply_text(
                "⛔ You don't have permission to use this command."
            )
            return

        # Get days parameter if provided (default: 30)
        days = 30
        if context.args and context.args[0].isdigit():
            days = int(context.args[0])

        # Calculate date ranges
        today = timezone.now().date()
        start_date = today - datetime.timedelta(days=days)

        try:
            # Get all locations
            locations = Location.objects.all()

            if not locations.exists():
                await update.message.reply_text("No locations found in the database.")
                return

            # Calculate total scans across all locations
            total_scans = QRCodeScan.objects.count()
            recent_scans = QRCodeScan.objects.filter(
                timestamp__date__gte=start_date
            ).count()

            # Format message
            message = f"📊 *QR Code Statistics - All Locations (Last {days} days)*\n\n"
            message += f"*Total Scans Across All Locations: {total_scans}*\n"
            message += f"*Recent Scans (Last {days} days): {recent_scans}*\n\n"
            message += "*Breakdown by Location:*\n\n"

            # Add stats for each location
            for location in locations:
                location_total = location.scans.count()
                location_recent = location.scans.filter(
                    timestamp__date__gte=start_date
                ).count()

                message += f"*{location.name}*\n"
                message += f"Total scans: {location_total}\n"
                message += f"Recent scans ({days} days): {location_recent}\n"

                # Calculate percentage of total scans
                if total_scans > 0:
                    percentage = (location_total / total_scans) * 100
                    message += f"Percentage of total: {percentage:.1f}%\n"

                message += "\n"

            await update.message.reply_text(message, parse_mode="Markdown")
        except Exception as e:
            logger.error(f"Error fetching all statistics: {str(e)}")
            await update.message.reply_text(
                f"Error fetching statistics. Please try again later."
            )

    async def compare_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Compare statistics between locations (admin only)"""
        user = update.effective_user

        if not self.is_admin(user.username):
            await update.message.reply_text(
                "⛔ You don't have permission to use this command."
            )
            return

        try:
            # Get all locations
            locations = Location.objects.all()

            if not locations.exists() or locations.count() < 2:
                await update.message.reply_text(
                    "Need at least two locations to compare."
                )
                return

            # Calculate time periods
            today = timezone.now().date()
            yesterday = today - datetime.timedelta(days=1)
            last_week = today - datetime.timedelta(days=7)
            last_month = today - datetime.timedelta(days=30)

            # Format message
            message = "📊 *Location Comparison*\n\n"

            # Today's scans
            message += "*Today's Scans:*\n"
            for location in locations:
                today_count = location.scans.filter(timestamp__date=today).count()
                message += f"{location.name}: {today_count}\n"

            # Yesterday's scans
            message += "\n*Yesterday's Scans:*\n"
            for location in locations:
                yesterday_count = location.scans.filter(
                    timestamp__date=yesterday
                ).count()
                message += f"{location.name}: {yesterday_count}\n"

            # Last 7 days
            message += "\n*Last 7 Days:*\n"
            for location in locations:
                week_count = location.scans.filter(
                    timestamp__date__gte=last_week
                ).count()
                message += f"{location.name}: {week_count}\n"

            # Last 30 days
            message += "\n*Last 30 Days:*\n"
            for location in locations:
                month_count = location.scans.filter(
                    timestamp__date__gte=last_month
                ).count()
                message += f"{location.name}: {month_count}\n"

            # All time
            message += "\n*All Time:*\n"
            for location in locations:
                total_count = location.scans.count()
                message += f"{location.name}: {total_count}\n"

            await update.message.reply_text(message, parse_mode="Markdown")
        except Exception as e:
            logger.error(f"Error comparing locations: {str(e)}")
            await update.message.reply_text(
                f"Error comparing locations. Please try again later."
            )

    async def dashboard_command(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        """Display an interactive dashboard with buttons (admin only)"""
        user = update.effective_user

        if not self.is_admin(user.username):
            await update.message.reply_text(
                "⛔ You don't have permission to use this command."
            )
            return

        try:
            # Create inline keyboard with options
            keyboard = [
                [
                    InlineKeyboardButton("Today's Stats", callback_data="stats_today"),
                    InlineKeyboardButton(
                        "Yesterday's Stats", callback_data="stats_yesterday"
                    ),
                ],
                [
                    InlineKeyboardButton("Last 7 Days", callback_data="stats_7days"),
                    InlineKeyboardButton("Last 30 Days", callback_data="stats_30days"),
                ],
                [
                    InlineKeyboardButton(
                        "All Time Stats", callback_data="stats_alltime"
                    ),
                    InlineKeyboardButton(
                        "Compare Locations", callback_data="compare_locations"
                    ),
                ],
            ]

            reply_markup = InlineKeyboardMarkup(keyboard)

            await update.message.reply_text(
                "📊 *QR Code Statistics Dashboard*\n\n"
                "Select an option to view statistics:",
                reply_markup=reply_markup,
                parse_mode="Markdown",
            )
        except Exception as e:
            logger.error(f"Error displaying dashboard: {str(e)}")
            await update.message.reply_text(
                f"Error displaying dashboard. Please try again later."
            )

    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle button callbacks from the dashboard"""
        query = update.callback_query
        await query.answer()

        user = update.effective_user
        if not self.is_admin(user.username):
            await query.edit_message_text(
                "⛔ You don't have permission to use this feature."
            )
            return

        callback_data = query.data

        try:
            if callback_data == "stats_today":
                # Get today's stats
                today = timezone.now().date()
                locations = Location.objects.all()

                message = "\ud83d\udcca *Today's Statistics*\n\n"
                total_today = QRCodeScan.objects.filter(timestamp__date=today).count()
                message += f"*Total Scans Today: {total_today}*\n\n"

                for location in locations:
                    today_count = location.scans.filter(timestamp__date=today).count()
                    message += f"*{location.name}*: {today_count} scans\n"

                # Add back button
                keyboard = [
                    [
                        InlineKeyboardButton(
                            "Back to Dashboard", callback_data="back_to_dashboard"
                        )
                    ]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)

                await query.edit_message_text(
                    message, reply_markup=reply_markup, parse_mode="Markdown"
                )

            elif callback_data == "stats_yesterday":
                # Get yesterday's stats
                today = timezone.now().date()
                yesterday = today - datetime.timedelta(days=1)
                locations = Location.objects.all()

                message = "\ud83d\udcca *Yesterday's Statistics*\n\n"
                total_yesterday = QRCodeScan.objects.filter(
                    timestamp__date=yesterday
                ).count()
                message += f"*Total Scans Yesterday: {total_yesterday}*\n\n"

                for location in locations:
                    yesterday_count = location.scans.filter(
                        timestamp__date=yesterday
                    ).count()
                    message += f"*{location.name}*: {yesterday_count} scans\n"

                # Add back button
                keyboard = [
                    [
                        InlineKeyboardButton(
                            "Back to Dashboard", callback_data="back_to_dashboard"
                        )
                    ]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)

                await query.edit_message_text(
                    message, reply_markup=reply_markup, parse_mode="Markdown"
                )

            elif callback_data == "stats_7days":
                # Get last 7 days stats
                today = timezone.now().date()
                last_week = today - datetime.timedelta(days=7)
                locations = Location.objects.all()

                message = "\ud83d\udcca *Last 7 Days Statistics*\n\n"
                total_week = QRCodeScan.objects.filter(
                    timestamp__date__gte=last_week
                ).count()
                message += f"*Total Scans (Last 7 Days): {total_week}*\n\n"

                for location in locations:
                    week_count = location.scans.filter(
                        timestamp__date__gte=last_week
                    ).count()
                    message += f"*{location.name}*: {week_count} scans\n"

                # Add back button
                keyboard = [
                    [
                        InlineKeyboardButton(
                            "Back to Dashboard", callback_data="back_to_dashboard"
                        )
                    ]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)

                await query.edit_message_text(
                    message, reply_markup=reply_markup, parse_mode="Markdown"
                )

            elif callback_data == "stats_30days":
                # Get last 30 days stats
                today = timezone.now().date()
                last_month = today - datetime.timedelta(days=30)
                locations = Location.objects.all()

                message = "\ud83d\udcca *Last 30 Days Statistics*\n\n"
                total_month = QRCodeScan.objects.filter(
                    timestamp__date__gte=last_month
                ).count()
                message += f"*Total Scans (Last 30 Days): {total_month}*\n\n"

                for location in locations:
                    month_count = location.scans.filter(
                        timestamp__date__gte=last_month
                    ).count()
                    message += f"*{location.name}*: {month_count} scans\n"

                # Add back button
                keyboard = [
                    [
                        InlineKeyboardButton(
                            "Back to Dashboard", callback_data="back_to_dashboard"
                        )
                    ]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)

                await query.edit_message_text(
                    message, reply_markup=reply_markup, parse_mode="Markdown"
                )

            elif callback_data == "stats_alltime":
                # Get all-time stats
                locations = Location.objects.all()

                message = "\ud83d\udcca *All-Time Statistics*\n\n"
                total_all = QRCodeScan.objects.count()
                message += f"*Total Scans (All Time): {total_all}*\n\n"

                for location in locations:
                    all_count = location.scans.count()
                    percentage = 0
                    if total_all > 0:
                        percentage = (all_count / total_all) * 100
                    message += (
                        f"*{location.name}*: {all_count} scans ({percentage:.1f}%)\n"
                    )

                # Add back button
                keyboard = [
                    [
                        InlineKeyboardButton(
                            "Back to Dashboard", callback_data="back_to_dashboard"
                        )
                    ]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)

                await query.edit_message_text(
                    message, reply_markup=reply_markup, parse_mode="Markdown"
                )

            elif callback_data == "compare_locations":
                # Compare locations
                locations = Location.objects.all()

                if not locations.exists() or locations.count() < 2:
                    await query.edit_message_text(
                        "Need at least two locations to compare."
                    )
                    return

                # Calculate time periods
                today = timezone.now().date()
                yesterday = today - datetime.timedelta(days=1)
                last_week = today - datetime.timedelta(days=7)
                last_month = today - datetime.timedelta(days=30)

                # Format message
                message = "📊 *Location Comparison*\n\n"

                # Today's scans
                message += "*Today's Scans:*\n"
                for location in locations:
                    today_count = location.scans.filter(timestamp__date=today).count()
                    message += f"{location.name}: {today_count}\n"

                # Yesterday's scans
                message += "\n*Yesterday's Scans:*\n"
                for location in locations:
                    yesterday_count = location.scans.filter(
                        timestamp__date=yesterday
                    ).count()
                    message += f"{location.name}: {yesterday_count}\n"

                # Last 7 days
                message += "\n*Last 7 Days:*\n"
                for location in locations:
                    week_count = location.scans.filter(
                        timestamp__date__gte=last_week
                    ).count()
                    message += f"{location.name}: {week_count}\n"

                # Last 30 days
                message += "\n*Last 30 Days:*\n"
                for location in locations:
                    month_count = location.scans.filter(
                        timestamp__date__gte=last_month
                    ).count()
                    message += f"{location.name}: {month_count}\n"

                # All time
                message += "\n*All Time:*\n"
                for location in locations:
                    total_count = location.scans.count()
                    message += f"{location.name}: {total_count}\n"

                # Add back button
                keyboard = [
                    [
                        InlineKeyboardButton(
                            "Back to Dashboard", callback_data="back_to_dashboard"
                        )
                    ]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)

                await query.edit_message_text(
                    message, reply_markup=reply_markup, parse_mode="Markdown"
                )

            elif callback_data == "back_to_dashboard":
                # Return to dashboard
                keyboard = [
                    [
                        InlineKeyboardButton(
                            "Today's Stats", callback_data="stats_today"
                        ),
                        InlineKeyboardButton(
                            "Yesterday's Stats", callback_data="stats_yesterday"
                        ),
                    ],
                    [
                        InlineKeyboardButton(
                            "Last 7 Days", callback_data="stats_7days"
                        ),
                        InlineKeyboardButton(
                            "Last 30 Days", callback_data="stats_30days"
                        ),
                    ],
                    [
                        InlineKeyboardButton(
                            "All Time Stats", callback_data="stats_alltime"
                        ),
                        InlineKeyboardButton(
                            "Compare Locations", callback_data="compare_locations"
                        ),
                    ],
                ]

                reply_markup = InlineKeyboardMarkup(keyboard)

                await query.edit_message_text(
                    "📊 *QR Code Statistics Dashboard*\n\n"
                    "Select an option to view statistics:",
                    reply_markup=reply_markup,
                    parse_mode="Markdown",
                )

        except Exception as e:
            logger.error(f"Error handling button callback: {str(e)}")
            await query.edit_message_text(
                f"Error processing request. Please try again later."
            )
