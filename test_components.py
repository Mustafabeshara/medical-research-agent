#!/usr/bin/env python3
"""
Test individual components of the Medical Research Agent.
Tests FDA API and Web Scraper (no paid API keys required).
"""

import json
import sys
sys.path.insert(0, '/Users/mustafaahmed/Documents/medical-research-agent')

from tools.fda_api import FDADatabase, check_fda_510k, get_fda_company_profile
from tools.web_scraper import CompanyScraper, scrape_company_website
from tools.competitor_mapping import map_competitors, build_market_matrix

def test_fda_api():
    """Test FDA openFDA API integration."""
    print("\n" + "="*60)
    print("🔬 TESTING FDA API (openFDA)")
    print("="*60)

    fda = FDADatabase()

    # Test 510(k) search
    print("\n1. Searching 510(k) for 'Medtronic'...")
    result = fda.search_510k(company_name="Medtronic", limit=5)

    if result.get("found"):
        print(f"   ✅ Found {result.get('total', 0)} clearances")
        for c in result.get("clearances", [])[:3]:
            print(f"      - {c.get('k_number')}: {c.get('device_name', 'N/A')[:50]}")
    else:
        print(f"   ❌ Error: {result.get('error', result.get('message'))}")

    # Test company profile
    print("\n2. Getting FDA profile for 'Philips'...")
    profile = fda.get_company_fda_profile("Philips")

    print(f"   FDA Cleared: {profile.get('fda_cleared')}")
    print(f"   Clearance Count: {profile.get('clearance_count')}")
    print(f"   Has Recalls: {profile.get('has_recalls')}")
    print(f"   FDA Registered: {profile.get('fda_registered')}")

    return True

def test_web_scraper():
    """Test website scraping."""
    print("\n" + "="*60)
    print("🌐 TESTING WEB SCRAPER")
    print("="*60)

    scraper = CompanyScraper()

    # Test with a medical device company
    test_url = "https://www.draeger.com"
    print(f"\n1. Scraping {test_url}...")

    result = scraper.scrape_company(test_url)

    if result.get("success"):
        print(f"   ✅ Company: {result.get('company_name')}")
        print(f"   Description: {result.get('description', 'N/A')[:100]}...")
        print(f"   Certifications found: {result.get('certifications', [])}")
        print(f"   Products found: {len(result.get('products', []))}")
        if result.get("contact"):
            emails = result["contact"].get("emails", [])
            print(f"   Emails found: {emails[:3] if emails else 'None'}")
    else:
        print(f"   ❌ Error: {result.get('error')}")

    return result.get("success", False)

def test_competitor_mapping():
    """Test competitor mapping."""
    print("\n" + "="*60)
    print("📊 TESTING COMPETITOR MAPPING")
    print("="*60)

    print("\n1. Mapping competitors for 'patient monitoring'...")
    result = json.loads(map_competitors("TestCompany", "patient monitoring"))

    print(f"   Market Leaders: {result.get('market_leaders', [])[:5]}")
    print(f"   Competitive Intensity: {result.get('competitive_intensity', 'N/A')[:50]}...")
    print(f"   Market Segments: {result.get('market_segments', [])}")

    return True

def main():
    print("\n" + "="*60)
    print("🧪 MEDICAL RESEARCH AGENT - COMPONENT TESTS")
    print("="*60)
    print("Testing components that don't require paid API keys...\n")

    results = {}

    # Test FDA API
    try:
        results["FDA API"] = test_fda_api()
    except Exception as e:
        print(f"   ❌ FDA API Error: {e}")
        results["FDA API"] = False

    # Test Web Scraper
    try:
        results["Web Scraper"] = test_web_scraper()
    except Exception as e:
        print(f"   ❌ Web Scraper Error: {e}")
        results["Web Scraper"] = False

    # Test Competitor Mapping
    try:
        results["Competitor Mapping"] = test_competitor_mapping()
    except Exception as e:
        print(f"   ❌ Competitor Mapping Error: {e}")
        results["Competitor Mapping"] = False

    # Summary
    print("\n" + "="*60)
    print("📋 TEST SUMMARY")
    print("="*60)
    for component, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"   {component}: {status}")

    print("\n" + "="*60)
    all_passed = all(results.values())
    if all_passed:
        print("✅ All component tests passed!")
    else:
        print("⚠️  Some tests failed - check output above")
    print("="*60 + "\n")

if __name__ == "__main__":
    main()
