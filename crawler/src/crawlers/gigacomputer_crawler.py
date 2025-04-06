"""
gigacomputer_crawler.py

Crawler specialized in scraping desktop computer specifications from Gigacomputer.cz.
Utilizes Selenium WebDriver to handle JavaScript-rendered content and BeautifulSoup for HTML parsing.

Crawler Workflow:
1. Collect product URLs from paginated listings.
2. Extract detailed product specifications from each collected URL.
"""

import time
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin

from crawler.src.crawlers.base_selenium_crawler import SeleniumBaseCrawler
from crawler.src.logger import logger
from crawler.src.utils.helpers import normalize_url


class GigacomputerCrawler(SeleniumBaseCrawler):
    """
    Specialized crawler for scraping desktop computer products from Gigacomputer.cz.

    This crawler goes through a two-phase process:
      1) Gathering product links from listing pages (pagination).
      2) Visiting each product detail page to extract specifications, including
         processor, RAM, storage, GPU, and price information.

    Inherits:
        SeleniumBaseCrawler: A base class providing Selenium WebDriver setup,
        teardown, and helper methods for page retrieval.

    Attributes:
        visited_urls (set): Keeps track of product pages already visited to avoid duplicates.
        collected_data (list): Stores scraped product data dictionaries.
        batch_size (int): Threshold for writing partial results (flush) during scraping.
        start_urls (list): Initial listing pages from which the crawler begins.
        name (str): Identifier for logging.
    """

    def is_article_link(self, url):
        """
        Check if a given URL is likely to be a product detail link on Gigacomputer.cz.

        This method inspects the URL structure and path to determine if it includes
        "/zbozi/" and ends with ".html". If those conditions hold, we assume the URL
        points to a specific product detail page.

        Args:
            url (str): The URL to evaluate.

        Returns:
            bool: True if the URL resembles a valid product detail page; False otherwise.
        """
        parsed = urlparse(url)
        return parsed.scheme in ["http", "https"] and "/zbozi/" in parsed.path and parsed.path.lower().endswith(".html")

    def extract_data_from_page(self, url):
        """
        Fetch a product detail page and extract relevant specifications.

        This is the main entry point for retrieving a product's data. It leverages
        the Selenium WebDriver (inherited from SeleniumBaseCrawler) to load the page,
        handle JavaScript, and parse the result via BeautifulSoup. It then calls
        an internal parsing method to structure the data.

        Args:
            url (str): The product detail page URL.

        Returns:
            dict or None: A dictionary of product fields if successful, or None on error.
        """
        logger.info(f"[{self.name}] Loading product page: {url}")
        try:
            # Retrieve the page as BeautifulSoup; a short sleep is included for page load
            soup = self._get_page_soup(url, sleep_time=2, dismiss_banner=False)
            return self._parse_gigacomputer_product_page(soup, url)
        except Exception as e:
            logger.error(f"[{self.name}] Error loading {url}: {e}")
            return None

    def _parse_gigacomputer_product_page(self, soup, url):
        """
        Parse the HTML content of a Gigacomputer.cz product page to extract specs.

        This method inspects specific blocks of HTML (like #parameters, #priceGroup)
        to gather data about CPU, GPU, RAM, storage, OS, brand, and price.

        Args:
            soup (BeautifulSoup): The parsed HTML of the product page.
            url (str): The product page URL, used for logging and error context.

        Returns:
            dict: A dictionary of product fields:
                  {
                    "model_procesoru": str or None,
                    "pocet_jader_procesoru": str or None,
                    "frekvence_procesoru": str or None,
                    "model_graficke_karty": str or None,
                    "pamet_graficke_karty": str or None,
                    "kapacita_uloziste": str or None,
                    "typ_uloziste": str or None,
                    "velikost_ram": str or None,
                    "provedeni_pocitace": str or None,
                    "operacni_system": str or None,
                    "znacka": str or None,
                    "price": str or None
                  }
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
            "provedeni_pocitace": None,
            "operacni_system": None,
            "znacka": None,
            "price": None
        }

        # Locate parameter blocks
        parameters_div = soup.find("div", id="parameters")
        if not parameters_div:
            logger.info(f"[{self.name}] No parameters found on {url}")
            return data

        # For each parameter block, gather relevant specs
        for block in parameters_div.find_all("div", class_="parameter"):
            title_tag = block.find("div", class_="title")
            items = block.find_all("div", class_="item")

            if not title_tag or not items:
                continue

            title = title_tag.get_text(strip=True).lower()
            block_data = {}
            # Each .item has a .name and a .value
            for item in items:
                name_span = item.find("span", class_="name")
                value_span = item.find("span", class_="value")
                if name_span and value_span:
                    key = name_span.get_text(strip=True)
                    val = value_span.get_text(strip=True)
                    block_data[key] = val

            # Map extracted fields into our data dictionary
            if title == "procesor":
                model = " ".join(filter(None, [
                    block_data.get("Výrobce"),
                    block_data.get("Modelová řada"),
                    block_data.get("Typ")
                ]))
                data["model_procesoru"] = model or None
                data["pocet_jader_procesoru"] = block_data.get("Počet jader")
                data["frekvence_procesoru"] = block_data.get("Frekvence")

            elif title == "grafická karta":
                gpu_model = " ".join(filter(None, [
                    block_data.get("Modelová řada"),
                    block_data.get("Typ")
                ]))
                data["model_graficke_karty"] = gpu_model or None
                data["pamet_graficke_karty"] = block_data.get("Vlastní paměť")

            elif title == "pevný disk":
                data["kapacita_uloziste"] = (
                    block_data.get("Celková kapacita") or
                    block_data.get("Kapacita SSD")
                )
                data["typ_uloziste"] = block_data.get("Typ")

            elif title == "operační paměť":
                data["velikost_ram"] = block_data.get("Celková kapacita")

            elif title == "velikost":
                data["provedeni_pocitace"] = block_data.get("Velikost")

            elif title == "operační systém":
                data["operacni_system"] = block_data.get("Název")

        # Extract price from #priceGroup
        price_div = soup.find("div", id="priceGroup")
        if price_div:
            price_span = price_div.find("span", itemprop="price")
            if price_span and price_span.has_attr("content"):
                data["price"] = price_span["content"]

        logger.info(f"[{self.name}] Extracted data successfully for {url}")
        return data

    def crawl(self):
        """
        Perform a two-phase crawl:
          1) Collect product listing URLs from pagination.
          2) Visit each product detail page (extracted in phase 1)
             and scrape the relevant fields.

        This method iterates over start URLs, discovering subsequent listing pages
        via rel="next" links, and collecting product detail links by checking each
        <a> tag with is_article_link(). The final data is stored in collected_data
        and optionally written out in batches.

        Raises:
            SystemExit: If no start URLs are defined.
        """
        if not self.start_urls:
            logger.error(f"[{self.name}] No start URLs provided.")
            return

        listing_queue = [normalize_url(u) for u in self.start_urls]
        visited_listings = set()
        product_urls = set()

        # Phase 1: Collect product URLs from listing pages
        while listing_queue:
            current_list_url = listing_queue.pop(0)
            if current_list_url in visited_listings:
                continue
            visited_listings.add(current_list_url)

            logger.info(f"[{self.name}] Processing listing: {current_list_url}")

            try:
                self.driver.get(current_list_url)
                time.sleep(2)
                soup = BeautifulSoup(self.driver.page_source, "html.parser")

                # Collect product URLs on the listing page
                new_products = 0
                for a in soup.find_all("a", href=True):
                    full_url = normalize_url(urljoin(current_list_url, a["href"]))
                    if self.is_article_link(full_url) and full_url not in product_urls:
                        new_products += 1
                        product_urls.add(full_url)
                logger.info(f"[{self.name}] Found {new_products} new product(s) on {current_list_url}")

                # Check for next page using rel="next" link
                next_link_tag = soup.find("a", rel="next")
                if next_link_tag:
                    next_url = urljoin(current_list_url, next_link_tag.get("href"))
                    if next_url not in visited_listings:
                        logger.info(f"[{self.name}] Queuing next listing page: {next_url}")
                        listing_queue.append(next_url)
                else:
                    logger.info(f"[{self.name}] No next page found on {current_list_url}")

            except Exception as e:
                logger.error(f"[{self.name}] Error processing {current_list_url}: {e}")

        logger.info(f"[{self.name}] URL collection completed ({len(product_urls)} total products).")

        # Phase 2: Visit each product URL and parse specs
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

        # Flush any remaining data after crawling
        if self.collected_data:
            self._flush_data()

        logger.info(f"[{self.name}] Crawling completed.")
        self.quit_driver()
