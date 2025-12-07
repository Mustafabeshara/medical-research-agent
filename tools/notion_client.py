"""
Notion integration for saving research results.
"""

import requests
import json
from datetime import datetime
from typing import Dict, Any
import sys
sys.path.append("..")
from config import NOTION_API_KEY, NOTION_DATABASE_ID


class NotionDB:
    """Simple Notion database client for research results."""

    def __init__(self):
        self.api_key = NOTION_API_KEY
        self.database_id = NOTION_DATABASE_ID
        self.base_url = "https://api.notion.com/v1"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28"
        }

    def save_company(self, company_data: Dict[str, Any]) -> str:
        """
        Save a company to the Notion database.

        Expected company_data format:
        {
            "name": "Company Name",
            "specialty": "PICU Equipment",
            "headquarters": "City, Country",
            "products": "Product 1, Product 2",
            "website": "https://example.com",
            "ce_mark": True,
            "fda_cleared": True,
            "iso_13485": True,
            "gulf_presence": "None/Unknown",
            "distribution_model": "Distributors",
            "contact_email": "info@example.com",
            "notes": "Research notes here"
        }
        """

        properties = {
            "Company Name": {
                "title": [{"text": {"content": company_data.get("name", "Unknown")}}]
            },
            "Specialty": {
                "select": {"name": company_data.get("specialty", "Other")}
            },
            "Headquarters": {
                "rich_text": [{"text": {"content": company_data.get("headquarters", "")}}]
            },
            "Products": {
                "rich_text": [{"text": {"content": company_data.get("products", "")[:2000]}}]
            },
            "Website": {
                "url": company_data.get("website")
            },
            "CE Mark": {
                "checkbox": company_data.get("ce_mark", False)
            },
            "FDA Cleared": {
                "checkbox": company_data.get("fda_cleared", False)
            },
            "ISO 13485": {
                "checkbox": company_data.get("iso_13485", False)
            },
            "Gulf Presence": {
                "select": {"name": company_data.get("gulf_presence", "None/Unknown")}
            },
            "Distribution Model": {
                "select": {"name": company_data.get("distribution_model", "Unknown")}
            },
            "Notes": {
                "rich_text": [{"text": {"content": company_data.get("notes", "")[:2000]}}]
            },
            "Research Date": {
                "date": {"start": datetime.now().isoformat()[:10]}
            },
            "Status": {
                "select": {"name": "Researched"}
            }
        }

        # Add email if present
        if company_data.get("contact_email"):
            properties["Contact Email"] = {"email": company_data["contact_email"]}

        payload = {
            "parent": {"database_id": self.database_id},
            "properties": properties
        }

        try:
            response = requests.post(
                f"{self.base_url}/pages",
                headers=self.headers,
                json=payload
            )
            response.raise_for_status()
            result = response.json()
            return json.dumps({
                "success": True,
                "page_id": result.get("id"),
                "url": result.get("url")
            })

        except requests.exceptions.HTTPError as e:
            return json.dumps({
                "success": False,
                "error": str(e),
                "response": e.response.text if e.response else None
            })

    def query_existing(self, company_name: str) -> bool:
        """Check if a company already exists in the database."""
        payload = {
            "filter": {
                "property": "Company Name",
                "title": {"contains": company_name}
            }
        }

        try:
            response = requests.post(
                f"{self.base_url}/databases/{self.database_id}/query",
                headers=self.headers,
                json=payload
            )
            response.raise_for_status()
            results = response.json().get("results", [])
            return len(results) > 0

        except Exception:
            return False


def save_to_notion_db(company_data: Dict) -> str:
    """Wrapper function for the agent to use."""
    db = NotionDB()
    return db.save_company(company_data)


if __name__ == "__main__":
    # Test with sample data
    test_company = {
        "name": "Test Medical Co",
        "specialty": "PICU Equipment",
        "headquarters": "Boston, USA",
        "products": "Ventilators, Monitors",
        "website": "https://example.com",
        "ce_mark": True,
        "fda_cleared": True,
        "notes": "Test entry - delete me"
    }

    db = NotionDB()
    result = db.save_company(test_company)
    print(result)
