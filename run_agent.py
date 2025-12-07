#!/usr/bin/env python3
"""
Medical Company Research Agent - Main Entry Point
Run: python run_agent.py "PICU equipment"
"""

import anthropic
import json
import sys
from datetime import datetime
from dotenv import load_dotenv

from tools.search import search_manufacturers, brave_search
from tools.notion_client import save_to_notion_db, NotionDB
from config import ANTHROPIC_API_KEY

load_dotenv()

client = anthropic.Anthropic()

# Agent tools definition
TOOLS = [
    {
        "name": "search_manufacturers",
        "description": "Search for medical equipment manufacturers in a specific specialty. Returns list of companies with URLs and descriptions.",
        "input_schema": {
            "type": "object",
            "properties": {
                "specialty": {
                    "type": "string",
                    "description": "Medical specialty to search for (e.g., 'PICU equipment', 'interventional radiology')"
                }
            },
            "required": ["specialty"]
        }
    },
    {
        "name": "search_company_details",
        "description": "Search for specific details about a company",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Specific search query about a company"
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "check_fda_status",
        "description": "Search for FDA 510(k) clearances for a company or product",
        "input_schema": {
            "type": "object",
            "properties": {
                "company_name": {"type": "string"},
                "product_name": {"type": "string", "description": "Optional specific product"}
            },
            "required": ["company_name"]
        }
    },
    {
        "name": "save_company",
        "description": "Save researched company data to Notion database",
        "input_schema": {
            "type": "object",
            "properties": {
                "company_data": {
                    "type": "object",
                    "description": "Structured company information",
                    "properties": {
                        "name": {"type": "string"},
                        "specialty": {"type": "string"},
                        "headquarters": {"type": "string"},
                        "products": {"type": "string"},
                        "website": {"type": "string"},
                        "ce_mark": {"type": "boolean"},
                        "fda_cleared": {"type": "boolean"},
                        "iso_13485": {"type": "boolean"},
                        "gulf_presence": {"type": "string", "enum": ["Has Distributor", "Direct Office", "None/Unknown"]},
                        "distribution_model": {"type": "string", "enum": ["Direct", "Distributors", "Seeking Partners", "Unknown"]},
                        "contact_email": {"type": "string"},
                        "notes": {"type": "string"}
                    },
                    "required": ["name", "specialty"]
                }
            },
            "required": ["company_data"]
        }
    }
]

SYSTEM_PROMPT = """You are a medical equipment research agent for a business development team
focused on finding manufacturer partners for Gulf region distribution.

Your research process:
1. Search for manufacturers in the given specialty
2. For each promising company, gather:
   - Company name and headquarters
   - Main products in the specialty
   - Certifications (CE Mark, FDA 510(k), ISO 13485)
   - Distribution model (direct sales, uses distributors, seeking partners)
   - Current Gulf region presence (existing distributors, offices, or none)
   - Website and contact info
3. Save each researched company to Notion

Focus on MANUFACTURERS, not distributors or resellers.
Prioritize companies that:
- Have CE Mark (required for Gulf markets)
- Don't have existing Gulf region distributors (opportunity)
- Have innovative or in-demand products

Be thorough but efficient. Research at least 5-8 relevant manufacturers."""


def execute_tool(name: str, input_data: dict) -> str:
    """Execute a tool and return results."""

    if name == "search_manufacturers":
        return search_manufacturers(input_data["specialty"])

    elif name == "search_company_details":
        results = brave_search(input_data["query"], max_results=5)
        return json.dumps(results, indent=2)

    elif name == "check_fda_status":
        company = input_data["company_name"]
        product = input_data.get("product_name", "")
        query = f"FDA 510k {company} {product}".strip()
        results = brave_search(query, max_results=5)
        return json.dumps(results, indent=2)

    elif name == "save_company":
        return save_to_notion_db(input_data["company_data"])

    return json.dumps({"error": f"Unknown tool: {name}"})


def run_agent(specialty: str):
    """Run the research agent for a medical specialty."""

    print(f"\n{'='*60}")
    print(f"🔬 Medical Research Agent")
    print(f"📋 Specialty: {specialty}")
    print(f"📅 Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*60}\n")

    messages = [
        {
            "role": "user",
            "content": f"""Research manufacturers in the "{specialty}" medical equipment space.

Find manufacturers that could be potential distribution partners for the Gulf region
(UAE, Saudi Arabia, Kuwait, Qatar, Bahrain, Oman).

For each relevant company:
1. Search for their details
2. Check FDA/CE status
3. Save to Notion with complete information

Start by searching for manufacturers in this specialty."""
        }
    ]

    companies_saved = 0

    while True:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=messages
        )

        # Handle end of conversation
        if response.stop_reason == "end_turn":
            for block in response.content:
                if hasattr(block, "text"):
                    print(f"\n📊 Research Summary:\n{block.text}")
            break

        # Handle tool use
        if response.stop_reason == "tool_use":
            messages.append({"role": "assistant", "content": response.content})

            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    tool_name = block.name
                    tool_input = block.input

                    # Log tool usage
                    if tool_name == "save_company":
                        company = tool_input.get("company_data", {}).get("name", "Unknown")
                        print(f"💾 Saving: {company}")
                        companies_saved += 1
                    elif tool_name == "search_manufacturers":
                        print(f"🔍 Searching manufacturers in: {tool_input.get('specialty')}")
                    elif tool_name == "search_company_details":
                        print(f"🔎 Researching: {tool_input.get('query', '')[:50]}...")
                    elif tool_name == "check_fda_status":
                        print(f"📋 Checking FDA status: {tool_input.get('company_name')}")

                    # Execute tool
                    result = execute_tool(tool_name, tool_input)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result
                    })

            messages.append({"role": "user", "content": tool_results})

    print(f"\n{'='*60}")
    print(f"✅ Research complete!")
    print(f"📊 Companies saved to Notion: {companies_saved}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python run_agent.py \"specialty\"")
        print("Example: python run_agent.py \"PICU equipment\"")
        sys.exit(1)

    specialty = sys.argv[1]
    run_agent(specialty)
