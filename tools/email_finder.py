"""
Email Finder Integration using Hunter.io and Apollo.io APIs.
Finds business contact emails for outreach.
"""

import requests
import json
from typing import Dict, List, Optional
from urllib.parse import urlparse
import os


class HunterIO:
    """Hunter.io API client for email discovery."""

    BASE_URL = "https://api.hunter.io/v2"

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Hunter.io client.
        Get API key at: https://hunter.io/api-keys
        Free tier: 25 searches/month
        """
        self.api_key = api_key or os.getenv("HUNTER_API_KEY")
        if not self.api_key:
            raise ValueError("Hunter.io API key required")

    def domain_search(self, domain: str, limit: int = 10) -> Dict:
        """
        Find all emails associated with a domain.

        Args:
            domain: Company domain (e.g., "medtronic.com")
            limit: Max emails to return

        Returns:
            Dictionary with emails and patterns found
        """
        params = {
            "domain": domain,
            "api_key": self.api_key,
            "limit": limit
        }

        try:
            response = requests.get(
                f"{self.BASE_URL}/domain-search",
                params=params,
                timeout=15
            )
            response.raise_for_status()
            data = response.json().get("data", {})

            emails = []
            for email_data in data.get("emails", []):
                emails.append({
                    "email": email_data.get("value"),
                    "type": email_data.get("type"),  # personal, generic
                    "confidence": email_data.get("confidence"),
                    "first_name": email_data.get("first_name"),
                    "last_name": email_data.get("last_name"),
                    "position": email_data.get("position"),
                    "department": email_data.get("department"),
                    "linkedin": email_data.get("linkedin")
                })

            return {
                "success": True,
                "domain": domain,
                "organization": data.get("organization"),
                "pattern": data.get("pattern"),  # Email pattern like {first}.{last}
                "emails_found": len(emails),
                "emails": emails,
                "departments": self._extract_departments(emails)
            }

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                return {"success": False, "error": "Invalid API key"}
            elif e.response.status_code == 429:
                return {"success": False, "error": "Rate limit exceeded"}
            return {"success": False, "error": str(e)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def email_finder(
        self,
        domain: str,
        first_name: str = None,
        last_name: str = None,
        full_name: str = None
    ) -> Dict:
        """
        Find email for a specific person at a company.

        Args:
            domain: Company domain
            first_name: Person's first name
            last_name: Person's last name
            full_name: Full name (alternative to first/last)

        Returns:
            Dictionary with found email and confidence
        """
        params = {
            "domain": domain,
            "api_key": self.api_key
        }

        if full_name:
            params["full_name"] = full_name
        else:
            if first_name:
                params["first_name"] = first_name
            if last_name:
                params["last_name"] = last_name

        try:
            response = requests.get(
                f"{self.BASE_URL}/email-finder",
                params=params,
                timeout=15
            )
            response.raise_for_status()
            data = response.json().get("data", {})

            return {
                "success": True,
                "email": data.get("email"),
                "score": data.get("score"),  # Confidence 0-100
                "domain": domain,
                "sources": data.get("sources", [])
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def email_verifier(self, email: str) -> Dict:
        """
        Verify if an email address is valid and deliverable.

        Args:
            email: Email address to verify

        Returns:
            Verification result with status
        """
        params = {
            "email": email,
            "api_key": self.api_key
        }

        try:
            response = requests.get(
                f"{self.BASE_URL}/email-verifier",
                params=params,
                timeout=15
            )
            response.raise_for_status()
            data = response.json().get("data", {})

            return {
                "success": True,
                "email": email,
                "status": data.get("status"),  # valid, invalid, accept_all, unknown
                "result": data.get("result"),
                "score": data.get("score"),
                "disposable": data.get("disposable"),
                "webmail": data.get("webmail")
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _extract_departments(self, emails: List[Dict]) -> Dict:
        """Group emails by department."""
        departments = {}
        for email in emails:
            dept = email.get("department") or "Unknown"
            if dept not in departments:
                departments[dept] = []
            departments[dept].append(email.get("email"))
        return departments


class ApolloIO:
    """Apollo.io API client for contact enrichment."""

    BASE_URL = "https://api.apollo.io/v1"

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Apollo.io client.
        Get API key at: https://app.apollo.io/#/settings/integrations/api
        """
        self.api_key = api_key or os.getenv("APOLLO_API_KEY")

    def search_contacts(
        self,
        domain: str,
        titles: List[str] = None,
        limit: int = 10
    ) -> Dict:
        """
        Search for contacts at a company.

        Args:
            domain: Company domain
            titles: Job titles to filter by (e.g., ["VP Sales", "Director"])
            limit: Max results

        Returns:
            Dictionary with contact information
        """
        if not self.api_key:
            return {"success": False, "error": "Apollo API key required"}

        # Default titles for business development targeting
        if titles is None:
            titles = [
                "VP Sales", "Director Sales", "Business Development",
                "VP International", "Director International",
                "Managing Director", "General Manager",
                "VP Marketing", "Director Marketing"
            ]

        payload = {
            "api_key": self.api_key,
            "q_organization_domains": domain,
            "person_titles": titles,
            "per_page": limit
        }

        try:
            response = requests.post(
                f"{self.BASE_URL}/mixed_people/search",
                json=payload,
                timeout=15
            )
            response.raise_for_status()
            data = response.json()

            contacts = []
            for person in data.get("people", []):
                contacts.append({
                    "name": person.get("name"),
                    "title": person.get("title"),
                    "email": person.get("email"),
                    "email_status": person.get("email_status"),
                    "linkedin_url": person.get("linkedin_url"),
                    "city": person.get("city"),
                    "country": person.get("country"),
                    "company": person.get("organization", {}).get("name")
                })

            return {
                "success": True,
                "domain": domain,
                "contacts_found": len(contacts),
                "contacts": contacts
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def enrich_company(self, domain: str) -> Dict:
        """
        Get enriched company information.

        Args:
            domain: Company domain

        Returns:
            Enriched company data
        """
        if not self.api_key:
            return {"success": False, "error": "Apollo API key required"}

        payload = {
            "api_key": self.api_key,
            "domain": domain
        }

        try:
            response = requests.post(
                f"{self.BASE_URL}/organizations/enrich",
                json=payload,
                timeout=15
            )
            response.raise_for_status()
            data = response.json().get("organization", {})

            return {
                "success": True,
                "name": data.get("name"),
                "domain": domain,
                "industry": data.get("industry"),
                "estimated_employees": data.get("estimated_num_employees"),
                "annual_revenue": data.get("annual_revenue_printed"),
                "founded_year": data.get("founded_year"),
                "linkedin_url": data.get("linkedin_url"),
                "location": {
                    "city": data.get("city"),
                    "state": data.get("state"),
                    "country": data.get("country")
                },
                "technologies": data.get("technologies", [])[:10],
                "keywords": data.get("keywords", [])[:10]
            }

        except Exception as e:
            return {"success": False, "error": str(e)}


class EmailFinder:
    """
    Unified email finder that tries multiple sources.
    Falls back gracefully if APIs are not configured.
    """

    def __init__(self):
        self.hunter = None
        self.apollo = None

        # Try to initialize available services
        try:
            if os.getenv("HUNTER_API_KEY"):
                self.hunter = HunterIO()
        except:
            pass

        try:
            if os.getenv("APOLLO_API_KEY"):
                self.apollo = ApolloIO()
        except:
            pass

    def find_contacts(
        self,
        website: str,
        target_roles: List[str] = None
    ) -> Dict:
        """
        Find business contacts for a company.

        Args:
            website: Company website URL
            target_roles: Specific roles to target

        Returns:
            Combined results from available sources
        """
        # Extract domain from URL
        domain = self._extract_domain(website)

        result = {
            "domain": domain,
            "sources_checked": [],
            "contacts": [],
            "email_pattern": None,
            "generic_emails": []
        }

        # Default target roles for medical device BD
        if target_roles is None:
            target_roles = [
                "VP Sales", "Director Business Development",
                "VP International", "Export Manager",
                "Managing Director EMEA", "Regional Manager Middle East"
            ]

        # Try Hunter.io first
        if self.hunter:
            try:
                hunter_result = self.hunter.domain_search(domain, limit=15)
                result["sources_checked"].append("hunter.io")

                if hunter_result.get("success"):
                    result["email_pattern"] = hunter_result.get("pattern")

                    for email in hunter_result.get("emails", []):
                        if email.get("type") == "generic":
                            result["generic_emails"].append(email.get("email"))
                        else:
                            result["contacts"].append({
                                "name": f"{email.get('first_name', '')} {email.get('last_name', '')}".strip(),
                                "email": email.get("email"),
                                "title": email.get("position"),
                                "department": email.get("department"),
                                "confidence": email.get("confidence"),
                                "linkedin": email.get("linkedin"),
                                "source": "hunter.io"
                            })
            except Exception as e:
                result["hunter_error"] = str(e)

        # Try Apollo.io
        if self.apollo:
            try:
                apollo_result = self.apollo.search_contacts(domain, target_roles, limit=10)
                result["sources_checked"].append("apollo.io")

                if apollo_result.get("success"):
                    for contact in apollo_result.get("contacts", []):
                        # Avoid duplicates
                        existing_emails = [c.get("email") for c in result["contacts"]]
                        if contact.get("email") and contact.get("email") not in existing_emails:
                            result["contacts"].append({
                                "name": contact.get("name"),
                                "email": contact.get("email"),
                                "title": contact.get("title"),
                                "linkedin": contact.get("linkedin_url"),
                                "location": contact.get("country"),
                                "source": "apollo.io"
                            })
            except Exception as e:
                result["apollo_error"] = str(e)

        # Suggest emails based on pattern if we have it
        if result["email_pattern"] and not result["contacts"]:
            result["suggested_emails"] = self._suggest_emails(
                domain,
                result["email_pattern"],
                target_roles
            )

        result["total_contacts"] = len(result["contacts"])
        return result

    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL."""
        if not url.startswith(("http://", "https://")):
            url = "https://" + url

        parsed = urlparse(url)
        domain = parsed.netloc or parsed.path
        domain = domain.replace("www.", "")
        return domain.split("/")[0]

    def _suggest_emails(
        self,
        domain: str,
        pattern: str,
        roles: List[str]
    ) -> List[Dict]:
        """
        Suggest likely emails based on discovered pattern.
        Common patterns: {first}.{last}, {f}{last}, {first}_{last}
        """
        suggestions = []

        # Common generic emails to try
        generic = [
            f"info@{domain}",
            f"sales@{domain}",
            f"contact@{domain}",
            f"export@{domain}",
            f"international@{domain}",
            f"bd@{domain}",
            f"partnerships@{domain}"
        ]

        for email in generic:
            suggestions.append({
                "email": email,
                "type": "generic",
                "confidence": "medium"
            })

        return suggestions


def find_company_contacts(website: str, target_roles: List[str] = None) -> str:
    """
    Main function for agent to find company contacts.
    Returns JSON with contact information.
    """
    finder = EmailFinder()
    result = finder.find_contacts(website, target_roles)
    return json.dumps(result, indent=2)


def verify_email(email: str) -> str:
    """
    Verify if an email is valid.
    Returns JSON with verification result.
    """
    try:
        hunter = HunterIO()
        result = hunter.email_verifier(email)
        return json.dumps(result, indent=2)
    except ValueError:
        return json.dumps({"error": "Hunter.io API key required for email verification"})


if __name__ == "__main__":
    # Test (requires API keys)
    print("Testing Email Finder...")

    if os.getenv("HUNTER_API_KEY"):
        result = find_company_contacts("medtronic.com")
        print(result)
    else:
        print("Set HUNTER_API_KEY to test email finder")

    # Show what the output would look like
    sample_output = {
        "domain": "example-medical.com",
        "sources_checked": ["hunter.io"],
        "contacts": [
            {
                "name": "John Smith",
                "email": "john.smith@example-medical.com",
                "title": "VP Sales",
                "department": "Sales",
                "confidence": 95,
                "source": "hunter.io"
            }
        ],
        "email_pattern": "{first}.{last}",
        "generic_emails": ["info@example-medical.com", "sales@example-medical.com"],
        "total_contacts": 1
    }
    print("\n--- Sample Output Format ---")
    print(json.dumps(sample_output, indent=2))
