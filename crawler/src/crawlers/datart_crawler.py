"""
datart_crawler.py

Crawler subclass specifically designed to scrape desktop computer product details from Datart.cz.
Uses Selenium WebDriver to handle JavaScript-rendered pages and BeautifulSoup for HTML parsing.

Crawler Workflow:
1. Collect product URLs from paginated product listings.
2. Extract detailed product specifications from each product URL.
"""

import re
import time

import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin

from crawler.src.crawlers.base_selenium_crawler import SeleniumBaseCrawler
from crawler.src.logger import logger
from crawler.src.utils.helpers import normalize_url, extract_attributes_from_property_tables

# URL patterns identifying product detail pages on Datart.cz
DATART_DETAIL_PAGE_PATTERNS = [
    re.compile(r'/herni-pocitac-.*\.html', re.IGNORECASE),
    re.compile(r'/pc-mini.*\.html', re.IGNORECASE),
    re.compile(r'/pocitac-.*\.html', re.IGNORECASE),
    re.compile(r'/stolni-pocitac-.*\.html', re.IGNORECASE)
]


class DatartCrawler(SeleniumBaseCrawler):
    """
    Web crawler specialized for scraping product details from Datart.cz.

    Extends:
        SeleniumBaseCrawler
    """

    def is_article_link(self, url):
        """
        Check if the URL is a Datart.cz product detail page.

        Args:
            url (str): URL to evaluate.

        Returns:
            bool: True if URL matches product detail patterns; False otherwise.
        """
        parsed = urlparse(url)
        return parsed.scheme in ["http", "https"] and any(pattern.search(parsed.path) for pattern in DATART_DETAIL_PAGE_PATTERNS)

    def extract_data_from_page(self, url):
        """
        Load a product page and extract data using Selenium and BeautifulSoup.

        Args:
            url (str): URL of the product page.

        Returns:
            dict or None: Extracted product specifications or None on failure.
        """
        logger.info(f"[{self.name}] Loading page: {url}")
        try:
            soup = self._get_page_soup(url, sleep_time=2, dismiss_banner=False)
            return self._parse_datart_product_page(soup, url)
        except Exception as e:
            logger.error(f"[{self.name}] Error loading {url}: {e}")
            return None

    def _parse_datart_product_page(self, soup, url):
        """
        Parse product specifications from the Datart.cz product page.

        Args:
            soup (BeautifulSoup): Parsed HTML of the product page.
            url (str): URL of the product page.

        Returns:
            dict or None: Product specifications or None if extraction fails.
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

        # Extract product specifications from property tables
        table_data = extract_attributes_from_property_tables(soup)

        for key, value in table_data.items():
            if value is not None:
                data[key] = value

        if all(v is None for v in data.values()):
            logger.info(f"[{self.name}] No specs found for {url}")
            return None

        logger.info(f"[{self.name}] Successfully extracted data for {url}")
        return data

    def crawl(self):
        """
        Main crawling process in two phases:
        1. Crawl listing pages to gather product URLs.
        2. Extract detailed data from each collected product URL.
        """
        if not self.start_urls:
            logger.error(f"[{self.name}] No start URLs provided.")
            return

        listing_queue = [normalize_url(u) for u in self.start_urls]
        visited_listings = set()
        product_urls = set()

        # Phase 1: Collect product URLs from paginated listings
        while listing_queue:
            current_list_url = listing_queue.pop(0)
            if current_list_url in visited_listings:
                continue
            visited_listings.add(current_list_url)

            logger.info(f"[{self.name}] Crawling listing page: {current_list_url}")

            try:
                self.driver.get(current_list_url)
                time.sleep(2)
                soup = BeautifulSoup(self.driver.page_source, "html.parser")

                new_products = 0
                for a in soup.find_all("a", href=True):
                    full_url = normalize_url(urljoin(current_list_url, a["href"]))
                    if self.is_article_link(full_url) and full_url not in product_urls:
                        new_products += 1
                        product_urls.add(full_url)
                logger.info(f"[{self.name}] Found {new_products} new product(s) on {current_list_url}")

                # Queue next page only if products were found on this listing.
                if new_products == 0:
                    logger.info(f"[{self.name}] No products found on {current_list_url}, skipping next page.")
                    continue

                next_url = self.get_next_page_url(current_list_url)
                if next_url in visited_listings or next_url in listing_queue:
                    continue

                try:
                    resp = requests.get(next_url, headers=self.headers, timeout=10)
                    if resp.status_code >= 400:
                        logger.info(f"[{self.name}] Next page {next_url} returned {resp.status_code}, skipping.")
                        continue
                    temp_soup = BeautifulSoup(resp.content, "html.parser")
                    if not temp_soup.find("div", class_="product-box"):
                        logger.info(f"[{self.name}] No product-box elements on next page {next_url}, skipping.")
                        continue
                    logger.info(f"[{self.name}] Queued next listing page: {next_url}")
                    listing_queue.append(next_url)

                except Exception as e:
                    logger.info(f"[{self.name}] Next listing page {next_url} not valid: {e}")

            except Exception as e:
                logger.error(f"[{self.name}] Error processing listing {current_list_url}: {e}")

        logger.info(f"[{self.name}] URL collection complete ({len(product_urls)} total products).")

        # Phase 2: Extract detailed product data
        for p_url in product_urls:
            if p_url in self.visited_urls:
                continue
            self.visited_urls.add(p_url)

            logger.info(f"[{self.name}] Extracting product data: {p_url}")
            data = self.extract_data_from_page(p_url)
            if data:
                self.collected_data.append(data)
                if len(self.collected_data) >= self.batch_size:
                    self._flush_data()

        # Flush remaining data
        if self.collected_data:
            self._flush_data()

        logger.info(f"[{self.name}] Crawling completed.")
        self.quit_driver()
