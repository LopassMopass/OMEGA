"""
pocitarna_crawler.py

Crawler specialized in scraping desktop computer product specifications from Pocitarna.cz.
Leverages Selenium WebDriver for JavaScript-rendered content and BeautifulSoup for parsing HTML content.

Crawler Workflow:
1. Traverse product listings with pagination.
2. Gather all product URLs.
3. Extract detailed product data from each product URL.
"""

import re
import time

from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin

from crawler.src.crawlers.base_selenium_crawler import SeleniumBaseCrawler
from crawler.src.logger import logger
from crawler.src.utils.helpers import normalize_url

POCITARNA_DETAIL_PAGE_PATTERNS = [
    re.compile(r'/pocitace/[^/]+-\d+/?$', re.IGNORECASE),
]


class PocitarnaCrawler(SeleniumBaseCrawler):
    """
    Specialized crawler for Pocitarna.cz desktop computer products.

    Extends:
        SeleniumBaseCrawler
    """

    def is_article_link(self, url):
        """
        Check if the URL corresponds to a Pocitarna.cz product detail page.

        Args:
            url (str): URL to evaluate.

        Returns:
            bool: True if it's a product page, False otherwise.
        """
        parsed = urlparse(url)
        return parsed.scheme in ["http", "https"] and any(pattern.search(parsed.path) for pattern in POCITARNA_DETAIL_PAGE_PATTERNS)

    def extract_data_from_page(self, url):
        """
        Load product page and extract specifications using Selenium and BeautifulSoup.

        Args:
            url (str): Product page URL.

        Returns:
            dict or None: Extracted product data, or None on failure.
        """
        logger.info(f"[{self.name}] Extracting data from: {url}")
        try:
            soup = self._get_page_soup(url, sleep_time=2, dismiss_banner=False)
            return self._parse_pocitarna_product_page(soup, url)
        except Exception as e:
            logger.error(f"[{self.name}] Error loading {url}: {e}")
            return None

    def _parse_pocitarna_product_page(self, soup, url):
        """
        Parse specifications from a Pocitarna.cz product page.

        Args:
            soup (BeautifulSoup): Parsed HTML content.
            url (str): URL of the product page.

        Returns:
            dict: Extracted specifications.
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
            "operacni_system": None,
            "znacka": None,
            "provedeni_pocitace": None,
            "price": None,
        }

        # Extract price
        price_el = soup.select_one("strong.price-final[data-testid='productCardPrice']")
        if price_el:
            price_text = price_el.get_text(strip=True).replace("Kč", "").replace("\xa0", "").replace(" ", "")
            data["price"] = int(price_text) if price_text.isdigit() else None

        # Extract product parameters
        for param in soup.select("div.fv-parameter"):
            data_param = param.get("data-param", "").lower()
            value_el = param.select_one("div.value")
            if not data_param or not value_el:
                continue
            value = value_el.get_text(strip=True)

            if "model procesoru" in data_param:
                data["model_procesoru"] = value
            elif "frekvence procesoru" in data_param:
                data["frekvence_procesoru"] = value
            elif "počet jader" in data_param:
                data["pocet_jader_procesoru"] = value
            elif "operační paměť velikost" in data_param:
                data["velikost_ram"] = value
            elif "integrovaná grafická karta" in data_param:
                data["model_graficke_karty"] = value
            elif "operační systém" in data_param:
                data["operacni_system"] = value
            elif "značka" in data_param:
                data["znacka"] = value
            elif "úložiště" in data_param:
                if "ssd" in value.lower() or "hdd" in value.lower():
                    data["typ_uloziste"] = value
                else:
                    data["kapacita_uloziste"] = value
            elif "provedení" in data_param:
                data["provedeni_pocitace"] = value

        logger.info(f"[{self.name}] Data extraction complete for {url}")
        return data

    def crawl(self):
        """
        Main crawler method to gather URLs and extract product data systematically.
        """
        if not self.start_urls:
            logger.error(f"[{self.name}] No start URLs provided.")
            return

        listing_queue = [normalize_url(u) for u in self.start_urls]
        visited_listings = set()
        product_urls = set()

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
                        product_urls.add(full_url)
                        new_products += 1

                logger.info(f"[{self.name}] Found {new_products} new product(s) on {current_list_url}")

                # Look for next page link with class "next pagination-link"
                next_link = soup.find("a", class_="next pagination-link")
                if next_link and next_link.get("href"):
                    next_page_url = normalize_url(urljoin(current_list_url, next_link["href"]))
                    if next_page_url not in visited_listings and next_page_url not in listing_queue:
                        listing_queue.append(next_page_url)
                else:
                    logger.info(f"[{self.name}] No next page found for {current_list_url}")

            except Exception as e:
                logger.error(f"[{self.name}] Error crawling {current_list_url}: {e}")

        for product_url in product_urls:
            if product_url in self.visited_urls:
                continue
            self.visited_urls.add(product_url)
            data = self.extract_data_from_page(product_url)
            if data:
                self.collected_data.append(data)
                if len(self.collected_data) >= self.batch_size:
                    self._flush_data()

        if self.collected_data:
            self._flush_data()

        logger.info(f"[{self.name}] Crawling completed.")
        self.quit_driver()
