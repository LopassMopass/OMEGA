"""
alza_crawler.py

Crawler subclass specifically designed to scrape desktop computer product details from Alza.cz.
Implements Selenium WebDriver for JavaScript-rendered pagination and BeautifulSoup for HTML parsing.

Crawler Workflow:
1. Collect product URLs from paginated product listings.
2. For each product URL, extract detailed product specifications.
"""

import re
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

from crawler.src.crawlers.base_selenium_crawler import SeleniumBaseCrawler
from crawler.src.logger import logger
from crawler.src.utils.helpers import normalize_url, extract_attributes_from_property_tables


class AlzaCrawler(SeleniumBaseCrawler):
    """
    A web crawler specialized for scraping Alza.cz desktop computer products.

    Extends:
        SeleniumBaseCrawler
    """

    def is_article_link(self, url):
        """
        Determine whether the URL corresponds to a product detail page on Alza.cz.

        Criteria:
            - URL contains "alza.cz" domain.
            - URL includes 'dq=' parameter or ends with '-d<number>.htm'.

        Args:
            url (str): The URL to evaluate.

        Returns:
            bool: True if it's a product page URL; False otherwise.
        """
        parsed = urlparse(url)
        return (
            parsed.scheme in ["http", "https"]
            and "alza.cz" in parsed.netloc
            and (
                "dq=" in parsed.query
                or re.search(r"-d\d+\.htm$", parsed.path) is not None
            )
        )

    def get_next_page_url(self, current_list_url, soup=None):
        """
        Extract the next listing page URL from pagination using BeautifulSoup.

        Args:
            current_list_url (str): URL of the current listing page.
            soup (BeautifulSoup, optional): Parsed HTML soup of the current page. Defaults to None.

        Returns:
            str or None: Next page URL if found; None otherwise.
        """
        if soup is None:
            soup = BeautifulSoup(self.driver.page_source, "html.parser")

        next_link = soup.select_one("a.next.fa.fa-chevron-right[href]")
        if next_link:
            next_url = urljoin(current_list_url, next_link["href"])
            logger.info(f"[{self.name}] Next listing URL found: {next_url}")
            return next_url

        logger.info(f"[{self.name}] No next listing page found (end of pagination).")
        return None

    def extract_data_from_page(self, url):
        """
        Load and extract product details from the product page using Selenium and BeautifulSoup.

        Args:
            url (str): Product page URL.

        Returns:
            dict or None: Dictionary with product specifications, or None if extraction fails.
        """
        logger.info(f"[{self.name}] Extracting data using Selenium: {url}")
        try:
            soup = self._get_page_soup(url, sleep_time=2, dismiss_banner=False)
            return self._parse_alza_product_page(soup, url)
        except Exception as e:
            logger.error(f"[{self.name}] Selenium error loading {url}: {e}")
            return None

    def _parse_alza_product_page(self, soup, url):
        """
        Parse product specifications from HTML soup of the Alza product page.

        Args:
            soup (BeautifulSoup): Parsed HTML content of the product page.
            url (str): URL of the product page (used for logging purposes).

        Returns:
            dict or None: Dictionary containing product specs, or None if no data is found.
        """
        data = {
            "model_procesoru": None,
            "pocet_jader_procesoru": None,
            "frekvence_procesoru": None,
            "model_graficke_karty": None,
            "pamet_graficke_karty": None,
            "kapacita_uloziste": None,
            "typ_uloziste": None,
            "velikost_ram": None,
            "zdroj": None,
            "provedeni_pocitace": None,
            "operacni_system": None,
            "znacka": None,
        }

        # Extract data from predefined tables using helper function
        table_data = extract_attributes_from_property_tables(soup)

        # Update extracted values to data dictionary
        for key, val in table_data.items():
            if val is not None:
                data[key] = val

        if all(v is None for v in data.values()):
            logger.info(f"[{self.name}] No recognizable product specs found for {url}")
            return None

        logger.info(f"[{self.name}] Successfully extracted data for {url}")
        return data

    def crawl(self):
        """
        Main crawler method performing two-phase crawling:
        1. Collect all product detail URLs by traversing listing pages.
        2. Extract product data from each collected URL.
        """
        if not self.start_urls:
            logger.error(f"[{self.name}] No start URLs provided.")
            return

        listing_queue = [normalize_url(u) for u in self.start_urls]
        visited_listings = set()
        product_urls = set()

        # Phase 1: Collect Product URLs
        while listing_queue:
            current_list_url = listing_queue.pop(0)
            if current_list_url in visited_listings:
                continue
            visited_listings.add(current_list_url)

            logger.info(f"[{self.name}] Crawling listing page: {current_list_url}")

            try:
                soup = self._get_page_soup(current_list_url, sleep_time=2, dismiss_banner=False)

                # Find and store unique product URLs
                new_products = {
                    url for url in self._collect_product_urls(current_list_url, sleep_time=2)
                    if self.is_article_link(url)
                }
                product_urls.update(new_products)

                logger.info(f"[{self.name}] Found {len(new_products)} new products on page.")

                # Queue next page if exists
                next_url = self.get_next_page_url(current_list_url, soup)
                if next_url and next_url not in visited_listings:
                    listing_queue.append(next_url)

            except Exception as e:
                logger.error(f"[{self.name}] Error processing {current_list_url}: {e}")

        logger.info(f"[{self.name}] Finished URL collection ({len(product_urls)} total products).")

        # Phase 2: Extract Product Data
        for product_url in product_urls:
            if product_url in self.visited_urls:
                continue
            self.visited_urls.add(product_url)

            logger.info(f"[{self.name}] Extracting product: {product_url}")
            data = self.extract_data_from_page(product_url)
            if data:
                self.collected_data.append(data)
                if len(self.collected_data) >= self.batch_size:
                    self._flush_data()

        # Flush any remaining data
        if self.collected_data:
            self._flush_data()

        logger.info(f"[{self.name}] Crawling completed.")
        self.quit_driver()
