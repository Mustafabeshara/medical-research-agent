#!/usr/bin/env python3
"""
Medical Research Agent with Excel Export
Researches manufacturers and populates Excel file with structured data.
"""

import anthropic
import json
import pandas as pd
from datetime import datetime
from pathlib import Path
import sys
import os
from dotenv import load_dotenv

# Add tools to path
sys.path.insert(0, str(Path(__file__).parent))

from tools.search import search_manufacturers, web_search
from tools.fda_api import get_fda_company_profile
from tools.web_scraper import scrape_company_website
from tools.competitor_mapping import map_competitors

load_dotenv()

client = anthropic.Anthropic()

# Excel file path
EXCEL_PATH = "/Users/mustafaahmed/Documents/Company_Data_Categorized/COMPANIES_ENRICHED_V2.xlsx"

# Tools for the agent
TOOLS = [
    {
        "name": "search_manufacturers",
        "description": "Search for medical equipment manufacturers in a specific specialty",
        "input_schema": {
            "type": "object",
            "properties": {
                "specialty": {"type": "string"}
            },
            "required": ["specialty"]
        }
    },
    {
        "name": "get_fda_profile",
        "description": "Get FDA clearance profile for a company",
        "input_schema": {
            "type": "object",
            "properties": {
                "company_name": {"type": "string"}
            },
            "required": ["company_name"]
        }
    },
    {
        "name": "scrape_website",
        "description": "Scrape company website for details",
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {"type": "string"}
            },
            "required": ["url"]
        }
    },
    {
        "name": "map_competitors",
        "description": "Map competitors in a specialty",
        "input_schema": {
            "type": "object",
            "properties": {
                "company_name": {"type": "string"},
                "specialty": {"type": "string"}
            },
            "required": ["company_name", "specialty"]
        }
    },
    {
        "name": "add_company_to_excel",
        "description": "Add a researched company to the Excel database",
        "input_schema": {
            "type": "object",
            "properties": {
                "company_name": {"type": "string"},
                "website": {"type": "string"},
                "specialty": {"type": "string"},
                "email": {"type": "string"},
                "phone": {"type": "string"},
                "location": {"type": "string"},
                "company_description": {"type": "string"},
                "primary_focus": {"type": "string"},
                "key_products_solutions": {"type": "string"},
                "fda_status": {"type": "string"},
                "relevance": {"type": "string", "enum": ["High", "Medium", "Low"]},
                "priority_level": {"type": "string", "enum": ["High", "Medium", "Low"]},
                "competitors": {"type": "string"},
                "notes": {"type": "string"}
            },
            "required": ["company_name", "specialty"]
        }
    }
]

SYSTEM_PROMPT = """You are a medical equipment research agent. Your job is to:

1. Search for manufacturers in the given medical specialty
2. For each promising company, gather detailed information
3. Check their FDA status
4. Add each company to the Excel database using the add_company_to_excel tool

For each company you research, use add_company_to_excel with:
- company_name: Full company name
- website: Company website URL
- specialty: The medical specialty (e.g., "PICU Equipment", "Patient Monitoring")
- email: Contact email if found
- phone: Phone number if found
- location: Headquarters location (City, Country)
- company_description: 1-2 sentence description of the company
- primary_focus: Main product area
- key_products_solutions: List of main products
- fda_status: "FDA Cleared", "CE Marked", "Both", or "Unknown"
- relevance: "High", "Medium", or "Low" for Gulf region distribution
- priority_level: "High", "Medium", or "Low" based on opportunity
- competitors: List of main competitors
- notes: Any additional notes about distribution opportunity

Focus on manufacturers (not distributors) that could be potential partners for Gulf region distribution.
Research at least 5-8 relevant companies."""


def execute_tool(name: str, input_data: dict) -> str:
    """Execute a tool and return results."""

    if name == "search_manufacturers":
        return search_manufacturers(input_data["specialty"])

    elif name == "get_fda_profile":
        return get_fda_company_profile(input_data["company_name"])

    elif name == "scrape_website":
        return scrape_company_website(input_data["url"])

    elif name == "map_competitors":
        return map_competitors(input_data["company_name"], input_data["specialty"])

    elif name == "add_company_to_excel":
        return add_to_excel(input_data)

    return json.dumps({"error": f"Unknown tool: {name}"})


