"""
base_crawler.py

Module providing a BaseCrawler class implementing the Template Method design pattern.
This class serves as the parent class for specific website crawlers that collect and process article or product data.
"""

import requests
from urllib.parse import urljoin
from bs4 import BeautifulSoup

from crawler.src.logger import logger
from crawler.src.config_manager import ConfigManager
from crawler.src.utils.helpers import normalize_url


class BaseCrawler:
    """
    Abstract base class for web crawlers.

    This class outlines a standardized crawling process using the Template Method pattern.
    Subclasses must define how to identify article/product links and extract data from pages.

    Methods to implement in subclasses:
        - is_article_link(url)
        - extract_data_from_page(url)
    """

    def __init__(self, name, data_queue, write_done_event):
        """
        Initialize the BaseCrawler instance.

        Args:
            name (str): Identifier for the crawler instance, used for logging and configuration.
            data_queue (queue.Queue): Queue for storing scraped data to be consumed by writer threads.
            write_done_event (threading.Event): Synchronization event to signal data write completion.
        """
        self.name = name
        self.data_queue = data_queue
        self.write_done_event = write_done_event

        # Load crawler-specific configuration
        self.config = ConfigManager().get_crawler_config(name)
        self.start_urls = self.config.get("start_urls", [])
        self.headers = {"User-Agent": self.config.get("user_agent", "WebCrawlerBot/1.0")}
        self.batch_size = ConfigManager().get("batch_size", 10)

        # Internal state management
        self.collected_data = []
        self.url_queue = [normalize_url(url) for url in self.start_urls]
        self.visited_urls = set()

    def is_article_link(self, url):
        """
        Determine whether a URL points to an article/product page.

        This method must be implemented by subclasses based on specific URL structures.

        Args:
            url (str): URL to evaluate.

        Returns:
            bool: True if URL is an article/product link; False otherwise.

        Raises:
            NotImplementedError: Always, as subclasses must override this method.
        """
        raise NotImplementedError("Subclasses must implement 'is_article_link()'.")

    def extract_data_from_page(self, url):
        """
        Extract relevant data from a given article/product page.

        This method must be implemented by subclasses to extract specific data.

        Args:
            url (str): URL of the article/product page.

        Returns:
            dict or None: Extracted data in dictionary form, or None if extraction fails.

        Raises:
            NotImplementedError: Always, as subclasses must override this method.
        """
        raise NotImplementedError("Subclasses must implement 'extract_data_from_page()'.")

    def crawl(self):
        """
        Execute the main crawling loop, handling URL fetching, parsing, and data extraction.

        Continuously processes URLs from the queue until exhausted, extracting new URLs and data.
        """
        if not self.start_urls:
            logger.error(f"[{self.name}] No start URLs provided.")
            return

        while self.url_queue:
            current_url = normalize_url(self.url_queue.pop(0))

            if current_url in self.visited_urls:
                continue
            self.visited_urls.add(current_url)

            logger.info(f"[{self.name}] Processing URL: {current_url}")

            try:
                response = requests.get(current_url, headers=self.headers, timeout=10)
                response.raise_for_status()
                soup = BeautifulSoup(response.content, "html.parser")

                # Extract and store data if it's an article link
                if self.is_article_link(current_url):
                    article_data = self.extract_data_from_page(current_url)
                    if article_data:
                        self.collected_data.append(article_data)
                        if len(self.collected_data) >= self.batch_size:
                            self._flush_data()

                # Discover and enqueue new article URLs
                for link in soup.find_all("a", href=True):
                    full_url = normalize_url(urljoin(current_url, link["href"]))
                    if full_url not in self.visited_urls and self.is_article_link(full_url):
                        self.url_queue.append(full_url)

            except requests.RequestException as e:
                logger.error(f"[{self.name}] HTTP error fetching {current_url}: {e}")
            except Exception as e:
                logger.error(f"[{self.name}] Unexpected error at {current_url}: {e}")

        # Ensure any remaining collected data is flushed
        if self.collected_data:
            self._flush_data()

        logger.info(f"[{self.name}] Crawling completed.")

    def _flush_data(self):
        """
        Flush collected data batch to the data queue for writer processing.

        Ensures data is safely transferred and synchronization is maintained.
        """
        self.write_done_event.clear()
        self.data_queue.put((self.name, self.collected_data))
        self.write_done_event.wait()
        self.collected_data = []
