#!/usr/bin/env python3
"""
Batch Research Agent - Process multiple medical specialties in sequence.
Generates comprehensive market research reports.

Usage:
    python batch_research.py specialties.txt
    python batch_research.py --specialties "PICU equipment" "patient monitoring" "ventilators"
"""

import anthropic
import json
import sys
import os
import argparse
from datetime import datetime
from pathlib import Path
from typing import List, Dict
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

from dotenv import load_dotenv

# Import all tools
from tools.search import search_manufacturers, brave_search
from tools.notion_client import save_to_notion_db, NotionDB
from tools.web_scraper import scrape_company_website
from tools.fda_api import check_fda_510k, get_fda_company_profile
from tools.competitor_mapping import map_competitors, build_market_matrix
from tools.email_finder import find_company_contacts

load_dotenv()

client = anthropic.Anthropic()


# Enhanced tool definitions
TOOLS = [
    {
        "name": "search_manufacturers",
        "description": "Search for medical equipment manufacturers in a specific specialty",
        "input_schema": {
            "type": "object",
            "properties": {
                "specialty": {"type": "string", "description": "Medical specialty to search"}
            },
            "required": ["specialty"]
        }
    },
    {
        "name": "scrape_company_website",
        "description": "Deep scrape a company website to extract detailed information including products, certifications, contact details, and distribution info",
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "Company website URL to scrape"}
            },
            "required": ["url"]
        }
    },
    {
        "name": "check_fda_status",
        "description": "Check FDA 510(k) clearance status using the official FDA database",
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
        "name": "get_fda_profile",
        "description": "Get comprehensive FDA profile including clearances, recalls, and registration status",
        "input_schema": {
            "type": "object",
            "properties": {
                "company_name": {"type": "string"}
            },
            "required": ["company_name"]
        }
    },
    {
        "name": "map_competitors",
        "description": "Analyze competitive landscape and identify major players in a specialty",
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
        "name": "find_contacts",
        "description": "Find business contacts and emails for a company using Hunter.io/Apollo",
        "input_schema": {
            "type": "object",
            "properties": {
                "website": {"type": "string", "description": "Company website URL"},
                "target_roles": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Job titles to target (e.g., 'VP Sales', 'Export Manager')"
                }
            },
            "required": ["website"]
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
                    "properties": {
                        "name": {"type": "string"},
                        "specialty": {"type": "string"},
                        "headquarters": {"type": "string"},
                        "products": {"type": "string"},
                        "website": {"type": "string"},
                        "ce_mark": {"type": "boolean"},
                        "fda_cleared": {"type": "boolean"},
                        "iso_13485": {"type": "boolean"},
                        "gulf_presence": {"type": "string"},
                        "distribution_model": {"type": "string"},
                        "contact_email": {"type": "string"},
                        "notes": {"type": "string"}
                    },
                    "required": ["name", "specialty"]
                }
            },
            "required": ["company_data"]
        }
    },
    {
        "name": "generate_report",
        "description": "Generate a summary report for a completed specialty research",
        "input_schema": {
            "type": "object",
            "properties": {
                "specialty": {"type": "string"},
                "companies_researched": {"type": "array", "items": {"type": "object"}},
                "market_insights": {"type": "string"}
            },
            "required": ["specialty"]
        }
    }
]


SYSTEM_PROMPT = """You are an advanced medical equipment research agent for business development.

For each specialty, you will:
1. Search for manufacturers using search_manufacturers
2. For each promising company:
   a. Scrape their website for detailed info (scrape_company_website)
   b. Check FDA status (get_fda_profile)
   c. Find business contacts (find_contacts)
   d. Map competitors (map_competitors)
   e. Save complete data to Notion (save_company)
3. Generate a summary report

RESEARCH PRIORITIES:
- Focus on manufacturers, not distributors
- Prioritize companies with CE Mark (required for Gulf)
- Identify companies WITHOUT existing Gulf presence (opportunity)
- Look for innovative products and strong regulatory status
- Find decision-maker contacts for outreach

Be thorough but efficient. Research 5-8 companies per specialty.
Always save data to Notion before moving to the next company."""


