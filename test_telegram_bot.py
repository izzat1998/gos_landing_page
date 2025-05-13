#!/usr/bin/env python
"""
Test script to diagnose Telegram bot issues
"""
import logging
import os
import sys
import traceback
from datetime import datetime

import requests
from django.conf import settings
from django.core.management import call_command

# Configure logging
LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
os.makedirs(LOG_DIR, exist_ok=True)
log_file = os.path.join(LOG_DIR, f'telegram_debug_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')

# Configure root logger
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger('telegram_test')

def test_api_connection():
    """Test the connection to the API endpoint"""
    logger.info("Testing API connection...")
    
    try:
        api_url = f"{settings.SITE_URL}/api/location-stats/?days=30"
        headers = {"Authorization": f"Token {settings.API_TOKEN}"}
        
        logger.info(f"API URL: {api_url}")
        logger.info(f"Using token: {settings.API_TOKEN[:5]}...")
        
        response = requests.get(api_url, headers=headers, timeout=10)
        
        logger.info(f"API Response Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            logger.info(f"API Response Data: {data[:100]}...")  # Log first 100 chars
            logger.info("API connection successful!")
            return True
        else:
            logger.error(f"API Error: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        logger.error(f"API Connection Error: {str(e)}")
        logger.error(traceback.format_exc())
        return False

def check_telegram_token():
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

def run_diagnostics():
    """Run all diagnostic tests"""
    logger.info("Starting Telegram bot diagnostics...")
    logger.info(f"Log file: {log_file}")
    
    # Check Django settings
    logger.info(f"SITE_URL: {settings.SITE_URL}")
    logger.info(f"API_TOKEN configured: {'Yes' if settings.API_TOKEN else 'No'}")
    logger.info(f"TELEGRAM_BOT_TOKEN configured: {'Yes' if settings.TELEGRAM_BOT_TOKEN else 'No'}")
    
    # Test API connection
    api_ok = test_api_connection()
    logger.info(f"API Connection Test: {'PASSED' if api_ok else 'FAILED'}")
    
    # Check Telegram token
    token_ok = check_telegram_token()
    logger.info(f"Telegram Token Test: {'PASSED' if token_ok else 'FAILED'}")
    
    # Summary
    if api_ok and token_ok:
        logger.info("All tests PASSED! If you're still experiencing issues, check the specific function implementations.")
    else:
        logger.error("Some tests FAILED. See the log for details.")
    
    return api_ok and token_ok

if __name__ == "__main__":
    print(f"Diagnostic log will be written to: {log_file}")
    success = run_diagnostics()
    
    if success:
        print("\nAll diagnostic tests passed!")
        print("If you're still experiencing issues, the problem may be in specific command handlers.")
        print(f"Check the log file for more details: {log_file}")
    else:
        print("\nSome diagnostic tests failed!")
        print(f"Please check the log file for details: {log_file}")
