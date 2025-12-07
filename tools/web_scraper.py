"""
Web Scraper for deep company page analysis.
Extracts structured information from manufacturer websites.
"""

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import json
import re
from typing import Dict, List, Optional
import time


class CompanyScraper:
    """Scrapes manufacturer websites for detailed company information."""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5"
        })
        self.timeout = 15

    def scrape_company(self, url: str) -> Dict:
        """
        Scrape a company website for key business development information.

        Returns structured data including:
        - Company overview
        - Products/services
        - Certifications
        - Distribution info
        - Contact details
        - International presence
        """
        result = {
            "url": url,
            "success": False,
            "company_name": None,
            "description": None,
            "products": [],
            "certifications": [],
            "distribution_info": None,
            "contact": {},
            "locations": [],
            "international_presence": [],
            "raw_about": None,
            "error": None
        }

        try:
            # Get homepage
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")

            # Extract company name
            result["company_name"] = self._extract_company_name(soup, url)

            # Extract meta description
            result["description"] = self._extract_description(soup)

            # Find and scrape key pages
            links = self._find_key_pages(soup, url)

            # Scrape About page
            if links.get("about"):
                about_data = self._scrape_about_page(links["about"])
                result["raw_about"] = about_data.get("content")
                result["locations"].extend(about_data.get("locations", []))

            # Scrape Products page
            if links.get("products"):
                result["products"] = self._scrape_products_page(links["products"])

            # Scrape Contact page
            if links.get("contact"):
                result["contact"] = self._scrape_contact_page(links["contact"])

            # Look for certifications across pages
            result["certifications"] = self._find_certifications(soup, response.text)

            # Look for distribution/partner info
            if links.get("distributors") or links.get("partners"):
                dist_url = links.get("distributors") or links.get("partners")
                result["distribution_info"] = self._scrape_distribution_page(dist_url)
                result["international_presence"] = self._find_international_presence(dist_url)

            result["success"] = True

        except requests.exceptions.Timeout:
            result["error"] = "Request timed out"
        except requests.exceptions.RequestException as e:
            result["error"] = f"Request failed: {str(e)}"
        except Exception as e:
            result["error"] = f"Scraping error: {str(e)}"

        return result

    def _extract_company_name(self, soup: BeautifulSoup, url: str) -> str:
        """Extract company name from page."""
        # Try og:site_name
        og_site = soup.find("meta", property="og:site_name")
        if og_site and og_site.get("content"):
            return og_site["content"].strip()

        # Try title tag
        title = soup.find("title")
        if title:
            # Clean common suffixes
            name = title.text.strip()
            for suffix in [" | Home", " - Home", " | Official", " - Official"]:
                name = name.replace(suffix, "")
            return name.split("|")[0].split("-")[0].strip()

        # Fallback to domain
        domain = urlparse(url).netloc
        return domain.replace("www.", "").split(".")[0].title()

    def _extract_description(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract meta description."""
        meta = soup.find("meta", attrs={"name": "description"})
        if meta and meta.get("content"):
            return meta["content"].strip()

        og_desc = soup.find("meta", property="og:description")
        if og_desc and og_desc.get("content"):
            return og_desc["content"].strip()

        return None

    def _find_key_pages(self, soup: BeautifulSoup, base_url: str) -> Dict[str, str]:
        """Find URLs for key pages (About, Products, Contact, Distributors)."""
        pages = {}
        keywords = {
            "about": ["about", "about-us", "company", "who-we-are", "our-story"],
            "products": ["products", "solutions", "devices", "equipment", "portfolio"],
            "contact": ["contact", "contact-us", "get-in-touch", "reach-us"],
            "distributors": ["distributors", "distribution", "partners", "where-to-buy", "find-distributor", "international"],
            "partners": ["become-partner", "partnership", "dealer"]
        }

        for link in soup.find_all("a", href=True):
            href = link.get("href", "").lower()
            text = link.text.lower().strip()

            for page_type, kws in keywords.items():
                if page_type not in pages:
                    for kw in kws:
                        if kw in href or kw in text:
                            full_url = urljoin(base_url, link["href"])
                            if urlparse(full_url).netloc == urlparse(base_url).netloc:
                                pages[page_type] = full_url
                                break

        return pages

    def _scrape_about_page(self, url: str) -> Dict:
        """Scrape About page for company info."""
        result = {"content": "", "locations": []}

        try:
            response = self.session.get(url, timeout=self.timeout)
            soup = BeautifulSoup(response.text, "html.parser")

            # Remove nav, footer, scripts
            for tag in soup.find_all(["nav", "footer", "script", "style", "header"]):
                tag.decompose()

            # Get main content
            main = soup.find("main") or soup.find("article") or soup.find(class_=re.compile(r"content|main|about"))
            if main:
                result["content"] = main.get_text(separator=" ", strip=True)[:3000]
            else:
                result["content"] = soup.body.get_text(separator=" ", strip=True)[:3000] if soup.body else ""

            # Look for location mentions
            location_patterns = [
                r"headquartered?\s+in\s+([A-Z][a-z]+(?:,?\s+[A-Z][a-z]+)*)",
                r"based\s+in\s+([A-Z][a-z]+(?:,?\s+[A-Z][a-z]+)*)",
                r"offices?\s+in\s+([A-Z][a-z]+(?:,?\s+[A-Z][a-z]+)*)"
            ]
            for pattern in location_patterns:
                matches = re.findall(pattern, result["content"])
                result["locations"].extend(matches)

        except Exception:
            pass

        return result

    def _scrape_products_page(self, url: str) -> List[str]:
        """Scrape Products page for product names."""
        products = []

        try:
            response = self.session.get(url, timeout=self.timeout)
            soup = BeautifulSoup(response.text, "html.parser")

            # Look for product titles in common patterns
            for selector in ["h2", "h3", ".product-title", ".product-name", "[class*='product'] h2", "[class*='product'] h3"]:
                for el in soup.select(selector)[:20]:
                    text = el.get_text(strip=True)
                    if text and len(text) < 100 and text not in products:
                        products.append(text)

        except Exception:
            pass

        return products[:15]  # Limit to top 15

    def _scrape_contact_page(self, url: str) -> Dict:
        """Scrape Contact page for contact details."""
        contact = {"emails": [], "phones": [], "address": None}

        try:
            response = self.session.get(url, timeout=self.timeout)
            text = response.text

            # Find emails
            emails = re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", text)
            contact["emails"] = list(set([e for e in emails if not e.endswith((".png", ".jpg", ".gif"))]))[:5]

            # Find phone numbers
            phones = re.findall(r"[\+]?[(]?[0-9]{1,3}[)]?[-\s\.]?[(]?[0-9]{1,4}[)]?[-\s\.]?[0-9]{1,4}[-\s\.]?[0-9]{1,9}", text)
            contact["phones"] = list(set([p.strip() for p in phones if len(p) > 8]))[:5]

            # Try to find address
            soup = BeautifulSoup(text, "html.parser")
            address_el = soup.find(class_=re.compile(r"address")) or soup.find("address")
            if address_el:
                contact["address"] = address_el.get_text(separator=", ", strip=True)[:200]

        except Exception:
            pass

        return contact

    def _find_certifications(self, soup: BeautifulSoup, html: str) -> List[str]:
        """Find certification mentions in page content."""
        certifications = []

        cert_patterns = [
            (r"CE\s*[Mm]ark(?:ed)?", "CE Mark"),
            (r"FDA\s*(?:510\(?k\)?|cleared|approved|registered)", "FDA"),
            (r"ISO\s*13485", "ISO 13485"),
            (r"ISO\s*9001", "ISO 9001"),
            (r"ISO\s*14001", "ISO 14001"),
            (r"MDR\s*(?:compliant|certified)?", "EU MDR"),
            (r"GMP\s*(?:certified)?", "GMP"),
            (r"MDSAP", "MDSAP"),
            (r"TGA\s*(?:registered|approved)?", "TGA (Australia)"),
            (r"Health\s*Canada", "Health Canada"),
        ]

        for pattern, cert_name in cert_patterns:
            if re.search(pattern, html, re.IGNORECASE):
                if cert_name not in certifications:
                    certifications.append(cert_name)

        return certifications

    def _scrape_distribution_page(self, url: str) -> Optional[str]:
        """Scrape distribution/partner page for distribution model info."""
        try:
            response = self.session.get(url, timeout=self.timeout)
            soup = BeautifulSoup(response.text, "html.parser")

            # Remove nav, footer
            for tag in soup.find_all(["nav", "footer", "script", "style"]):
                tag.decompose()

            text = soup.get_text(separator=" ", strip=True)[:2000]

            # Analyze distribution model
            if any(kw in text.lower() for kw in ["become a partner", "become a distributor", "seeking distributors", "looking for partners"]):
                return "Seeking Partners"
            elif any(kw in text.lower() for kw in ["our distributors", "authorized distributors", "find a distributor"]):
                return "Uses Distributors"
            elif any(kw in text.lower() for kw in ["direct sales", "buy direct", "contact sales"]):
                return "Direct Sales"

        except Exception:
            pass

        return None

    def _find_international_presence(self, url: str) -> List[str]:
        """Find countries/regions where company has presence."""
        regions = []
        gulf_countries = ["UAE", "Saudi Arabia", "Kuwait", "Qatar", "Bahrain", "Oman", "United Arab Emirates"]

        try:
            response = self.session.get(url, timeout=self.timeout)
            text = response.text

            for country in gulf_countries:
                if country.lower() in text.lower():
                    regions.append(country)

        except Exception:
            pass

        return regions


def scrape_company_website(url: str) -> str:
    """Main function for agent to call."""
    scraper = CompanyScraper()
    result = scraper.scrape_company(url)
    return json.dumps(result, indent=2)


if __name__ == "__main__":
    # Test scraper
    test_url = "https://www.medtronic.com"
    result = scrape_company_website(test_url)
    print(result)
