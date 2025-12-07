# Medical Company Research Agent

AI-powered agent that researches medical equipment manufacturers for business development in the Gulf region.

## Features

- 🔍 **Web Search** - Finds manufacturers by medical specialty using Brave Search
- 🌐 **Deep Web Scraping** - Extracts products, certifications, contacts from company websites
- 📋 **FDA Database Integration** - Queries official FDA openFDA API for 510(k) clearances, recalls, registrations
- 📊 **Competitor Mapping** - Analyzes competitive landscape and market positioning
- 📧 **Email Finder** - Discovers business contacts using Hunter.io and Apollo.io
- 🌍 **Gulf Focus** - Identifies companies without existing Gulf distributors (opportunities)
- 📝 **Notion Export** - Saves structured data to your Notion database
- 🔄 **Batch Processing** - Research multiple specialties in sequence

## Project Structure

```
medical-research-agent/
├── run_agent.py          # Single specialty research
├── batch_research.py     # Multi-specialty batch processing
├── config.py             # Configuration settings
├── requirements.txt      # Dependencies
├── .env.example          # Environment template
└── tools/
    ├── search.py         # Brave Search integration
    ├── web_scraper.py    # Deep website scraping
    ├── fda_api.py        # FDA openFDA API
    ├── competitor_mapping.py  # Competitive analysis
    ├── email_finder.py   # Hunter.io/Apollo contact finder
    └── notion_client.py  # Notion database integration
```

## Setup

### 1. Install Dependencies

```bash
cd ~/medical-research-agent
pip install -r requirements.txt
```

### 2. Configure API Keys

```bash
cp .env.example .env
```

Edit `.env` with your keys:

```bash
# Required
ANTHROPIC_API_KEY=sk-ant-xxxxx
BRAVE_API_KEY=xxxxx          # https://brave.com/search/api

# Notion Integration
NOTION_API_KEY=secret_xxxxx  # https://notion.so/my-integrations
NOTION_DATABASE_ID=xxxxx

# Optional (enhances functionality)
HUNTER_API_KEY=xxxxx         # https://hunter.io (25 free/month)
APOLLO_API_KEY=xxxxx         # https://apollo.io
FDA_API_KEY=xxxxx            # https://open.fda.gov (increases rate limit)
```

### 3. Set Up Notion Database

Create a Notion database with these properties:

| Property | Type |
|----------|------|
| Company Name | Title |
| Specialty | Select |
| Headquarters | Text |
| Products | Text |
| Website | URL |
| CE Mark | Checkbox |
| FDA Cleared | Checkbox |
| ISO 13485 | Checkbox |
| Gulf Presence | Select (Has Distributor, Direct Office, None/Unknown) |
| Distribution Model | Select (Direct, Distributors, Seeking Partners, Unknown) |
| Contact Email | Email |
| Notes | Text |
| Research Date | Date |
| Status | Select (Researched, To Contact, In Discussion, Not Fit) |

Then share the database with your Notion integration.

## Usage

### Single Specialty Research

```bash
python run_agent.py "PICU equipment"
python run_agent.py "interventional radiology"
python run_agent.py "patient monitoring"
```

### Batch Processing (Multiple Specialties)

```bash
# From command line
python batch_research.py --specialties "PICU equipment" "ventilators" "infusion pumps"

# From file (one specialty per line)
python batch_research.py specialties.txt

# With custom output directory
python batch_research.py --specialties "cardiac monitoring" -o ./my_research
```

Example `specialties.txt`:
```
PICU equipment
patient monitoring
ventilators
infusion pumps
surgical equipment
```

## What the Agent Does

For each specialty, the agent:

1. **Searches** for manufacturers using Brave Search
2. **Scrapes** each company website for:
   - Products and product categories
   - Certifications (CE, FDA, ISO)
   - Distribution model
   - Contact information
   - International presence
3. **Checks FDA** status via openFDA API:
   - 510(k) clearances
   - Device recalls
   - Establishment registrations
4. **Finds contacts** using Hunter.io/Apollo:
   - Email addresses
   - Job titles
   - LinkedIn profiles
5. **Maps competitors** in the specialty
6. **Saves** complete data to Notion
7. **Generates** summary report

## Output

- Structured company data in Notion
- Markdown reports per specialty
- JSON summary with statistics:
  - Companies researched
  - Contacts found
  - FDA clearance counts
  - Research duration

## API Costs

| Service | Free Tier | Notes |
|---------|-----------|-------|
| Brave Search | 2,000/month | Required |
| Hunter.io | 25/month | Optional, enhances contacts |
| Apollo.io | 50 credits/month | Optional, alternative to Hunter |
| openFDA | 240/minute | No key needed, key increases limit |
| Notion | Unlimited | Required |

## Customization

### Target Different Regions

Edit `tools/competitor_mapping.py` to change the focus region from Gulf to another market.

### Change Target Roles for Contacts

Edit `tools/email_finder.py` `target_roles` to find different job titles.

### Adjust Search Queries

Edit `config.py` `SEARCH_QUERIES_PER_SPECIALTY` to customize search patterns.
