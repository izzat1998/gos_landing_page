import logging
import os
import traceback
from datetime import datetime

# Create logs directory if it doesn't exist
LOG_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "logs"
)
os.makedirs(LOG_DIR, exist_ok=True)

# Setup file handler with timestamp
log_file = os.path.join(
    LOG_DIR, f"telegram_debug_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
)

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler(log_file), logging.StreamHandler()],
)


def log_function_call(func_name, user_id=None, username=None, args=None, error=None):
    """Log function calls and errors"""
    logger = logging.getLogger("telegram_bot")

    if error:
        logger.error(f"ERROR in {func_name} - User: {user_id} ({username}) - {error}")
        logger.error(f"Traceback: {traceback.format_exc()}")
    else:
        logger.info(f"CALL {func_name} - User: {user_id} ({username}) - Args: {args}")


def log_api_request(url, status_code=None, response_text=None, error=None):
    """Log API requests and responses"""
    logger = logging.getLogger("telegram_bot")

    if error:
        logger.error(f"API ERROR - URL: {url} - {error}")
    else:
        logger.info(f"API REQUEST - URL: {url} - Status: {status_code}")
        if response_text:
            # Truncate long responses
            if len(response_text) > 500:
                response_text = response_text[:500] + "..."
            logger.debug(f"API RESPONSE: {response_text}")


def get_log_file_path():
    """Return the path to the log file"""
    return log_file
