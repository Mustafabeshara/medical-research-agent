"""
Competitor Mapping and Market Positioning Analysis.
Identifies competitors, market segments, and positioning for medical device companies.
"""

import json
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
import requests


@dataclass
class CompetitorProfile:
    """Structured competitor information."""
    name: str
    website: Optional[str] = None
    specialty_overlap: List[str] = None
    market_position: str = "Unknown"  # Leader, Challenger, Niche, Emerging
    estimated_size: str = "Unknown"  # Enterprise, Mid-Market, SMB, Startup
    key_products: List[str] = None
    geographic_focus: List[str] = None
    strengths: List[str] = None
    weaknesses: List[str] = None
    competitive_threat: str = "Medium"  # High, Medium, Low


class CompetitorAnalyzer:
    """Analyzes competitive landscape for medical device companies."""

    # Known major players by specialty (reference data)
    MAJOR_PLAYERS = {
        "patient monitoring": ["Philips", "GE Healthcare", "Medtronic", "Nihon Kohden", "Mindray", "Dräger"],
        "ventilators": ["Medtronic", "Philips", "GE Healthcare", "Dräger", "Hamilton Medical", "Getinge"],
        "infusion pumps": ["BD", "Baxter", "B. Braun", "ICU Medical", "Fresenius Kabi", "Smiths Medical"],
        "defibrillators": ["Philips", "Stryker", "Physio-Control", "ZOLL", "Nihon Kohden", "Cardiac Science"],
        "imaging": ["Siemens Healthineers", "GE Healthcare", "Philips", "Canon Medical", "Fujifilm", "Hologic"],
        "ultrasound": ["GE Healthcare", "Philips", "Siemens", "Canon Medical", "Fujifilm", "Mindray"],
        "surgical equipment": ["Stryker", "Medtronic", "Johnson & Johnson", "Zimmer Biomet", "Smith & Nephew"],
        "interventional radiology": ["Siemens", "Philips", "GE Healthcare", "Boston Scientific", "Cook Medical"],
        "picu": ["Philips", "GE Healthcare", "Dräger", "Nihon Kohden", "Mindray"],
        "nicu": ["Dräger", "GE Healthcare", "Philips", "Atom Medical", "Fanem"],
        "anesthesia": ["Dräger", "GE Healthcare", "Mindray", "Penlon", "Spacelabs"],
        "laboratory": ["Roche", "Abbott", "Siemens Healthineers", "Beckman Coulter", "Sysmex"]
    }

    # Company size indicators
    SIZE_INDICATORS = {
        "enterprise": ["Fortune 500", "global leader", "billion revenue", "worldwide presence", "multinational"],
        "mid_market": ["regional leader", "hundreds of millions", "multiple countries", "established"],
        "smb": ["specialized", "focused", "regional", "growing"],
        "startup": ["innovative", "disrupting", "founded in 20", "series", "venture"]
    }

    def __init__(self, search_func=None):
        """
        Initialize analyzer.

        Args:
            search_func: Optional function to search for additional competitor info
        """
        self.search_func = search_func

    def identify_competitors(
        self,
        company_name: str,
        specialty: str,
        products: List[str] = None
    ) -> Dict:
        """
        Identify competitors for a company in a given specialty.

        Returns competitive landscape analysis.
        """
        specialty_lower = specialty.lower()

        # Find relevant major players
        major_competitors = []
        for key, players in self.MAJOR_PLAYERS.items():
            if key in specialty_lower or specialty_lower in key:
                for player in players:
                    if player.lower() != company_name.lower():
                        major_competitors.append(player)

        # Remove duplicates
        major_competitors = list(set(major_competitors))

        # Build competitive landscape
        landscape = {
            "company": company_name,
            "specialty": specialty,
            "analyzed_at": datetime.now().isoformat(),
            "market_leaders": major_competitors[:5],
            "total_identified": len(major_competitors),
            "competitive_intensity": self._assess_intensity(len(major_competitors)),
            "market_segments": self._identify_segments(specialty),
            "positioning_opportunities": self._find_opportunities(specialty),
            "gulf_market_notes": self._gulf_market_notes(specialty)
        }

        return landscape

    def compare_companies(
        self,
        company_a: Dict,
        company_b: Dict
    ) -> Dict:
        """
        Compare two companies for competitive analysis.

        Args:
            company_a: First company data (from research)
            company_b: Second company data

        Returns comparison analysis.
        """
        comparison = {
            "companies": [company_a.get("name"), company_b.get("name")],
            "comparison_date": datetime.now().isoformat(),
            "dimensions": {}
        }

        # Compare certifications
        a_certs = set(company_a.get("certifications", []))
        b_certs = set(company_b.get("certifications", []))
        comparison["dimensions"]["certifications"] = {
            company_a.get("name"): list(a_certs),
            company_b.get("name"): list(b_certs),
            "shared": list(a_certs & b_certs),
            "advantage": company_a.get("name") if len(a_certs) > len(b_certs) else company_b.get("name")
        }

        # Compare Gulf presence
        a_gulf = company_a.get("gulf_presence", "None")
        b_gulf = company_b.get("gulf_presence", "None")
        comparison["dimensions"]["gulf_presence"] = {
            company_a.get("name"): a_gulf,
            company_b.get("name"): b_gulf
        }

        # Product overlap (if available)
        a_products = set(company_a.get("products", []))
        b_products = set(company_b.get("products", []))
        if a_products or b_products:
            comparison["dimensions"]["product_overlap"] = {
                "unique_to_a": list(a_products - b_products)[:5],
                "unique_to_b": list(b_products - a_products)[:5],
                "overlap_score": len(a_products & b_products) / max(len(a_products | b_products), 1)
            }

        return comparison

    def build_competitive_matrix(
        self,
        companies: List[Dict],
        specialty: str
    ) -> Dict:
        """
        Build a competitive matrix for multiple companies.

        Args:
            companies: List of company data dictionaries
            specialty: Market specialty

        Returns matrix with rankings and comparisons.
        """
        matrix = {
            "specialty": specialty,
            "companies_analyzed": len(companies),
            "generated_at": datetime.now().isoformat(),
            "rankings": {
                "by_certifications": [],
                "by_gulf_opportunity": [],
                "by_product_breadth": []
            },
            "matrix": [],
            "recommendations": []
        }

        # Score each company
        scored = []
        for company in companies:
            score = {
                "name": company.get("name"),
                "cert_score": len(company.get("certifications", [])),
                "gulf_score": 0 if company.get("gulf_presence") in ["Has Distributor", "Direct Office"] else 1,
                "product_score": len(company.get("products", [])),
                "total_score": 0
            }
            score["total_score"] = score["cert_score"] + score["gulf_score"] * 2 + min(score["product_score"], 5)
            scored.append(score)

        # Sort by different criteria
        matrix["rankings"]["by_certifications"] = [
            s["name"] for s in sorted(scored, key=lambda x: x["cert_score"], reverse=True)
        ]
        matrix["rankings"]["by_gulf_opportunity"] = [
            s["name"] for s in sorted(scored, key=lambda x: x["gulf_score"], reverse=True)
        ]
        matrix["rankings"]["by_product_breadth"] = [
            s["name"] for s in sorted(scored, key=lambda x: x["product_score"], reverse=True)
        ]

        # Build matrix rows
        for s in sorted(scored, key=lambda x: x["total_score"], reverse=True):
            matrix["matrix"].append({
                "company": s["name"],
                "certifications": s["cert_score"],
                "gulf_opportunity": "High" if s["gulf_score"] == 1 else "Low",
                "product_breadth": s["product_score"],
                "overall_score": s["total_score"]
            })

        # Top recommendations
        top_companies = sorted(scored, key=lambda x: x["total_score"], reverse=True)[:3]
        for company in top_companies:
            matrix["recommendations"].append({
                "company": company["name"],
                "rationale": f"Score: {company['total_score']} - " +
                           ("No Gulf presence" if company["gulf_score"] == 1 else "Established market")
            })

        return matrix

    def _assess_intensity(self, num_competitors: int) -> str:
        """Assess competitive intensity based on number of major players."""
        if num_competitors >= 6:
            return "High - Crowded market with many established players"
        elif num_competitors >= 3:
            return "Medium - Competitive but room for differentiation"
        else:
            return "Low - Limited competition, opportunity for market entry"

    def _identify_segments(self, specialty: str) -> List[str]:
        """Identify market segments within a specialty."""
        segments = {
            "patient monitoring": ["Bedside monitors", "Central stations", "Wearables", "Telemetry"],
            "ventilators": ["ICU ventilators", "Transport ventilators", "Home care", "Neonatal"],
            "imaging": ["CT", "MRI", "X-ray", "Mobile imaging"],
            "ultrasound": ["General imaging", "Cardiac", "Point-of-care", "OB/GYN"],
            "surgical": ["Instruments", "Electrosurgery", "Navigation", "Robotics"]
        }

        for key, segs in segments.items():
            if key in specialty.lower():
                return segs

        return ["Core products", "Accessories", "Software/Services"]

    def _find_opportunities(self, specialty: str) -> List[str]:
        """Identify positioning opportunities in the market."""
        return [
            "Price-competitive alternative to major brands",
            "Specialized features for emerging markets",
            "Bundled service and support packages",
            "Local regulatory expertise and support",
            "Training and education programs",
            "Flexible financing options"
        ]

    def _gulf_market_notes(self, specialty: str) -> List[str]:
        """Provide Gulf-specific market notes."""
        return [
            "Saudi Vision 2030 driving healthcare investment",
            "UAE positioning as regional medical tourism hub",
            "MOH and DOH tender requirements vary by emirate/country",
            "Arabic language support often required for public sector",
            "Local partner registration typically required for tender participation",
            "Growing demand for connected/smart medical devices"
        ]


