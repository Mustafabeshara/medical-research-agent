#!/usr/bin/env python3
"""
Company Research Agent
Enriches company data with detailed information from web research
"""
import pandas as pd
import os
import json
import time
import re
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# Try to import optional dependencies
try:
    import requests
    from bs4 import BeautifulSoup
    HAS_WEB = True
except ImportError:
    HAS_WEB = False
    print("Note: requests/beautifulsoup4 not installed. Install with: pip install requests beautifulsoup4")

# Paths
INPUT_FILE = "/Users/mustafaahmed/Documents/Company_Data_Categorized/MASTER_ALL_COMPANIES_CONSOLIDATED.xlsx"
OUTPUT_FOLDER = "/Users/mustafaahmed/Documents/Company_Data_Categorized"
PROGRESS_FILE = os.path.join(OUTPUT_FOLDER, "research_progress.json")

print("=" * 70)
print("COMPANY RESEARCH AGENT")
print("=" * 70)

# ============================================================
# CONFIGURATION
# ============================================================
BATCH_SIZE = 50  # Companies per batch
DELAY_BETWEEN_REQUESTS = 1  # Seconds between web requests
MAX_RETRIES = 2

# Output columns
OUTPUT_COLUMNS = [
    'company_name',
    'specialty',
    'relevance',
    'prevalence_of_indication',
    'primary_focus',
    'key_products_solutions',
    'fda_status',
    'priority_level',
    'website',
    'notes',
    'company_description',
    'uniqueness',
    'competitors',
    'email',
    'phone',
    'location',
    'research_date',
    'research_status'
]

# Relevance categories
RELEVANCE_OPTIONS = ['High', 'Medium', 'Low', 'Not Relevant']

# FDA Status options
FDA_STATUS_OPTIONS = ['FDA Cleared', 'FDA Approved', '510(k)', 'PMA', 'De Novo',
                      'Not FDA Regulated', 'Pending', 'Unknown']

# Priority levels
PRIORITY_OPTIONS = ['Critical', 'High', 'Medium', 'Low']

# ============================================================
# RESEARCH FUNCTIONS
# ============================================================

def clean_url(url):
    """Clean and validate URL"""
    if pd.isna(url) or not url:
        return None
    url = str(url).strip()
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    # Remove trailing slashes and clean
    url = re.sub(r'/+$', '', url)
    return url

def extract_domain(url):
    """Extract domain from URL"""
    if not url:
        return None
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        return parsed.netloc.replace('www.', '')
    except:
        return None

def fetch_webpage(url, timeout=10):
    """Fetch webpage content"""
    if not HAS_WEB:
        return None
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=timeout, verify=False)
        if response.status_code == 200:
            return response.text
    except Exception as e:
        pass
    return None

def extract_company_info(html, company_name):
    """Extract company information from webpage HTML"""
    if not html:
        return {}

    try:
        soup = BeautifulSoup(html, 'html.parser')
        info = {}

        # Get page title
        title = soup.find('title')
        if title:
            info['page_title'] = title.get_text().strip()

        # Get meta description
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc:
            info['meta_description'] = meta_desc.get('content', '')

        # Get all text for analysis
        text = soup.get_text(separator=' ', strip=True)[:5000]
        info['page_text'] = text

        # Look for product-related content
        product_keywords = ['product', 'solution', 'device', 'system', 'platform', 'service']
        products_found = []
        for tag in soup.find_all(['h1', 'h2', 'h3', 'li']):
            tag_text = tag.get_text().strip()
            if any(kw in tag_text.lower() for kw in product_keywords):
                if len(tag_text) < 200:
                    products_found.append(tag_text)
        info['products_found'] = products_found[:10]

        # Look for FDA mentions
        fda_pattern = re.compile(r'(FDA|510\(k\)|PMA|cleared|approved)', re.IGNORECASE)
        fda_matches = fda_pattern.findall(text)
        info['fda_mentions'] = list(set(fda_matches))

        return info
    except Exception as e:
        return {}

def determine_relevance(company_data, category):
    """Determine relevance based on category and data"""
    high_relevance_categories = [
        'Cardiology & Cardiovascular',
        'Surgical & Operating Room',
        'Radiology & Imaging',
        'Laboratory & Diagnostics'
    ]
    medium_relevance_categories = [
        'Patient Monitoring',
        'Orthopedics & Spine',
        'Neurology & Neurosurgery',
        'Oncology'
    ]

    if category in high_relevance_categories:
        return 'High'
    elif category in medium_relevance_categories:
        return 'Medium'
    elif category == 'Other / Uncategorized':
        return 'Low'
    else:
        return 'Medium'

