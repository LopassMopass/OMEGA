"""
writer.py

Module responsible for asynchronously writing scraped data to JSON files.
"""

import json
import os
from crawler.src.logger import logger
from crawler.src.config_manager import ConfigManager

def writer_thread(data_queue, write_done_events):
    """
    Thread function continuously writing data from crawlers to JSON files.

    Args:
        data_queue (queue.Queue): Queue from which to retrieve data.
        write_done_events (dict): Events indicating write completion per crawler.
    """
    config = ConfigManager()
    output_dir = config.get("output_directory", "./data")
    os.makedirs(output_dir, exist_ok=True)

    all_data = {src: [] for src in write_done_events}

    while True:
        source_name, data = data_queue.get()
        if source_name == "STOP":
            logger.info("[writer] Stopping writer thread.")
            break

        all_data[source_name].extend(data)

        filename = os.path.join(output_dir, f"{source_name}.json")
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(all_data[source_name], f, ensure_ascii=False, indent=4)

        logger.info(f"[writer] Wrote {len(data)} items to {filename}. Total: {len(all_data[source_name])}")
        write_done_events[source_name].set()
