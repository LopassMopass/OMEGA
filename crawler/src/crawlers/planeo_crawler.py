"""
planeo_crawler.py

Crawler designed for extracting desktop computer specifications from Planeo.cz.
Utilizes undetected-chromedriver (Selenium) for enhanced handling of JavaScript-rendered pages,
cookie consent dialogs, and BeautifulSoup for parsing HTML content.

Crawler Workflow:
1. Navigate product listings with pagination.
2. Collect product detail URLs from listing pages.
3. Extract detailed product data from each product URL.
"""

import re
import undetected_chromedriver as uc
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin

from crawler.src.crawlers.base_selenium_crawler import SeleniumBaseCrawler
from crawler.src.logger import logger
from crawler.src.utils.helpers import normalize_url, get_planeo_next_page_url

from selenium.common import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


class PlaneoCrawler(SeleniumBaseCrawler):
    """
    Specialized crawler for scraping product data from Planeo.cz.

    Extends:
        SeleniumBaseCrawler
    """

    def __init__(self, *args, **kwargs):
        """
        Initialize the crawler with undetected-chromedriver to handle anti-bot measures effectively.
        """
        super().__init__(*args, **kwargs)

        options = uc.ChromeOptions()
        options.add_argument("--start-maximized")
        options.add_argument("--lang=cs")
        user_agent = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/135.0.7049.42 Safari/537.36")
        options.add_argument(f"--user-agent={user_agent}")

        self.driver = uc.Chrome(options=options)
        self.driver.execute_cdp_cmd("Network.setExtraHTTPHeaders", {"headers": {"User-Agent": user_agent}})

    def dismiss_cookie_banner(self):
        """
        Dismiss the cookie consent banner if present on the page to avoid obstructions during crawling.
        """
        try:
            WebDriverWait(self.driver, 8).until(
                EC.element_to_be_clickable((By.ID, "CybotCookiebotDialogBodyButtonDecline"))
            ).click()
            logger.info("[PlaneoCrawler] Cookie banner dismissed.")
        except TimeoutException:
            logger.debug("[PlaneoCrawler] Cookie banner not found.")

    def is_article_link(self, url):
        """
        Determine if the URL points to a valid product detail page on Planeo.cz.

        Args:
            url (str): URL to evaluate.

        Returns:
            bool: True if it's a valid product detail page, False otherwise.
        """
        parsed = urlparse(url)
        return 'planeo' in parsed.netloc and parsed.path.strip("/") != ""

    def extract_data_from_page(self, url):
        """
        Load product page and extract detailed specifications using Selenium and BeautifulSoup.

        Args:
            url (str): URL of the product page.

        Returns:
            dict or None: Product data dictionary or None if extraction fails.
        """
        logger.info(f"[{self.name}] Extracting data from: {url}")
        try:
            self.dismiss_cookie_banner()
            soup = self._get_page_soup(url, sleep_time=2, dismiss_banner=False)
            return self._parse_planeo_product_page(soup, url)
        except Exception as e:
            logger.error(f"[{self.name}] Error loading {url}: {e}")
            return None

    def _parse_planeo_product_page(self, soup, url):
        """
        Parse product specifications from a Planeo.cz product page.

        Args:
            soup (BeautifulSoup): Parsed HTML of the page.
            url (str): Product page URL.

        Returns:
            dict: Extracted product specifications.
        """
        data = {
            "model_procesoru": None,
            "frekvence_procesoru": None,
            "pocet_jader_procesoru": None,
            "model_graficke_karty": None,
            "pamet_graficke_karty": None,
            "kapacita_uloziste": None,
            "typ_uloziste": None,
            "velikost_ram": None,
            "operacni_system": None,
            "znacka": None,
            "price": None,
        }

        parameters_div = soup.find("div", id="parameters")
        if parameters_div:
            for row in parameters_div.select("tr.dfl.jcsb.pr2.w100p"):
                th, td = row.select_one("th.pl1"), row.select_one("td.pl1")
                if not th or not td:
                    continue
                label, value = th.get_text(strip=True).lower(), td.get_text(strip=True)

                if "model procesoru" in label:
                    data["model_procesoru"] = value
                elif "frekvence procesoru" in label:
                    data["frekvence_procesoru"] = value
                elif label == "grafika":
                    data["model_graficke_karty"] = value
                elif "paměť grafické karty" in label:
                    data["pamet_graficke_karty"] = value
                elif "ssd disk" in label:
                    data["kapacita_uloziste"] = value
                    data["typ_uloziste"] = "SSD"
                elif "operační paměť gb" in label:
                    data["velikost_ram"] = value
                elif "operační systém" in label:
                    data["operacni_system"] = value
                elif "výrobce procesoru" in label:
                    data["znacka"] = value

        price_div = soup.find("span", class_="price-value")
        if price_div:
            raw_price = re.sub(r"\D", "", price_div.get_text())
            data["price"] = int(raw_price) if raw_price.isdigit() else None

        logger.info(f"[{self.name}] Successfully extracted data from {url}")
        return data

    def crawl(self):
        """
        Main crawler method performing two-phase crawling:
        1. Collect all product URLs.
        2. Extract detailed product data from each URL.
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
                self.dismiss_cookie_banner()
                soup = self._get_page_soup(current_list_url, sleep_time=2, dismiss_banner=False)

                for div in soup.select("div.c-product a[href]"):
                    full_url = normalize_url(urljoin(current_list_url, div["href"]))
                    if self.is_article_link(full_url):
                        product_urls.add(full_url)

                next_url = get_planeo_next_page_url(current_list_url, soup)
                if next_url and next_url not in visited_listings:
                    listing_queue.append(next_url)

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