def determine_fda_status(info):
    """Determine FDA status from extracted info"""
    if not info:
        return 'Unknown'

    fda_mentions = info.get('fda_mentions', [])
    text = info.get('page_text', '').lower()

    if '510(k)' in str(fda_mentions) or '510(k)' in text:
        return '510(k)'
    elif 'pma' in str(fda_mentions).lower() or 'pma approved' in text:
        return 'PMA'
    elif 'fda cleared' in text:
        return 'FDA Cleared'
    elif 'fda approved' in text:
        return 'FDA Approved'
    elif any(m.lower() in ['cleared', 'approved'] for m in fda_mentions):
        return 'FDA Cleared'
    else:
        return 'Unknown'

def determine_priority(relevance, has_website, has_products):
    """Determine priority level"""
    if relevance == 'High' and has_website and has_products:
        return 'Critical'
    elif relevance == 'High':
        return 'High'
    elif relevance == 'Medium' and has_website:
        return 'Medium'
    else:
        return 'Low'

def find_competitors(company_name, category, all_companies):
    """Find potential competitors in the same category"""
    if not category or category == 'Other / Uncategorized':
        return ''

    same_category = all_companies[all_companies['category'] == category]
    competitors = same_category[same_category['company_name'] != company_name]['company_name'].head(5).tolist()
    return ', '.join(competitors) if competitors else ''

def assess_uniqueness(products, description, competitors_count):
    """Assess how unique the company is"""
    if competitors_count == 0:
        return 'Highly Unique - No direct competitors found'
    elif competitors_count <= 3:
        return 'Somewhat Unique - Few competitors'
    elif competitors_count <= 10:
        return 'Moderate - Several competitors exist'
    else:
        return 'Common - Many competitors in space'

def research_company(row, all_companies_df):
    """Research a single company and return enriched data"""
    company_name = row.get('company_name', '')
    website = clean_url(row.get('website', ''))
    category = row.get('category', 'Other / Uncategorized')
    existing_description = row.get('description', '')
    existing_products = row.get('products', '')

    result = {
        'company_name': company_name,
        'website': website,
        'specialty': category,
        'email': row.get('email', ''),
        'phone': row.get('phone', ''),
        'location': row.get('location', ''),
        'research_date': datetime.now().strftime('%Y-%m-%d'),
        'research_status': 'Completed'
    }

    # Try to fetch website info if available
    web_info = {}
    if website and HAS_WEB:
        html = fetch_webpage(website)
        if html:
            web_info = extract_company_info(html, company_name)
            time.sleep(DELAY_BETWEEN_REQUESTS)

    # Determine relevance
    result['relevance'] = determine_relevance(row, category)

    # Primary focus (from category)
    result['primary_focus'] = category

    # Company description
    if web_info.get('meta_description'):
        result['company_description'] = web_info['meta_description']
    elif existing_description and pd.notna(existing_description):
        result['company_description'] = str(existing_description)
    else:
        result['company_description'] = f"Medical company specializing in {category}"

    # Key products/solutions
    products_list = web_info.get('products_found', [])
    if products_list:
        result['key_products_solutions'] = '; '.join(products_list[:5])
    elif existing_products and pd.notna(existing_products):
        result['key_products_solutions'] = str(existing_products)
    else:
        result['key_products_solutions'] = ''

    # FDA Status
    result['fda_status'] = determine_fda_status(web_info)

    # Priority level
    has_website = bool(website)
    has_products = bool(result['key_products_solutions'])
    result['priority_level'] = determine_priority(result['relevance'], has_website, has_products)

    # Find competitors
    competitors = find_competitors(company_name, category, all_companies_df)
    result['competitors'] = competitors
    competitors_count = len(competitors.split(',')) if competitors else 0

    # Uniqueness assessment
    result['uniqueness'] = assess_uniqueness(
        result['key_products_solutions'],
        result['company_description'],
        competitors_count
    )

    # Prevalence of indication (based on category size)
    category_size = len(all_companies_df[all_companies_df['category'] == category])
    if category_size > 1000:
        result['prevalence_of_indication'] = 'High - Large market segment'
    elif category_size > 200:
        result['prevalence_of_indication'] = 'Medium - Moderate market segment'
    else:
        result['prevalence_of_indication'] = 'Low - Niche market segment'

    # Notes
    notes = []
    if not website:
        notes.append('No website available')
    if result['fda_status'] == 'Unknown':
        notes.append('FDA status needs verification')
    if not result['key_products_solutions']:
        notes.append('Products/solutions need research')
    result['notes'] = '; '.join(notes) if notes else 'Data complete'

    return result

