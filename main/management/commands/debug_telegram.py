import logging
import os
import sys
import traceback
from datetime import datetime

import requests
from django.conf import settings
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = "Диагностика проблем с Telegram ботом"

    def handle(self, *args, **options):
        # Configure logging
        LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'logs')
        os.makedirs(LOG_DIR, exist_ok=True)
        log_file = os.path.join(LOG_DIR, f'telegram_debug_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')

        # Configure file logger
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)

        # Get the logger
        logger = logging.getLogger('telegram_debug')
        logger.setLevel(logging.DEBUG)
        logger.addHandler(file_handler)
        
        # Also log to console
        console = logging.StreamHandler()
        console.setLevel(logging.INFO)
        console.setFormatter(formatter)
        logger.addHandler(console)

        self.stdout.write(f"Diagnostic log will be written to: {log_file}")
        success = self.run_diagnostics(logger)
        
        if success:
            self.stdout.write(self.style.SUCCESS("\nAll diagnostic tests passed!"))
            self.stdout.write("If you're still experiencing issues, the problem may be in specific command handlers.")
            self.stdout.write(f"Check the log file for more details: {log_file}")
        else:
            self.stdout.write(self.style.ERROR("\nSome diagnostic tests failed!"))
            self.stdout.write(f"Please check the log file for details: {log_file}")

    def test_api_connection(self, logger):
        """Test the connection to the API endpoint"""
        logger.info("Testing API connection...")
        
        try:
            api_url = f"{settings.SITE_URL}/api/location-stats/?days=30"
            headers = {"Authorization": f"Token {settings.API_TOKEN}"}
            
            logger.info(f"API URL: {api_url}")
            logger.info(f"Using token: {settings.API_TOKEN[:5] if settings.API_TOKEN else 'None'}...")
            
            response = requests.get(api_url, headers=headers, timeout=10)
            
            logger.info(f"API Response Status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                logger.info(f"API Response Data: {str(data)[:100]}...")  # Log first 100 chars
                logger.info("API connection successful!")
                return True
            else:
                logger.error(f"API Error: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            logger.error(f"API Connection Error: {str(e)}")
            logger.error(traceback.format_exc())
            return False

    def check_telegram_token(self, logger):
        """Check if the Telegram token is valid"""
        logger.info("Checking Telegram token...")
        
        try:
            token = settings.TELEGRAM_BOT_TOKEN
            if not token:
                logger.error("Telegram token is not configured")
                return False
                
            # Make a simple request to the Telegram API to check token validity
            url = f"https://api.telegram.org/bot{token}/getMe"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('ok'):
                    bot_info = data.get('result', {})
                    logger.info(f"Telegram token is valid! Bot: {bot_info.get('username')}")
                    return True
                else:
                    logger.error(f"Telegram API error: {data}")
                    return False
            else:
                logger.error(f"Telegram API returned status code: {response.status_code}")
                logger.error(f"Response: {response.text}")
                return False
        except Exception as e:
            logger.error(f"Error checking Telegram token: {str(e)}")
            logger.error(traceback.format_exc())
            return False

    def run_diagnostics(self, logger):
        """Run all diagnostic tests"""
        logger.info("Starting Telegram bot diagnostics...")
        
        # Check Django settings
        logger.info(f"SITE_URL: {settings.SITE_URL}")
        logger.info(f"API_TOKEN configured: {'Yes' if settings.API_TOKEN else 'No'}")
        logger.info(f"TELEGRAM_BOT_TOKEN configured: {'Yes' if settings.TELEGRAM_BOT_TOKEN else 'No'}")
        
        # Test API connection
        api_ok = self.test_api_connection(logger)
        logger.info(f"API Connection Test: {'PASSED' if api_ok else 'FAILED'}")
        
        # Check Telegram token
        token_ok = self.check_telegram_token(logger)
        logger.info(f"Telegram Token Test: {'PASSED' if token_ok else 'FAILED'}")
        
        # Summary
        if api_ok and token_ok:
            logger.info("All tests PASSED! If you're still experiencing issues, check the specific function implementations.")
        else:
            logger.error("Some tests FAILED. See the log for details.")
        
        return api_ok and token_ok
