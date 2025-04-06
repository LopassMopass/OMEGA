import re
import time
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin

from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException

from crawler.src.crawlers.base_selenium_crawler import SeleniumBaseCrawler
from crawler.src.logger import logger
from crawler.src.utils.helpers import normalize_url

# Regex to detect product-detail URLs
STOLNIPOCITACE_DETAIL_PAGE_PATTERNS = [
    re.compile(r'/[a-z0-9-]+/\d{4,}-[a-z0-9-]+\.html', re.IGNORECASE)
]

class StolniPocitaceCrawler(SeleniumBaseCrawler):
    """
    A crawler for stolnipocitace.cz that uses Selenium to handle JS-rendered
    pages. For each category (start URL) it fully follows the pagination chain
    by clicking the 'Další' button, gathers product-detail URLs, and then
    extracts product details including price and processor info.
    """

    def __init__(self, name, data_queue, write_done_event):
        super().__init__(name, data_queue, write_done_event)

    def is_article_link(self, url):
        parsed = urlparse(url)
        if parsed.scheme not in ["http", "https"]:
            return False
        return any(pattern.search(url) for pattern in STOLNIPOCITACE_DETAIL_PAGE_PATTERNS)

    def extract_data_from_page(self, url):
        logger.info(f"[{self.name}] Extracting data with Selenium: {url}")
        try:
            self.driver.get(url)
            time.sleep(2)  # Wait for JS-rendered content
            html = self.driver.page_source
        except Exception as e:
            logger.error(f"[{self.name}] Selenium error loading {url}: {e}")
            return None

        soup = BeautifulSoup(html, "html.parser")

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
            "price": None,
        }

        # 1) Parse price
        price_el = soup.select_one('p.our_price_display span#our_price_display.price[itemprop="price"]')
        if price_el:
            price_content = price_el.get("content", "").strip()
            if price_content:
                try:
                    data["price"] = float(price_content)
                except ValueError:
                    data["price"] = price_el.get_text(strip=True)
            else:
                data["price"] = price_el.get_text(strip=True)

        # 2) Parse specs from <div class="rte">
        specs_div = soup.find("div", class_="rte")
        if specs_div:
            for bold_el in specs_div.find_all("b"):
                label_text = bold_el.get_text(strip=True).rstrip(":").lower()
                raw_value = ""
                if bold_el.next_sibling and isinstance(bold_el.next_sibling, str):
                    raw_value = bold_el.next_sibling.strip(" :\n\r\t")

                if "procesor" in label_text:
                    data["model_procesoru"] = raw_value
                elif "operační systém" in label_text or "operacni system" in label_text:
                    data["operacni_system"] = raw_value
                elif "grafika" in label_text or "grafická karta" in label_text:
                    data["model_graficke_karty"] = raw_value
                elif "pevný disk" in label_text or "pevny disk" in label_text:
                    data["kapacita_uloziste"] = raw_value
                elif "paměť" in label_text or "pamet" in label_text:
                    data["velikost_ram"] = raw_value

            inner_html = specs_div.decode_contents()
            lines = inner_html.split("<br>")
            for line in lines:
                # Convert each line into plain text
                text_line = BeautifulSoup(line, "html.parser").get_text().strip()
                if text_line.lower().startswith("zdroj"):
                    # Remove the keyword "zdroj" and any extra spaces
                    zdroj_info = text_line[len("zdroj"):].strip()
                    data["zdroj"] = zdroj_info
                    break

        # 3) Parse specs from <table class="table-data-sheet">
        specs_table = soup.find("table", class_="table-data-sheet")
        if specs_table:
            for row in specs_table.find_all("tr"):
                cells = row.find_all(["td", "th"])

                if len(cells) == 2:

                    label = cells[0].get_text(strip=True).lower()
                    value = cells[1].get_text(strip=True)

                    if "procesor" in label:
                        data["model_procesoru"] = value
                    elif "operační systém" in label or "operacni system" in label:
                        data["operacni_system"] = value
                    elif "grafická karta" in label or "graficka karta" in label:
                        data["model_graficke_karty"] = value
                    elif "pevný disk" in label or "pevny disk" in label:
                        data["kapacita_uloziste"] = value
                    elif ("operační paměť" in label or "paměť" in label):
                        data["velikost_ram"] = value
                    elif "použití pc" in label or "pouziti pc" in label:
                        data["provedeni_pocitace"] = value

        # 4) Post-process to extract number of cores/frequency from model_procesoru
        if data["model_procesoru"]:
            cores, frequency = self.parse_processor_info(data["model_procesoru"])
            if cores:
                data["pocet_jader_procesoru"] = cores
            if frequency:
                data["frekvence_procesoru"] = frequency

        logger.info(f"[{self.name}] Extracted data for {url}: {data}")
        return data

    def parse_processor_info(self, text):
        cores = None
        frequency = None

        # e.g. "8 jader"
        match_cores = re.search(r'(\d+)\s*(?:jader|jádra|cores)', text, re.IGNORECASE)
        if match_cores:
            cores = match_cores.group(1)

        # e.g. "1,8 GHz" or "3.4 GHz"
        match_freq = re.search(r'(\d+[.,]\d+)\s*GHz', text, re.IGNORECASE)
        if match_freq:
            frequency = f"{match_freq.group(1)} GHz"

        return cores, frequency

    def crawl(self):
        if not self.start_urls:
            logger.error(f"[{self.name}] No start URLs provided.")
            return

        visited_listings = set()
        product_urls = set()

        # --- PHASE 1: For each start URL, exhaust pagination (by clicking 'Další') ---
        for start_url in self.start_urls:
            logger.info(f"[{self.name}] Starting category: {start_url}")
            self.driver.get(start_url)
            time.sleep(2)

            while True:
                # Parse the current page
                soup = BeautifulSoup(self.driver.page_source, "html.parser")

                current_url = self.driver.current_url
                if current_url in visited_listings:
                    break
                visited_listings.add(current_url)

                # Collect product links
                found_count = 0
                for a_tag in soup.find_all("a", href=True):
                    full_url = normalize_url(urljoin(current_url, a_tag["href"]))
                    if self.is_article_link(full_url) and full_url not in product_urls:
                        product_urls.add(full_url)
                        found_count += 1
                logger.info(f"[{self.name}] Found {found_count} product(s) on this page.")

                # Try to find and click the "Další" pagination link in Selenium
                try:
                    next_button = self.driver.find_element(By.CSS_SELECTOR, 'li#pagination_next a')
                except NoSuchElementException:
                    # No next page link => break
                    logger.info(f"[{self.name}] No 'Next' button found; finishing this category.")
                    break

                # Sometimes it's present but not clickable/active => check if disabled
                parent_li = next_button.find_element(By.XPATH, "./parent::li")
                if "disabled" in parent_li.get_attribute("class"):
                    logger.info(f"[{self.name}] 'Next' button is disabled; finishing this category.")
                    break

                # If we get here, we have a next button and it's not disabled => click it
                logger.info(f"[{self.name}] Clicking 'Next' to load more products.")
                next_button.click()
                time.sleep(3)  # Wait for next page content to load

            # After finishing "while True" for this category, we move on to the next start URL

        logger.info(f"[{self.name}] Finished collecting product URLs from all categories. Found {len(product_urls)} total.")

        # --- PHASE 2: Extract data from each product detail page ---
        for p_url in product_urls:
            if p_url in self.visited_urls:
                continue
            self.visited_urls.add(p_url)
            logger.info(f"[{self.name}] Processing product: {p_url}")
            try:
                data = self.extract_data_from_page(p_url)
                if data:
                    self.collected_data.append(data)
                    if len(self.collected_data) >= self.batch_size:
                        self._flush_data()
            except Exception as e:
                logger.error(f"[{self.name}] Error processing product page {p_url}: {e}")

        # Flush any remaining data
        if self.collected_data:
            self._flush_data()

        logger.info(f"[{self.name}] Crawling completed.")
        self.quit_driver()
