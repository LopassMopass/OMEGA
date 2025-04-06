"""
helpers.py

Utility functions for parsing and normalizing data and URLs used across crawler modules.
"""

import re
from urllib.parse import urlparse, urlunparse, urljoin

def normalize_url(url):
    """
    Normalize URL by lowercasing scheme and netloc and removing trailing slashes.

    Args:
        url (str): URL to normalize.

    Returns:
        str: Normalized URL.
    """
    parsed = urlparse(url)
    return urlunparse((parsed.scheme.lower(), parsed.netloc.lower(), parsed.path.rstrip('/'), '', '', ''))

def parse_int(value, remove_list=None):
    """
    Parse integer from string, cleaning unwanted characters.

    Args:
        value (str): String containing the number.
        remove_list (list): Optional list of strings to remove.

    Returns:
        int or None: Parsed integer, or None if parsing fails.
    """
    if not value:
        return None
    cleaned = value.lower()
    for r in (remove_list or []):
        cleaned = cleaned.replace(r, "")
    cleaned = re.sub(r'[^\d.]', '', cleaned.replace(",", "."))
    try:
        return int(float(cleaned))
    except ValueError:
        return None

def parse_float(value, remove_list=None):
    """
    Parse float from string.

    Args:
        value (str): String to parse.
        remove_list (list): Characters to remove before parsing.

    Returns:
        float or None: Parsed float or None if failed.
    """
    if not value:
        return None
    cleaned = value.lower()
    for r in (remove_list or []):
        cleaned = cleaned.replace(r, "")
    cleaned = re.sub(r'[^\d.]', '', cleaned.replace(",", "."))
    try:
        return float(cleaned)
    except ValueError:
        return None

def parse_bool(value):
    """
    Parse boolean value from string.

    Args:
        value (str): String to parse.

    Returns:
        bool: True if "ano" or "yes" in value, otherwise False.
    """
    return bool(value) and ("ano" in value.lower() or "yes" in value.lower())

def parse_str(value_text):
    """
    Trim whitespace from string.

    Args:
        value_text (str): String to trim.

    Returns:
        str: Trimmed string.
    """
    return value_text.strip()

def parse_processor_cell_text(td_value):
    """
    Extract processor model, core count description, and frequency from text.

    This method analyzes strings typically found in table cells describing CPUs,
    extracting relevant attributes: processor model, textual description of core count
    (e.g., "dvacetičtyřjádrový"), and frequency in GHz.

    Example inputs:
        - "Intel® Core™ i7-14700K (dvacetičtyřjádrový – až 5,6 GHz)"
        - "AMD Ryzen 7 5700G (osmijádrový, max 4,6 GHz)"
        - "5800 MHz"
        - "dvacetičtyřjádrový – až 5,6 GHz"

    Extraction logic:
        - model_procesoru: Entire input string if known CPU brand is detected (Intel, AMD, Ryzen, etc.).
        - pocet_jader_procesoru: The phrase ending with "jádrový" or "jader" exactly as in input.
        - frekvence_procesoru: Numeric frequency extracted and normalized to GHz.

    Args:
        td_value (str): Raw text from a CPU description table cell.

    Returns:
        tuple:
            - cpu_model (str or None): Complete CPU model description if brand detected, else None.
            - pocet_jader_str (str or None): Core count description (original language), else None.
            - freq_ghz (float or None): CPU frequency normalized to GHz, else None.
    """
    text = td_value.strip()
    text_lower = text.lower()

    known_cpu_brands = ["intel", "amd", "apple", "ryzen", "core", "m1", "m2", "m4"]
    if any(brand in text_lower for brand in known_cpu_brands):
        cpu_model = text  # store entire text as model
    else:
        cpu_model = None

    pocet_jader_str = None
    m_cores = re.search(r"\b([\wá-ž]+jádrový|[\wá-ž]+jader)\b", text_lower)
    if m_cores:
        start_idx = m_cores.start()
        end_idx = m_cores.end()
        pocet_jader_str = text[start_idx:end_idx]

    freq_ghz = None

    m_ghz = re.search(r"(\d+(?:[.,]\d+)?)\s*ghz", text_lower)
    if m_ghz:
        freq_ghz = parse_float(m_ghz.group(1))
    else:
        m_mhz = re.search(r"(\d+(?:[.,]\d+)?)\s*mhz", text_lower)
        if m_mhz:
            mhz_val = parse_float(m_mhz.group(1))
            if mhz_val:
                freq_ghz = mhz_val / 1000.0

    return cpu_model, pocet_jader_str, freq_ghz


