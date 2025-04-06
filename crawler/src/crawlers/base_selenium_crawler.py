"""
base_selenium_crawler.py

Module providing SeleniumBaseCrawler, extending BaseCrawler for handling JavaScript-rendered web pages using Selenium WebDriver.
"""
import time

from urllib.parse import urlparse, parse_qs, urlencode, urlunparse, urljoin

from bs4 import BeautifulSoup

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

from crawler.src.crawlers.base_crawler import BaseCrawler
from crawler.src.utils.helpers import normalize_url


class SeleniumBaseCrawler(BaseCrawler):
    """
    Base crawler class leveraging Selenium WebDriver to support crawling JavaScript-driven websites.

    Extends the standard BaseCrawler functionalities with Selenium capabilities.
    """

    def __init__(self, name, data_queue, write_done_event):
        """
        Initialize Selenium WebDriver alongside standard crawler setup.

        Args:
            name (str): Name identifier for the crawler instance.
            data_queue (queue.Queue): Queue to store extracted data.
            write_done_event (threading.Event): Event signaling data write completion.
        """
        super().__init__(name, data_queue, write_done_event)

        # Configure Selenium options for headless browsing
        options = Options()
        options.add_argument("--headless=new")
        options.add_argument("--disable-gpu")

        # Initialize Selenium WebDriver
        self.driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=options
        )

    def get_next_page_url(self, current_url):
        """
        Compute the URL for the next pagination page based on URL query parameters.

        This method increments the 'page' parameter in the current URL, handling cases where it doesn't yet exist.

        Args:
            current_url (str): URL of the current pagination page.

        Returns:
            str: URL of the next pagination page.
        """
        parsed_url = urlparse(current_url)
        query_params = parse_qs(parsed_url.query)

        current_page = int(query_params.get("page", ["1"])[0])
        query_params["page"] = [str(current_page + 1)]

        new_query = urlencode(query_params, doseq=True)
        next_page_url = urlunparse(parsed_url._replace(query=new_query))

        return next_page_url

    def _get_page_soup(self, url, sleep_time=2, dismiss_banner=False):
        """
        Load a page using Selenium and return a BeautifulSoup object of the page source.

        Args:
            url (str): URL of the page to load.
            sleep_time (int, optional): Seconds to wait for page to render. Defaults to 2.
            dismiss_banner (bool, optional): Whether to call self.dismiss_cookie_banner() if available. Defaults to False.

        Returns:
            BeautifulSoup or None: Parsed page content, or None if an error occurs.
        """
        try:
            self.driver.get(url)
            if dismiss_banner and hasattr(self, "dismiss_cookie_banner"):
                self.dismiss_cookie_banner()
            time.sleep(sleep_time)
            return BeautifulSoup(self.driver.page_source, "html.parser")
        except Exception as e:
            from crawler.src.logger import logger  # Ensure logger is imported
            logger.error(f"[{self.name}] Error fetching page {url}: {e}")
            return None

    def _collect_product_urls(self, current_list_url, sleep_time=2, link_selector=None):
        """
        Load a listing page and collect product URLs based on a CSS selector or all <a> tags.

        Args:
            current_list_url (str): The URL of the listing page.
            sleep_time (int, optional): Time to wait for the page to render. Defaults to 2.
            link_selector (str, optional): CSS selector to limit which links are considered.
                                           If None, all anchor tags are used.

        Returns:
            set: A set of normalized product URLs found on the page.
        """
        soup = self._get_page_soup(current_list_url, sleep_time=sleep_time)
        if not soup:
            return set()

        product_urls = set()
        if link_selector:
            elements = soup.select(link_selector)
            for el in elements:
                href = el.get("href")
                if href:
                    product_urls.add(normalize_url(urljoin(current_list_url, href)))
        else:
            for a in soup.find_all("a", href=True):
                product_urls.add(normalize_url(urljoin(current_list_url, a["href"])))
        return product_urls

    def quit_driver(self):
        """
        Safely quit and clean up the Selenium WebDriver session.

        This method should be explicitly called at the end of crawling operations.
        """
        self.driver.quit()
