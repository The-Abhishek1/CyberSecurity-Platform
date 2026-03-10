import logging
import sys
from datetime import datetime
from typing import Optional

# Configure logger
logger = logging.getLogger("security-orchestrator")
logger.setLevel(logging.INFO)

# Console handler
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

def setup_logging():
    """Setup logging configuration"""
    logger.info("Logging configured")
    return logger