def map_competitors(company_name: str, specialty: str, products: List[str] = None) -> str:
    """
    Main function for agent to map competitors.
    Returns JSON with competitive landscape analysis.
    """
    analyzer = CompetitorAnalyzer()
    result = analyzer.identify_competitors(company_name, specialty, products)
    return json.dumps(result, indent=2, default=str)


def build_market_matrix(companies: List[Dict], specialty: str) -> str:
    """
    Build competitive matrix for multiple researched companies.
    Returns JSON with rankings and recommendations.
    """
    analyzer = CompetitorAnalyzer()
    matrix = analyzer.build_competitive_matrix(companies, specialty)
    return json.dumps(matrix, indent=2, default=str)


if __name__ == "__main__":
    # Test competitor mapping
    print("Testing Competitor Mapping...")

    result = map_competitors("Mindray", "patient monitoring")
    print(result)

    # Test matrix
    test_companies = [
        {"name": "Company A", "certifications": ["CE Mark", "FDA"], "gulf_presence": "None", "products": ["Monitor 1", "Monitor 2"]},
        {"name": "Company B", "certifications": ["CE Mark"], "gulf_presence": "Has Distributor", "products": ["Device X"]},
        {"name": "Company C", "certifications": ["CE Mark", "FDA", "ISO 13485"], "gulf_presence": "None", "products": ["Product 1", "Product 2", "Product 3"]}
    ]

    matrix = build_market_matrix(test_companies, "patient monitoring")
    print("\n--- Competitive Matrix ---")
    print(matrix)