# ============================================================
# MAIN PROCESSING
# ============================================================

def load_progress():
    """Load progress from file"""
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, 'r') as f:
            return json.load(f)
    return {'completed_indices': [], 'last_batch': 0}

def save_progress(progress):
    """Save progress to file"""
    with open(PROGRESS_FILE, 'w') as f:
        json.dump(progress, f)

def main():
    print(f"\n[1] Loading company data...")
    df = pd.read_excel(INPUT_FILE)
    total_companies = len(df)
    print(f"    Total companies: {total_companies}")

    # Load progress
    progress = load_progress()
    completed = set(progress.get('completed_indices', []))
    print(f"    Previously completed: {len(completed)}")

    # Find companies to process
    remaining_indices = [i for i in range(total_companies) if i not in completed]
    print(f"    Remaining to process: {len(remaining_indices)}")

    if not remaining_indices:
        print("\n    All companies have been researched!")
        return

    # Process in batches
    print(f"\n[2] Processing companies (batch size: {BATCH_SIZE})...")

    results = []
    batch_count = 0

    for i, idx in enumerate(remaining_indices):
        row = df.iloc[idx].to_dict()

        try:
            enriched = research_company(row, df)
            results.append(enriched)
            completed.add(idx)

            if (i + 1) % 10 == 0:
                print(f"    Processed {i + 1}/{len(remaining_indices)}: {row.get('company_name', 'Unknown')}")

        except Exception as e:
            print(f"    Error processing {row.get('company_name', 'Unknown')}: {e}")
            results.append({
                'company_name': row.get('company_name', ''),
                'research_status': 'Error',
                'notes': str(e)
            })

        # Save batch
        if (i + 1) % BATCH_SIZE == 0:
            batch_count += 1
            progress['completed_indices'] = list(completed)
            progress['last_batch'] = batch_count
            save_progress(progress)

            # Save intermediate results
            batch_df = pd.DataFrame(results)
            batch_file = os.path.join(OUTPUT_FOLDER, f"research_batch_{batch_count}.xlsx")
            batch_df.to_excel(batch_file, index=False)
            print(f"\n    Saved batch {batch_count} ({len(results)} companies)")

            # For demo, stop after first batch
            if batch_count >= 1 and len(remaining_indices) > BATCH_SIZE:
                print(f"\n    Demo mode: Stopping after first batch.")
                print(f"    Run again to continue processing remaining companies.")
                break

    # Save final progress
    progress['completed_indices'] = list(completed)
    save_progress(progress)

    # Create final enriched file
    print(f"\n[3] Creating enriched output file...")

    # Combine with any existing results
    all_results = []
    for f in os.listdir(OUTPUT_FOLDER):
        if f.startswith('research_batch_') and f.endswith('.xlsx'):
            batch_df = pd.read_excel(os.path.join(OUTPUT_FOLDER, f))
            all_results.append(batch_df)

    if all_results:
        final_df = pd.concat(all_results, ignore_index=True)
        final_df = final_df.drop_duplicates(subset=['company_name'], keep='last')

        # Ensure all columns exist
        for col in OUTPUT_COLUMNS:
            if col not in final_df.columns:
                final_df[col] = ''

        # Reorder columns
        final_df = final_df[[c for c in OUTPUT_COLUMNS if c in final_df.columns]]

        output_file = os.path.join(OUTPUT_FOLDER, "COMPANIES_ENRICHED_RESEARCH.xlsx")
        final_df.to_excel(output_file, index=False)
        print(f"    Saved: COMPANIES_ENRICHED_RESEARCH.xlsx ({len(final_df)} companies)")

    print("\n" + "=" * 70)
    print("RESEARCH AGENT COMPLETE")
    print(f"Processed: {len(completed)}/{total_companies} companies")
    print("=" * 70)

if __name__ == "__main__":
    main()
