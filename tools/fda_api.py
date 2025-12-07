"""
FDA openFDA API Integration for 510(k) clearance lookups.
Uses the free openFDA API - no API key required (rate limited to 240 requests/minute).
https://open.fda.gov/apis/device/510k/
"""

import requests
import json
from typing import Dict, List, Optional
from datetime import datetime
import re


class FDADatabase:
    """Interface to FDA openFDA device database."""

    BASE_URL = "https://api.fda.gov/device"

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize FDA API client.
        API key is optional but increases rate limit from 240/min to 120,000/day.
        Get a key at: https://open.fda.gov/apis/authentication/
        """
        self.api_key = api_key
        self.session = requests.Session()

    def search_510k(
        self,
        company_name: Optional[str] = None,
        product_name: Optional[str] = None,
        device_class: Optional[str] = None,
        limit: int = 25
    ) -> Dict:
        """
        Search FDA 510(k) database for device clearances.

        Args:
            company_name: Manufacturer/applicant name
            product_name: Device/product name
            device_class: Device classification (1, 2, or 3)
            limit: Max results to return

        Returns:
            Dictionary with clearance results and summary
        """
        search_parts = []

        if company_name:
            # Search in applicant field
            clean_name = self._clean_search_term(company_name)
            search_parts.append(f'applicant:"{clean_name}"')

        if product_name:
            clean_product = self._clean_search_term(product_name)
            search_parts.append(f'device_name:"{clean_product}"')

        if device_class:
            search_parts.append(f'device_class:"{device_class}"')

        if not search_parts:
            return {"error": "At least one search parameter required"}

        search_query = "+AND+".join(search_parts)

        params = {
            "search": search_query,
            "limit": limit,
            "sort": "decision_date:desc"  # Most recent first
        }

        if self.api_key:
            params["api_key"] = self.api_key

        try:
            response = self.session.get(
                f"{self.BASE_URL}/510k.json",
                params=params,
                timeout=15
            )

            if response.status_code == 404:
                return {
                    "found": False,
                    "total": 0,
                    "clearances": [],
                    "message": "No 510(k) clearances found matching criteria"
                }

            response.raise_for_status()
            data = response.json()

            clearances = []
            for item in data.get("results", []):
                clearances.append({
                    "k_number": item.get("k_number"),
                    "device_name": item.get("device_name"),
                    "applicant": item.get("applicant"),
                    "decision_date": item.get("decision_date"),
                    "decision_code": item.get("decision_code"),
                    "product_code": item.get("product_code"),
                    "device_class": item.get("device_class"),
                    "review_panel": item.get("review_advisory_committee"),
                    "statement_or_summary": item.get("statement_or_summary"),
                    "clearance_type": item.get("clearance_type")
                })

            return {
                "found": True,
                "total": data.get("meta", {}).get("results", {}).get("total", len(clearances)),
                "clearances": clearances,
                "query": {
                    "company": company_name,
                    "product": product_name
                }
            }

        except requests.exceptions.HTTPError as e:
            return {"error": f"FDA API error: {str(e)}"}
        except Exception as e:
            return {"error": f"Request failed: {str(e)}"}

    def get_510k_details(self, k_number: str) -> Dict:
        """Get detailed information for a specific 510(k) number."""
        params = {
            "search": f'k_number:"{k_number}"',
            "limit": 1
        }

        if self.api_key:
            params["api_key"] = self.api_key

        try:
            response = self.session.get(
                f"{self.BASE_URL}/510k.json",
                params=params,
                timeout=15
            )
            response.raise_for_status()
            data = response.json()

            if data.get("results"):
                return {"found": True, "details": data["results"][0]}
            return {"found": False, "message": f"No clearance found for {k_number}"}

        except Exception as e:
            return {"error": str(e)}

    def search_recalls(self, company_name: str, limit: int = 10) -> Dict:
        """Search for device recalls associated with a company."""
        clean_name = self._clean_search_term(company_name)

        params = {
            "search": f'recalling_firm:"{clean_name}"',
            "limit": limit,
            "sort": "recall_initiation_date:desc"
        }

        if self.api_key:
            params["api_key"] = self.api_key

        try:
            response = self.session.get(
                f"{self.BASE_URL}/recall.json",
                params=params,
                timeout=15
            )

            if response.status_code == 404:
                return {"found": False, "recalls": [], "message": "No recalls found"}

            response.raise_for_status()
            data = response.json()

            recalls = []
            for item in data.get("results", []):
                recalls.append({
                    "recall_number": item.get("res_event_number"),
                    "product_description": item.get("product_description", "")[:200],
                    "reason": item.get("reason_for_recall", "")[:200],
                    "classification": item.get("product_res_number"),
                    "status": item.get("status"),
                    "initiation_date": item.get("recall_initiation_date")
                })

            return {
                "found": True,
                "total": data.get("meta", {}).get("results", {}).get("total", len(recalls)),
                "recalls": recalls
            }

        except Exception as e:
            return {"error": str(e)}

    def search_registrations(self, company_name: str) -> Dict:
        """Search FDA establishment registrations."""
        clean_name = self._clean_search_term(company_name)

        params = {
            "search": f'proprietor_name:"{clean_name}"',
            "limit": 10
        }

        if self.api_key:
            params["api_key"] = self.api_key

        try:
            response = self.session.get(
                f"{self.BASE_URL}/registrationlisting.json",
                params=params,
                timeout=15
            )

            if response.status_code == 404:
                return {"registered": False, "establishments": []}

            response.raise_for_status()
            data = response.json()

            establishments = []
            for item in data.get("results", []):
                establishments.append({
                    "name": item.get("establishment_type", [{}])[0].get("description") if item.get("establishment_type") else None,
                    "registration_number": item.get("registration", {}).get("registration_number"),
                    "status": item.get("registration", {}).get("status_code"),
                    "address": item.get("address_line_1"),
                    "city": item.get("city"),
                    "country": item.get("iso_country_code")
                })

            return {
                "registered": len(establishments) > 0,
                "total": data.get("meta", {}).get("results", {}).get("total", 0),
                "establishments": establishments
            }

        except Exception as e:
            return {"error": str(e)}

    def get_company_fda_profile(self, company_name: str) -> Dict:
        """
        Get comprehensive FDA profile for a company.
        Includes 510(k)s, recalls, and registrations.
        """
        profile = {
            "company": company_name,
            "fda_cleared": False,
            "clearance_count": 0,
            "recent_clearances": [],
            "has_recalls": False,
            "recall_count": 0,
            "recent_recalls": [],
            "fda_registered": False,
            "risk_notes": []
        }

        # Get 510(k) clearances
        clearances = self.search_510k(company_name=company_name, limit=10)
        if clearances.get("found"):
            profile["fda_cleared"] = True
            profile["clearance_count"] = clearances.get("total", 0)
            profile["recent_clearances"] = clearances.get("clearances", [])[:5]

        # Get recalls
        recalls = self.search_recalls(company_name, limit=5)
        if recalls.get("found") and recalls.get("recalls"):
            profile["has_recalls"] = True
            profile["recall_count"] = recalls.get("total", 0)
            profile["recent_recalls"] = recalls.get("recalls", [])
            profile["risk_notes"].append(f"Company has {recalls.get('total', 0)} recall(s) on record")

        # Get registrations
        registrations = self.search_registrations(company_name)
        if registrations.get("registered"):
            profile["fda_registered"] = True

        return profile

    def _clean_search_term(self, term: str) -> str:
        """Clean search term for FDA API."""
        # Remove special characters that might break the query
        cleaned = re.sub(r'[^\w\s\-\.]', '', term)
        return cleaned.strip()


def check_fda_510k(company_name: str, product_name: Optional[str] = None) -> str:
    """
    Main function for agent to check FDA 510(k) status.
    Returns JSON string with clearance information.
    """
    fda = FDADatabase()
    result = fda.search_510k(
        company_name=company_name,
        product_name=product_name,
        limit=15
    )
    return json.dumps(result, indent=2, default=str)


def get_fda_company_profile(company_name: str) -> str:
    """
    Get full FDA profile for a company.
    Returns JSON with clearances, recalls, and registration status.
    """
    fda = FDADatabase()
    profile = fda.get_company_fda_profile(company_name)
    return json.dumps(profile, indent=2, default=str)


if __name__ == "__main__":
    # Test FDA lookups
    print("Testing FDA API...")

    # Test 510(k) search
    print("\n--- 510(k) Search for Medtronic ---")
    result = check_fda_510k("Medtronic")
    print(result)

    # Test company profile
    print("\n--- Full FDA Profile for Philips ---")
    profile = get_fda_company_profile("Philips")
    print(profile)
