"""
logger.py

Module configuring a standardized logger used across crawler modules.
"""

import os
import logging
from crawler.src.config_manager import ConfigManager

config = ConfigManager()

logger = logging.getLogger("crawler_logger")
logger.setLevel(logging.DEBUG)

log_file = config.get("log_file", "./logs/crawler.log")
os.makedirs(os.path.dirname(log_file), exist_ok=True)

file_handler = logging.FileHandler(log_file, mode='a', encoding='utf-8')
file_handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - %(message)s')
file_handler.setFormatter(formatter)

logger.addHandler(file_handler)
