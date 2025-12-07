"""
Medical Company Research Agent
Researches manufacturers in a given medical specialty and outputs structured data.
"""

import anthropic
import json
from datetime import datetime

client = anthropic.Anthropic()

# Define the tools the agent can use
tools = [
    {
        "name": "web_search",
        "description": "Search the web for medical equipment manufacturers and companies",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query for finding manufacturers"
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "extract_company_info",
        "description": "Extract structured company information from research results",
        "input_schema": {
            "type": "object",
            "properties": {
                "company_name": {"type": "string"},
                "raw_data": {"type": "string", "description": "Raw research data to extract from"}
            },
            "required": ["company_name", "raw_data"]
        }
    },
    {
        "name": "check_regulatory_status",
        "description": "Check FDA 510(k) database and CE Mark status for a company/product",
        "input_schema": {
            "type": "object",
            "properties": {
                "company_name": {"type": "string"},
                "product_category": {"type": "string"}
            },
            "required": ["company_name"]
        }
    },
    {
        "name": "save_to_notion",
        "description": "Save structured company data to Notion database",
        "input_schema": {
            "type": "object",
            "properties": {
                "company_data": {
                    "type": "object",
                    "description": "Structured company information"
                }
            },
            "required": ["company_data"]
        }
    }
]

# Tool implementations (you'll need to fill these in)
def execute_tool(tool_name: str, tool_input: dict) -> str:
    """Execute a tool and return results."""

    if tool_name == "web_search":
        # Option 1: Use Brave Search API
        # Option 2: Use SerpAPI
        # Option 3: Use Tavily API
        return search_web(tool_input["query"])

    elif tool_name == "extract_company_info":
        # Claude will handle extraction via prompting
        return json.dumps({
            "status": "extracted",
            "company": tool_input["company_name"]
        })

    elif tool_name == "check_regulatory_status":
        return check_fda_ce_status(
            tool_input["company_name"],
            tool_input.get("product_category", "")
        )

    elif tool_name == "save_to_notion":
        return save_to_notion_db(tool_input["company_data"])

    return json.dumps({"error": f"Unknown tool: {tool_name}"})


def search_web(query: str) -> str:
    """
    Implement web search using your preferred API.
    Options:
    - Brave Search API (you have this via MCP)
    - SerpAPI
    - Tavily (designed for AI agents)
    """
    # TODO: Implement with your API of choice
    # Example with Brave Search:
    # import requests
    # headers = {"X-Subscription-Token": BRAVE_API_KEY}
    # resp = requests.get(
    #     "https://api.search.brave.com/res/v1/web/search",
    #     params={"q": query, "count": 10},
    #     headers=headers
    # )
    # return json.dumps(resp.json())
    pass


def check_fda_ce_status(company: str, product_category: str) -> str:
    """
    Check regulatory databases:
    - FDA 510(k): https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfpmn/pmn.cfm
    - CE Mark: Check company website or EUDAMED (when available)
    """
    # TODO: Implement FDA/CE checking
    # Could scrape FDA database or use their API
    pass


def save_to_notion_db(company_data: dict) -> str:
    """
    Save to Notion using their API.
    Requires: NOTION_API_KEY and DATABASE_ID
    """
    # TODO: Implement Notion integration
    # from notion_client import Client
    # notion = Client(auth=NOTION_API_KEY)
    # notion.pages.create(
    #     parent={"database_id": DATABASE_ID},
    #     properties={...}
    # )
    pass


def run_research_agent(specialty: str, max_companies: int = 10):
    """
    Main agent loop - researches manufacturers in a medical specialty.
    """

    system_prompt = """You are a medical equipment research agent for a business development team.

Your task is to research manufacturers in a given medical specialty and extract:
1. Company name and headquarters location
2. Main products in the specialty
3. Key certifications (ISO 13485, CE Mark, FDA clearances)
4. Distribution model (direct, distributors, looking for partners)
5. Gulf region presence (existing distributors, offices, or gaps)
6. Contact information if available
7. Competitive positioning notes

Be thorough but efficient. Use web_search to find companies, then extract structured data.
For each promising company, check their regulatory status.
Save each company's data to Notion when complete.

Focus on manufacturers, not distributors or resellers."""

    messages = [
        {
            "role": "user",
            "content": f"""Research manufacturers in the "{specialty}" medical equipment space.

Find up to {max_companies} relevant manufacturers that could be potential partners for
distribution in the Gulf region (UAE, Saudi Arabia, Kuwait, Qatar, Bahrain, Oman).

For each company, gather complete information and save to Notion."""
        }
    ]

    print(f"\n🔬 Starting research for: {specialty}")
    print("=" * 50)

    # Agent loop
    while True:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            system=system_prompt,
            tools=tools,
            messages=messages
        )

        # Check if we're done
        if response.stop_reason == "end_turn":
            # Extract final text response
            for block in response.content:
                if hasattr(block, "text"):
                    print(f"\n📋 Final Report:\n{block.text}")
            break

        # Process tool calls
        if response.stop_reason == "tool_use":
            # Add assistant's response to messages
            messages.append({"role": "assistant", "content": response.content})

            # Execute each tool call
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    print(f"🔧 Using tool: {block.name}")
                    print(f"   Input: {json.dumps(block.input, indent=2)[:200]}...")

                    result = execute_tool(block.name, block.input)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result
                    })

            # Add tool results to messages
            messages.append({"role": "user", "content": tool_results})

    print("\n✅ Research complete!")


if __name__ == "__main__":
    import sys

    specialty = sys.argv[1] if len(sys.argv) > 1 else "PICU equipment"
    run_research_agent(specialty)
