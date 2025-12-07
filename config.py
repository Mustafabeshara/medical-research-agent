"""
Configuration for Medical Research Agent
Fill in your API keys and Notion database ID.
"""

import os

# API Keys (use environment variables in production)
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "your-key-here")
BRAVE_API_KEY = os.getenv("BRAVE_API_KEY", "your-key-here")
NOTION_API_KEY = os.getenv("NOTION_API_KEY", "your-key-here")

# Notion Database Configuration
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID", "your-database-id")

# Notion database schema - create a database with these properties:
NOTION_SCHEMA = {
    "Company Name": "title",
    "Specialty": "select",
    "Headquarters": "rich_text",
    "Products": "rich_text",
    "Website": "url",
    "CE Mark": "checkbox",
    "FDA Cleared": "checkbox",
    "ISO 13485": "checkbox",
    "Gulf Presence": "select",  # Options: "Has Distributor", "Direct Office", "None/Unknown"
    "Distribution Model": "select",  # Options: "Direct", "Distributors", "Seeking Partners"
    "Contact Email": "email",
    "Notes": "rich_text",
    "Research Date": "date",
    "Status": "select"  # Options: "Researched", "To Contact", "In Discussion", "Not Fit"
}

# Research settings
MAX_COMPANIES_PER_SEARCH = 10
SEARCH_QUERIES_PER_SPECIALTY = [
    "{specialty} equipment manufacturers",
    "{specialty} medical devices companies",
    "top {specialty} manufacturers medical",
    "{specialty} equipment CE marked",
    "{specialty} devices FDA cleared"
]
