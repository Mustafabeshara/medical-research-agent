"""
DuckDuckGo HTML Search Scraper - No API key required.
Uses DuckDuckGo's HTML interface which is more permissive than Google.
"""

import json
import requests
from bs4 import BeautifulSoup
from typing import List, Dict
import time
import random
from urllib.parse import quote_plus


class DuckDuckGoScraper:
    """Scrapes DuckDuckGo HTML search results."""

    def __init__(self):
        self.session = requests.Session()
        self.base_url = "https://html.duckduckgo.com/html/"

    def search(self, query: str, num_results: int = 10) -> List[Dict]:
        """Search DuckDuckGo and return results."""
        results = []

        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Referer": "https://duckduckgo.com/",
        }

        try:
            # DuckDuckGo HTML uses POST
            response = self.session.post(
                self.base_url,
                data={"q": query, "b": ""},
                headers=headers,
                timeout=15
            )
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")

            # Find result links
            for result in soup.find_all("div", class_="result"):
                try:
                    # Get title and URL
                    title_elem = result.find("a", class_="result__a")
                    if not title_elem:
                        continue

                    title = title_elem.get_text(strip=True)
                    url = title_elem.get("href", "")

                    # Skip if no valid URL
                    if not url or not url.startswith("http"):
                        continue

                    # Get description
                    desc_elem = result.find("a", class_="result__snippet")
                    desc = desc_elem.get_text(strip=True) if desc_elem else ""

                    results.append({
                        "title": title,
                        "url": url,
                        "description": desc[:300]
                    })

                    if len(results) >= num_results:
                        break

                except Exception:
                    continue

        except Exception as e:
            print(f"DuckDuckGo search error: {e}")

        return results[:num_results]


class BingHTMLScraper:
    """Fallback: Scrapes Bing HTML search results."""

    def __init__(self):
        self.session = requests.Session()

    def search(self, query: str, num_results: int = 10) -> List[Dict]:
        """Search Bing and return results."""
        results = []

        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }

        try:
            url = f"https://www.bing.com/search?q={quote_plus(query)}&count={num_results}"
            response = self.session.get(url, headers=headers, timeout=15)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")

            for li in soup.find_all("li", class_="b_algo"):
                try:
                    a = li.find("a", href=True)
                    if not a:
                        continue

                    title = a.get_text(strip=True)
                    href = a.get("href", "")

                    if not href.startswith("http"):
                        continue

                    desc_elem = li.find("p")
                    desc = desc_elem.get_text(strip=True) if desc_elem else ""

                    results.append({
                        "title": title,
                        "url": href,
                        "description": desc[:300]
                    })

                except Exception:
                    continue

        except Exception as e:
            print(f"Bing search error: {e}")

        return results[:num_results]


def web_search(query: str, max_results: int = 10) -> List[Dict]:
    """
    Search using DuckDuckGo (fallback to Bing).
    No API key needed.
    """
    # Try DuckDuckGo first
    ddg = DuckDuckGoScraper()
    results = ddg.search(query, max_results)

    # Fallback to Bing if DuckDuckGo fails
    if not results:
        print("  DuckDuckGo failed, trying Bing...")
        bing = BingHTMLScraper()
        results = bing.search(query, max_results)

    return results


def search_manufacturers(specialty: str) -> str:
    """Search for manufacturers in a medical specialty."""
    queries = [
        f"{specialty} equipment manufacturers",
        f"{specialty} medical devices companies",
        f"top {specialty} manufacturers"
    ]

    all_results = []
    seen_urls = set()

    for query in queries:
        print(f"  Searching: {query}...")
        results = web_search(query, max_results=10)
        for r in results:
            url = r.get("url", "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                all_results.append(r)
        time.sleep(random.uniform(0.5, 1))

    return json.dumps(all_results, indent=2)


brave_search = web_search


if __name__ == "__main__":
    print("Testing DuckDuckGo/Bing scraper...")
    results = web_search("PICU equipment manufacturers medical", max_results=5)
    print(f"Found {len(results)} results:")
    for r in results:
        print(f"  - {r['title'][:60]}")
        print(f"    {r['url']}")