def add_to_excel(company_data: dict) -> str:
    """Add a company to the Excel file."""
    try:
        # Read existing data
        if Path(EXCEL_PATH).exists():
            df = pd.read_excel(EXCEL_PATH)
        else:
            df = pd.DataFrame(columns=[
                'company_name', 'website', 'specialty', 'email', 'phone', 'location',
                'research_date', 'research_status', 'company_description', 'primary_focus',
                'key_products_solutions', 'fda_status', 'relevance', 'priority_level',
                'uniqueness', 'prevalence_of_indication', 'competitors', 'data_quality_score', 'notes'
            ])

        # Check if company already exists
        if company_data.get("company_name") in df['company_name'].values:
            return json.dumps({"status": "skipped", "reason": "Company already exists"})

        # Create new row
        new_row = {
            'company_name': company_data.get('company_name', ''),
            'website': company_data.get('website', ''),
            'specialty': company_data.get('specialty', ''),
            'email': company_data.get('email', ''),
            'phone': company_data.get('phone', ''),
            'location': company_data.get('location', ''),
            'research_date': datetime.now().strftime('%Y-%m-%d'),
            'research_status': 'Completed',
            'company_description': company_data.get('company_description', ''),
            'primary_focus': company_data.get('primary_focus', ''),
            'key_products_solutions': company_data.get('key_products_solutions', ''),
            'fda_status': company_data.get('fda_status', 'Unknown'),
            'relevance': company_data.get('relevance', 'Medium'),
            'priority_level': company_data.get('priority_level', 'Medium'),
            'uniqueness': '',
            'prevalence_of_indication': '',
            'competitors': company_data.get('competitors', ''),
            'data_quality_score': 80,
            'notes': company_data.get('notes', '')
        }

        # Append to dataframe
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)

        # Save to Excel
        df.to_excel(EXCEL_PATH, index=False)

        return json.dumps({
            "status": "success",
            "message": f"Added {company_data.get('company_name')} to Excel",
            "total_companies": len(df)
        })

    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})


def run_research(specialty: str):
    """Run research for a specialty and populate Excel."""

    print(f"\n{'='*60}")
    print(f"🔬 Medical Research Agent - Excel Export")
    print(f"📋 Specialty: {specialty}")
    print(f"📁 Output: {EXCEL_PATH}")
    print(f"📅 Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*60}\n")

    messages = [
        {
            "role": "user",
            "content": f"""Research manufacturers in the "{specialty}" medical equipment space.

Find 5-8 manufacturers that could be potential distribution partners for the Gulf region.

For EACH company you find:
1. Search for their details
2. Check their FDA profile if possible
3. Add them to the Excel database using add_company_to_excel

Make sure to actually call add_company_to_excel for each company with all available information.

Start by searching for manufacturers."""
        }
    ]

    companies_added = 0

    while True:
        try:
            response = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=4096,
                system=SYSTEM_PROMPT,
                tools=TOOLS,
                messages=messages
            )
        except Exception as e:
            print(f"API Error: {e}")
            break

        if response.stop_reason == "end_turn":
            for block in response.content:
                if hasattr(block, "text"):
                    print(f"\n📊 Summary:\n{block.text}")
            break

        if response.stop_reason == "tool_use":
            messages.append({"role": "assistant", "content": response.content})

            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    tool_name = block.name
                    tool_input = block.input

                    if tool_name == "add_company_to_excel":
                        print(f"💾 Adding: {tool_input.get('company_name', 'Unknown')}")
                        companies_added += 1
                    elif tool_name == "search_manufacturers":
                        print(f"🔍 Searching: {tool_input.get('specialty')}")
                    elif tool_name == "get_fda_profile":
                        print(f"📋 FDA check: {tool_input.get('company_name')}")
                    elif tool_name == "scrape_website":
                        print(f"🌐 Scraping: {tool_input.get('url', '')[:50]}...")

                    result = execute_tool(tool_name, tool_input)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result
                    })

            messages.append({"role": "user", "content": tool_results})

    print(f"\n{'='*60}")
    print(f"✅ Research complete!")
    print(f"📊 Companies added to Excel: {companies_added}")
    print(f"📁 File: {EXCEL_PATH}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    specialty = sys.argv[1] if len(sys.argv) > 1 else "PICU equipment"
    run_research(specialty)