def execute_tool(name: str, input_data: dict) -> str:
    """Execute a tool and return results."""

    if name == "search_manufacturers":
        return search_manufacturers(input_data["specialty"])

    elif name == "scrape_company_website":
        return scrape_company_website(input_data["url"])

    elif name == "check_fda_status":
        return check_fda_510k(
            input_data["company_name"],
            input_data.get("product_name")
        )

    elif name == "get_fda_profile":
        return get_fda_company_profile(input_data["company_name"])

    elif name == "map_competitors":
        return map_competitors(
            input_data["company_name"],
            input_data["specialty"]
        )

    elif name == "find_contacts":
        return find_company_contacts(
            input_data["website"],
            input_data.get("target_roles")
        )

    elif name == "save_company":
        return save_to_notion_db(input_data["company_data"])

    elif name == "generate_report":
        # Just acknowledge - the report is in the agent's response
        return json.dumps({"status": "report_generated", "specialty": input_data["specialty"]})

    return json.dumps({"error": f"Unknown tool: {name}"})


def research_specialty(specialty: str, output_dir: Path = None) -> Dict:
    """
    Run full research for a single specialty.
    Returns research results and statistics.
    """
    start_time = datetime.now()

    print(f"\n{'='*60}")
    print(f"🔬 Researching: {specialty}")
    print(f"📅 Started: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")

    messages = [
        {
            "role": "user",
            "content": f"""Research manufacturers in the "{specialty}" medical equipment space.

Find 5-8 manufacturers that could be potential distribution partners for the Gulf region.

For each company:
1. Scrape their website for complete info
2. Check their FDA profile (clearances, recalls, registration)
3. Find business contacts for outreach
4. Analyze competitive positioning
5. Save to Notion with all data

Focus on companies that:
- Have CE Mark certification
- Don't have existing Gulf distributors
- Have innovative or in-demand products

Start by searching for manufacturers."""
        }
    ]

    stats = {
        "specialty": specialty,
        "companies_found": 0,
        "companies_saved": 0,
        "contacts_found": 0,
        "fda_cleared": 0,
        "start_time": start_time.isoformat(),
        "end_time": None,
        "duration_minutes": 0,
        "errors": []
    }

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
            stats["errors"].append(f"API error: {str(e)}")
            break

        # Handle end of conversation
        if response.stop_reason == "end_turn":
            for block in response.content:
                if hasattr(block, "text"):
                    print(f"\n📊 Summary:\n{block.text}")

                    # Save report to file if output_dir specified
                    if output_dir:
                        report_file = output_dir / f"{specialty.replace(' ', '_')}_report.md"
                        with open(report_file, "w") as f:
                            f.write(f"# Research Report: {specialty}\n\n")
                            f.write(f"Generated: {datetime.now().isoformat()}\n\n")
                            f.write(block.text)
                        print(f"📄 Report saved: {report_file}")
            break

        # Handle tool use
        if response.stop_reason == "tool_use":
            messages.append({"role": "assistant", "content": response.content})

            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    tool_name = block.name
                    tool_input = block.input

                    # Log and track stats
                    if tool_name == "save_company":
                        company = tool_input.get("company_data", {}).get("name", "Unknown")
                        print(f"💾 Saving: {company}")
                        stats["companies_saved"] += 1
                        if tool_input.get("company_data", {}).get("fda_cleared"):
                            stats["fda_cleared"] += 1

                    elif tool_name == "search_manufacturers":
                        print(f"🔍 Searching: {tool_input.get('specialty')}")

                    elif tool_name == "scrape_company_website":
                        url = tool_input.get("url", "")
                        print(f"🌐 Scraping: {url[:50]}...")
                        stats["companies_found"] += 1

                    elif tool_name == "find_contacts":
                        print(f"📧 Finding contacts...")

                    elif tool_name == "get_fda_profile":
                        print(f"📋 FDA check: {tool_input.get('company_name')}")

                    elif tool_name == "map_competitors":
                        print(f"📊 Mapping competitors...")

                    # Execute tool
                    try:
                        result = execute_tool(tool_name, tool_input)

                        # Track contact stats
                        if tool_name == "find_contacts":
                            try:
                                contact_data = json.loads(result)
                                stats["contacts_found"] += contact_data.get("total_contacts", 0)
                            except:
                                pass

                    except Exception as e:
                        result = json.dumps({"error": str(e)})
                        stats["errors"].append(f"{tool_name}: {str(e)}")

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result
                    })

            messages.append({"role": "user", "content": tool_results})

    # Finalize stats
    end_time = datetime.now()
    stats["end_time"] = end_time.isoformat()
    stats["duration_minutes"] = (end_time - start_time).total_seconds() / 60

    print(f"\n✅ Completed: {specialty}")
    print(f"   Companies saved: {stats['companies_saved']}")
    print(f"   Contacts found: {stats['contacts_found']}")
    print(f"   Duration: {stats['duration_minutes']:.1f} minutes")

    return stats


