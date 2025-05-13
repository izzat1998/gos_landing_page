from django.core.management.base import BaseCommand
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import requests
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Runs the Telegram bot for QR code statistics'
    
    def handle(self, *args, **kwargs):
        # Set up logging
        logging.basicConfig(
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            level=logging.INFO
        )
        
        # Create the application
        application = ApplicationBuilder().token(settings.TELEGRAM_BOT_TOKEN).build()
        
        # Add command handlers
        application.add_handler(CommandHandler("start", self.start_command))
        application.add_handler(CommandHandler("stats", self.stats_command))
        application.add_handler(CommandHandler("help", self.help_command))
        
        self.stdout.write('Starting Telegram bot...')
        application.run_polling()
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Send a welcome message when the command /start is issued."""
        await update.message.reply_text(
            "👋 Welcome to the GOS Furniture QR Code Statistics Bot!\n\n"
            "Use /stats to see QR code scan statistics\n"
            "Use /help to see available commands"
        )
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Send a help message when the command /help is issued."""
        await update.message.reply_text(
            "Available commands:\n\n"
            "/stats - View QR code scan statistics\n"
            "/stats 7 - View statistics for the last 7 days\n"
            "/help - Show this help message"
        )
    
    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Get and display QR code statistics."""
        # Get days parameter if provided (default: 30)
        days = 30
        if context.args and context.args[0].isdigit():
            days = int(context.args[0])
        
        # Get stats from API
        api_url = f"{settings.SITE_URL}/api/location-stats/?days={days}"
        headers = {'Authorization': f'Token {settings.API_TOKEN}'}
        
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
                
            await update.message.reply_text(message, parse_mode='Markdown')
        except Exception as e:
            logger.error(f"Error fetching statistics: {str(e)}")
            await update.message.reply_text(f"Error fetching statistics. Please try again later.")