def extract_attributes_from_property_tables(soup):
    """
    Parse detailed product attributes from structured property tables in HTML content.

    This method scans HTML elements with class "product-property-table" to extract
    specific desktop computer attributes, storing them into a standardized dictionary.

    Extracted attributes include:
        - CPU details (model, core count, frequency)
        - Graphics card details (model, memory)
        - Storage details (capacity, type)
        - RAM size
        - Power supply ("zdroj")
        - Computer form factor ("provedeni_pocitace")
        - Operating system ("operacni_system")
        - Brand ("znacka")
        - Product price ("price")

    Special parsing logic:
        - Processor details invoke `parse_processor_cell_text()` for extraction.
        - Numeric fields (e.g., storage capacity, RAM size) are parsed into integers.

    Args:
        soup (BeautifulSoup): Parsed HTML content of a product page.

    Returns:
        dict: Dictionary with product attributes populated, keys include:
            - model_procesoru (str or None)
            - pocet_jader_procesoru (str or None)
            - frekvence_procesoru (float or None)
            - model_graficke_karty (str or None)
            - pamet_graficke_karty (int or None)
            - kapacita_uloziste (int or None)
            - typ_uloziste (str or None)
            - velikost_ram (int or None)
            - zdroj (int or None)
            - provedeni_pocitace (str or None)
            - operacni_system (str or None)
            - znacka (str or None)
            - price (int or None)
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
        "price": None
    }

    param_map = {
        "grafická karta": ("model_graficke_karty", str.strip),
        "velikost paměti vga": ("pamet_graficke_karty", parse_int),
        "typ úložiště": ("typ_uloziste", str.strip),
        "kapacita úložiště": ("kapacita_uloziste", parse_int),
        "velikost paměti ram": ("velikost_ram", parse_int),
        "zdroj": ("zdroj", parse_int),
        "provedení počítače": ("provedeni_pocitace", str.strip),
        "operační systém": ("operacni_system", str.strip),
        "značky": ("znacka", str.strip),
    }

    for table_div in soup.find_all("div", class_="product-property-table"):
        for row in table_div.find_all("tr"):
            th = row.find("th")
            td = row.find("td")
            if not th or not td:
                continue

            span = th.find("span")
            if span and span.get("title"):
                name_text = span["title"].strip().lower()
            else:
                name_text = th.get_text(strip=True).lower()

            raw_value = td.get_text(strip=True)

            if "procesor" in name_text:
                cpu_model, cpu_cores_str, cpu_freq = parse_processor_cell_text(raw_value)
                if cpu_model:
                    data["model_procesoru"] = cpu_model
                if cpu_cores_str:
                    data["pocet_jader_procesoru"] = cpu_cores_str  # store as string
                if cpu_freq is not None:
                    data["frekvence_procesoru"] = cpu_freq
                continue

            if "počet jader" in name_text:
                data["pocet_jader_procesoru"] = raw_value
                continue

            if "frekvence procesoru" in name_text:
                data["frekvence_procesoru"] = raw_value
                continue

            for label, (data_key, parser_func) in param_map.items():
                if label in name_text:
                    data[data_key] = parser_func(raw_value)
                    break

    price_div = soup.find("div", class_="product-price")
    if price_div:
        raw_price = price_div.get("data-price-value")
        if raw_price:
            try:
                data["price"] = int(raw_price.strip())
            except ValueError:
                pass

    return data

def get_planeo_next_page_url(current_list_url, soup):
    """
    Retrieve the next pagination URL from Planeo.cz product listings.

    This method identifies the pagination control (specifically the "next page" arrow button)
    in Planeo.cz's HTML structure. It constructs and returns an absolute URL to the subsequent
    product listing page.

    HTML example considered:
        <a href="/pocitace?offset=24"
           class="c-pagination__page--arrow js-product-filter-paging"></a>

    Args:
        current_list_url (str): URL of the current listing page.
        soup (BeautifulSoup): Parsed HTML content of the current listing page.

    Returns:
        str or None: Absolute URL of the next listing page if available; otherwise None.
    """
    next_arrow = soup.find("a", class_="c-pagination__page--arrow js-product-filter-paging")
    if next_arrow and next_arrow.has_attr("href"):
        next_href = next_arrow["href"]
        full_next_url = urljoin(current_list_url, next_href)
        return full_next_url
    return None