def run_batch_research(
    specialties: List[str],
    output_dir: str = None,
    parallel: bool = False
) -> Dict:
    """
    Run research for multiple specialties.

    Args:
        specialties: List of medical specialties to research
        output_dir: Directory to save reports (optional)
        parallel: Run specialties in parallel (experimental)

    Returns:
        Summary of all research
    """
    # Setup output directory
    if output_dir:
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
    else:
        output_path = Path("research_output") / datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*60}")
    print(f"🚀 BATCH RESEARCH AGENT")
    print(f"{'='*60}")
    print(f"📋 Specialties to research: {len(specialties)}")
    for i, s in enumerate(specialties, 1):
        print(f"   {i}. {s}")
    print(f"📁 Output directory: {output_path}")
    print(f"{'='*60}\n")

    all_stats = []
    start_time = datetime.now()

    if parallel and len(specialties) > 1:
        # Parallel execution (experimental - may hit rate limits)
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = {
                executor.submit(research_specialty, s, output_path): s
                for s in specialties
            }
            for future in as_completed(futures):
                specialty = futures[future]
                try:
                    stats = future.result()
                    all_stats.append(stats)
                except Exception as e:
                    print(f"❌ Error researching {specialty}: {e}")
                    all_stats.append({"specialty": specialty, "error": str(e)})
    else:
        # Sequential execution (recommended)
        for specialty in specialties:
            try:
                stats = research_specialty(specialty, output_path)
                all_stats.append(stats)

                # Brief pause between specialties to avoid rate limits
                if specialties.index(specialty) < len(specialties) - 1:
                    print("\n⏳ Pausing before next specialty...")
                    time.sleep(5)

            except Exception as e:
                print(f"❌ Error researching {specialty}: {e}")
                all_stats.append({"specialty": specialty, "error": str(e)})

    # Generate summary
    end_time = datetime.now()
    total_duration = (end_time - start_time).total_seconds() / 60

    summary = {
        "batch_started": start_time.isoformat(),
        "batch_completed": end_time.isoformat(),
        "total_duration_minutes": total_duration,
        "specialties_researched": len(specialties),
        "total_companies_saved": sum(s.get("companies_saved", 0) for s in all_stats),
        "total_contacts_found": sum(s.get("contacts_found", 0) for s in all_stats),
        "specialty_stats": all_stats
    }

    # Save summary
    summary_file = output_path / "batch_summary.json"
    with open(summary_file, "w") as f:
        json.dump(summary, f, indent=2)

    # Print final summary
    print(f"\n{'='*60}")
    print(f"📊 BATCH RESEARCH COMPLETE")
    print(f"{'='*60}")
    print(f"   Specialties: {len(specialties)}")
    print(f"   Total companies: {summary['total_companies_saved']}")
    print(f"   Total contacts: {summary['total_contacts_found']}")
    print(f"   Duration: {total_duration:.1f} minutes")
    print(f"   Summary saved: {summary_file}")
    print(f"{'='*60}\n")

    return summary


def main():
    parser = argparse.ArgumentParser(
        description="Batch research medical equipment manufacturers"
    )
    parser.add_argument(
        "input_file",
        nargs="?",
        help="Text file with specialties (one per line)"
    )
    parser.add_argument(
        "--specialties",
        nargs="+",
        help="List of specialties to research"
    )
    parser.add_argument(
        "--output",
        "-o",
        help="Output directory for reports"
    )
    parser.add_argument(
        "--parallel",
        action="store_true",
        help="Run specialties in parallel (experimental)"
    )

    args = parser.parse_args()

    # Get specialties from file or command line
    specialties = []

    if args.input_file:
        with open(args.input_file, "r") as f:
            specialties = [line.strip() for line in f if line.strip()]
    elif args.specialties:
        specialties = args.specialties
    else:
        # Default specialties for demo
        specialties = [
            "PICU equipment",
            "patient monitoring",
            "infusion pumps"
        ]
        print("No specialties specified, using defaults...")

    run_batch_research(specialties, args.output, args.parallel)


if __name__ == "__main__":
    main()
