"""
Medical Research Agent Tools Package.
All tools for manufacturer research and business development.
"""

from .search import brave_search, search_manufacturers
from .notion_client import NotionDB, save_to_notion_db
from .web_scraper import CompanyScraper, scrape_company_website
from .fda_api import FDADatabase, check_fda_510k, get_fda_company_profile
from .competitor_mapping import CompetitorAnalyzer, map_competitors, build_market_matrix
from .email_finder import EmailFinder, HunterIO, find_company_contacts

__all__ = [
    # Search
    "brave_search",
    "search_manufacturers",

    # Notion
    "NotionDB",
    "save_to_notion_db",

    # Web Scraping
    "CompanyScraper",
    "scrape_company_website",

    # FDA
    "FDADatabase",
    "check_fda_510k",
    "get_fda_company_profile",

    # Competitors
    "CompetitorAnalyzer",
    "map_competitors",
    "build_market_matrix",

    # Email
    "EmailFinder",
    "HunterIO",
    "find_company_contacts"
]
