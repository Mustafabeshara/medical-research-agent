#!/usr/bin/env python3
"""
Company Research Agent V2
Enhanced with Groq AI, rate limiting, human-like behavior, and data validation
"""
import pandas as pd
import os
import json
import time
import re
import random
from datetime import datetime
from urllib.parse import urlparse
import warnings
warnings.filterwarnings('ignore')

# ============================================================
# CONFIGURATION
# ============================================================
INPUT_FILE = "/Users/mustafaahmed/Documents/Company_Data_Categorized/MASTER_ALL_COMPANIES_CONSOLIDATED.xlsx"
OUTPUT_FOLDER = "/Users/mustafaahmed/Documents/Company_Data_Categorized"
PROGRESS_FILE = os.path.join(OUTPUT_FOLDER, "research_progress_v2.json")
REVIEW_LOG_FILE = os.path.join(OUTPUT_FOLDER, "research_review_log.json")

# Rate limiting settings (human-like behavior)
MIN_DELAY = 2  # Minimum seconds between requests
MAX_DELAY = 5  # Maximum seconds between requests
BATCH_SIZE = 25  # Companies per batch (smaller for better rate limiting)
BATCH_DELAY = 30  # Seconds between batches
MAX_RETRIES = 3

# Groq API settings (free tier: 30 req/min, 14,400 req/day)
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_MODEL = "llama-3.1-8b-instant"  # Fast model for research
GROQ_RATE_LIMIT_PER_MIN = 25  # Stay under 30/min limit

print("=" * 70)
print("COMPANY RESEARCH AGENT V2")
print("Enhanced with AI, Rate Limiting, and Data Validation")
print("=" * 70)

# ============================================================
# DEPENDENCIES CHECK
# ============================================================
try:
    import requests
    from bs4 import BeautifulSoup
    HAS_WEB = True
except ImportError:
    HAS_WEB = False
    print("Note: Install requests and beautifulsoup4: pip install requests beautifulsoup4")

try:
    from groq import Groq
    HAS_GROQ = bool(GROQ_API_KEY)
    if HAS_GROQ:
        groq_client = Groq(api_key=GROQ_API_KEY)
        print("✓ Groq API connected")
    else:
        print("Note: Set GROQ_API_KEY environment variable for AI-powered research")
except ImportError:
    HAS_GROQ = False
    print("Note: Install groq: pip install groq")

# ============================================================
# RATE LIMITER
# ============================================================
class RateLimiter:
    """Rate limiter with human-like random delays"""
    def __init__(self, requests_per_minute=30):
        self.requests_per_minute = requests_per_minute
        self.request_times = []

    def wait(self):
        """Wait with human-like random delay"""
        now = time.time()
        # Remove old requests (older than 1 minute)
        self.request_times = [t for t in self.request_times if now - t < 60]

        # If at limit, wait until oldest request expires
        if len(self.request_times) >= self.requests_per_minute:
            sleep_time = 60 - (now - self.request_times[0]) + random.uniform(1, 3)
            print(f"    Rate limit: waiting {sleep_time:.1f}s...")
            time.sleep(sleep_time)

        # Add human-like random delay
        delay = random.uniform(MIN_DELAY, MAX_DELAY)
        time.sleep(delay)

        self.request_times.append(time.time())

rate_limiter = RateLimiter(GROQ_RATE_LIMIT_PER_MIN)

# ============================================================
# WEB SCRAPER WITH HUMAN-LIKE BEHAVIOR
# ============================================================
class HumanLikeScraper:
    """Web scraper with rotating user agents and human-like behavior"""

    USER_AGENTS = [
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
    ]

    def __init__(self):
        self.session = requests.Session() if HAS_WEB else None

    def get_headers(self):
        return {
            'User-Agent': random.choice(self.USER_AGENTS),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }

    def fetch(self, url, timeout=15):
        """Fetch URL with retries and human-like behavior"""
        if not self.session:
            return None

        for attempt in range(MAX_RETRIES):
            try:
                # Human-like delay before request
                time.sleep(random.uniform(0.5, 1.5))

                response = self.session.get(
                    url,
                    headers=self.get_headers(),
                    timeout=timeout,
                    verify=False,
                    allow_redirects=True
                )

                if response.status_code == 200:
                    return response.text
                elif response.status_code == 429:  # Rate limited
                    wait_time = 30 + random.uniform(10, 30)
                    print(f"    Rate limited, waiting {wait_time:.0f}s...")
                    time.sleep(wait_time)

            except Exception as e:
                if attempt < MAX_RETRIES - 1:
                    time.sleep(random.uniform(2, 5))

        return None

scraper = HumanLikeScraper()

# ============================================================
# DATA EXTRACTION
# ============================================================
def clean_url(url):
    """Clean and validate URL"""
    if pd.isna(url) or not url:
        return None
    url = str(url).strip()
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    url = re.sub(r'/+$', '', url)
    return url

def extract_webpage_data(html, company_name):
    """Extract structured data from webpage"""
    if not html or not HAS_WEB:
        return {}

    try:
        soup = BeautifulSoup(html, 'html.parser')
        data = {}

        # Remove script/style elements
        for element in soup(['script', 'style', 'nav', 'footer', 'header']):
            element.decompose()

        # Get title
        title = soup.find('title')
        data['page_title'] = title.get_text().strip()[:200] if title else ''

        # Get meta description
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc:
            data['meta_description'] = meta_desc.get('content', '')[:500]

        # Get Open Graph description (often better quality)
        og_desc = soup.find('meta', attrs={'property': 'og:description'})
        if og_desc:
            data['og_description'] = og_desc.get('content', '')[:500]

        # Extract main content text (first 3000 chars)
        main_content = soup.find('main') or soup.find('article') or soup.find('body')
        if main_content:
            data['main_text'] = ' '.join(main_content.get_text(separator=' ', strip=True).split())[:3000]

        # Find product mentions
        products = []
        product_sections = soup.find_all(['section', 'div'], class_=re.compile(r'product|solution|service', re.I))
        for section in product_sections[:3]:
            headings = section.find_all(['h1', 'h2', 'h3', 'h4'])
            for h in headings[:5]:
                text = h.get_text().strip()
                if len(text) < 100:
                    products.append(text)
        data['products_found'] = products[:10]

        # Find FDA mentions
        fda_pattern = re.compile(r'(FDA\s*(cleared|approved|510\(k\)|PMA|de novo)|510\(k\)|Class\s*[I]{1,3})', re.I)
        fda_matches = fda_pattern.findall(data.get('main_text', ''))
        data['fda_mentions'] = [m[0] if isinstance(m, tuple) else m for m in fda_matches][:5]

        # Find contact info
        email_pattern = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')
        emails = email_pattern.findall(html)
        data['emails_found'] = list(set(emails))[:3]

        phone_pattern = re.compile(r'[\+]?[(]?[0-9]{1,3}[)]?[-\s\.]?[(]?[0-9]{1,4}[)]?[-\s\.]?[0-9]{1,4}[-\s\.]?[0-9]{1,9}')
        phones = phone_pattern.findall(html)
        data['phones_found'] = [p for p in phones if len(p) >= 10][:3]

        return data

    except Exception as e:
        return {}

# ============================================================
# AI-POWERED ANALYSIS (GROQ)
# ============================================================
def analyze_with_groq(company_name, category, webpage_data):
    """Use Groq AI to analyze company and generate structured data"""
    if not HAS_GROQ:
        return None

    rate_limiter.wait()

    # Build context from webpage data
    context = f"""
Company: {company_name}
Category: {category}
Page Title: {webpage_data.get('page_title', 'N/A')}
Description: {webpage_data.get('meta_description', webpage_data.get('og_description', 'N/A'))}
Products Found: {', '.join(webpage_data.get('products_found', [])[:5])}
FDA Mentions: {', '.join(webpage_data.get('fda_mentions', []))}
Main Content (excerpt): {webpage_data.get('main_text', '')[:1000]}
"""

    prompt = f"""Analyze this medical company and provide structured data. Be concise and accurate.

{context}

Respond ONLY in this exact JSON format:
{{
    "company_description": "1-2 sentence description of what the company does",
    "primary_focus": "Main area of focus (e.g., Cardiovascular Devices, Surgical Tools)",
    "key_products": "List of 3-5 key products or solutions, comma separated",
    "fda_status": "One of: FDA Cleared, FDA Approved, 510(k), PMA, De Novo, Pending, Not FDA Regulated, Unknown",
    "relevance": "One of: High, Medium, Low based on medical device industry importance",
    "priority": "One of: Critical, High, Medium, Low based on market significance",
    "uniqueness": "Brief note on what makes this company unique or their competitive advantage",
    "market_segment": "One of: Large Market, Medium Market, Niche Market"
}}

If information is not available, use "Unknown" or reasonable inference from the company name and category."""

    try:
        response = groq_client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": "You are a medical device industry analyst. Provide accurate, structured company analysis."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=500
        )

        result_text = response.choices[0].message.content.strip()

        # Extract JSON from response
        json_match = re.search(r'\{[\s\S]*\}', result_text)
        if json_match:
            return json.loads(json_match.group())

    except Exception as e:
        print(f"    Groq API error: {str(e)[:50]}")

    return None

def fallback_analysis(company_name, category, webpage_data):
    """Fallback analysis when AI is not available"""
    result = {
        'company_description': '',
        'primary_focus': category,
        'key_products': '',
        'fda_status': 'Unknown',
        'relevance': 'Medium',
        'priority': 'Medium',
        'uniqueness': '',
        'market_segment': 'Unknown'
    }

    # Use meta description if available
    if webpage_data.get('meta_description'):
        result['company_description'] = webpage_data['meta_description'][:300]
    elif webpage_data.get('og_description'):
        result['company_description'] = webpage_data['og_description'][:300]

    # Use found products
    if webpage_data.get('products_found'):
        result['key_products'] = '; '.join(webpage_data['products_found'][:5])

    # Determine FDA status from mentions
    fda_mentions = webpage_data.get('fda_mentions', [])
    if fda_mentions:
        mention = str(fda_mentions[0]).lower()
        if '510(k)' in mention:
            result['fda_status'] = '510(k)'
        elif 'pma' in mention:
            result['fda_status'] = 'PMA'
        elif 'cleared' in mention:
            result['fda_status'] = 'FDA Cleared'
        elif 'approved' in mention:
            result['fda_status'] = 'FDA Approved'

    # Determine relevance based on category
    high_relevance = ['Cardiology', 'Surgical', 'Radiology', 'Laboratory']
    if any(cat in category for cat in high_relevance):
        result['relevance'] = 'High'
        result['priority'] = 'High'

    return result

# ============================================================
# DATA VALIDATION & REVIEW
# ============================================================
class DataValidator:
    """Validate and score extracted data quality"""

    def __init__(self):
        self.review_log = []

    def validate(self, company_name, extracted_data, ai_analysis):
        """Validate data quality and flag issues"""
        issues = []
        score = 100

        # Check required fields
        if not extracted_data.get('company_description'):
            issues.append("Missing company description")
            score -= 20

        if not extracted_data.get('key_products_solutions'):
            issues.append("No products/solutions found")
            score -= 15

        if extracted_data.get('fda_status') == 'Unknown':
            issues.append("FDA status unknown")
            score -= 10

        # Check for suspicious data
        desc = extracted_data.get('company_description', '')
        if len(desc) < 20:
            issues.append("Description too short")
            score -= 10
        elif len(desc) > 500:
            extracted_data['company_description'] = desc[:500] + '...'

        # Check if description matches company
        if company_name.lower() not in desc.lower() and len(desc) > 50:
            # Might be wrong company data
            issues.append("Description may not match company")
            score -= 15

        # Validate website data exists
        if not extracted_data.get('website'):
            issues.append("No website available")
            score -= 25

        # Log for review
        review_entry = {
            'company': company_name,
            'score': max(0, score),
            'issues': issues,
            'needs_review': score < 60,
            'timestamp': datetime.now().isoformat()
        }
        self.review_log.append(review_entry)

        return score, issues

    def save_review_log(self):
        """Save review log to file"""
        with open(REVIEW_LOG_FILE, 'w') as f:
            json.dump(self.review_log, f, indent=2)

        # Count issues
        needs_review = sum(1 for r in self.review_log if r['needs_review'])
        print(f"    Review log saved: {needs_review}/{len(self.review_log)} companies need review")

validator = DataValidator()

# ============================================================
# MAIN RESEARCH FUNCTION
# ============================================================
def research_company(row, all_companies_df):
    """Research a single company with full pipeline"""
    company_name = str(row.get('company_name', '')).strip()
    website = clean_url(row.get('website', ''))
    category = row.get('category', 'Other / Uncategorized')

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

    # Step 1: Scrape website
    webpage_data = {}
    if website:
        html = scraper.fetch(website)
        if html:
            webpage_data = extract_webpage_data(html, company_name)
            # Use found contact info if not in original data
            if not result['email'] and webpage_data.get('emails_found'):
                result['email'] = webpage_data['emails_found'][0]
            if not result['phone'] and webpage_data.get('phones_found'):
                result['phone'] = webpage_data['phones_found'][0]

    # Step 2: AI Analysis (with fallback)
    ai_analysis = None
    if HAS_GROQ and webpage_data:
        ai_analysis = analyze_with_groq(company_name, category, webpage_data)

    if ai_analysis:
        result['company_description'] = ai_analysis.get('company_description', '')
        result['primary_focus'] = ai_analysis.get('primary_focus', category)
        result['key_products_solutions'] = ai_analysis.get('key_products', '')
        result['fda_status'] = ai_analysis.get('fda_status', 'Unknown')
        result['relevance'] = ai_analysis.get('relevance', 'Medium')
        result['priority_level'] = ai_analysis.get('priority', 'Medium')
        result['uniqueness'] = ai_analysis.get('uniqueness', '')
        result['prevalence_of_indication'] = ai_analysis.get('market_segment', 'Unknown')
    else:
        # Fallback to rule-based analysis
        fallback = fallback_analysis(company_name, category, webpage_data)
        result['company_description'] = fallback['company_description']
        result['primary_focus'] = fallback['primary_focus']
        result['key_products_solutions'] = fallback['key_products']
        result['fda_status'] = fallback['fda_status']
        result['relevance'] = fallback['relevance']
        result['priority_level'] = fallback['priority']
        result['uniqueness'] = fallback['uniqueness']
        result['prevalence_of_indication'] = fallback['market_segment']

    # Step 3: Find competitors
    if category and category != 'Other / Uncategorized':
        same_cat = all_companies_df[all_companies_df['category'] == category]
        competitors = same_cat[same_cat['company_name'] != company_name]['company_name'].head(5).tolist()
        result['competitors'] = ', '.join(competitors)
    else:
        result['competitors'] = ''

    # Step 4: Validate
    score, issues = validator.validate(company_name, result, ai_analysis)
    result['data_quality_score'] = score
    result['notes'] = '; '.join(issues) if issues else 'Data complete'

    return result

# ============================================================
# PROGRESS MANAGEMENT
# ============================================================
def load_progress():
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, 'r') as f:
            return json.load(f)
    return {'completed_indices': [], 'last_batch': 0, 'groq_calls': 0}

def save_progress(progress):
    with open(PROGRESS_FILE, 'w') as f:
        json.dump(progress, f)

# ============================================================
# MAIN EXECUTION
# ============================================================
def main():
    print(f"\n[1] Loading company data...")
    df = pd.read_excel(INPUT_FILE)
    total = len(df)
    print(f"    Total companies: {total}")

    progress = load_progress()
    completed = set(progress.get('completed_indices', []))
    print(f"    Previously completed: {len(completed)}")

    remaining = [i for i in range(total) if i not in completed]
    print(f"    Remaining to process: {len(remaining)}")

    if not remaining:
        print("\n    All companies researched!")
        return

    print(f"\n[2] Processing companies...")
    print(f"    Batch size: {BATCH_SIZE}")
    print(f"    Using Groq AI: {'Yes' if HAS_GROQ else 'No (fallback mode)'}")
    print(f"    Rate limit: {GROQ_RATE_LIMIT_PER_MIN}/min")

    results = []
    batch_num = progress.get('last_batch', 0)

    for i, idx in enumerate(remaining):
        row = df.iloc[idx].to_dict()

        try:
            enriched = research_company(row, df)
            results.append(enriched)
            completed.add(idx)

            if (i + 1) % 5 == 0:
                company = row.get('company_name', 'Unknown')[:30]
                print(f"    [{i+1}/{len(remaining)}] {company}...")

        except Exception as e:
            results.append({
                'company_name': row.get('company_name', ''),
                'research_status': 'Error',
                'notes': str(e)[:100]
            })

        # Save batch
        if (i + 1) % BATCH_SIZE == 0:
            batch_num += 1
            progress['completed_indices'] = list(completed)
            progress['last_batch'] = batch_num
            save_progress(progress)

            batch_df = pd.DataFrame(results)
            batch_file = os.path.join(OUTPUT_FOLDER, f"research_v2_batch_{batch_num}.xlsx")
            batch_df.to_excel(batch_file, index=False)
            print(f"\n    ✓ Saved batch {batch_num} ({len(results)} companies)")

            # Save review log
            validator.save_review_log()

            # Batch delay (human-like)
            if len(remaining) - (i + 1) > 0:
                wait = BATCH_DELAY + random.uniform(5, 15)
                print(f"    Waiting {wait:.0f}s before next batch...")
                time.sleep(wait)

            # For demo, process limited batches
            if batch_num >= 2:
                print(f"\n    Demo: Stopping after {batch_num} batches.")
                print(f"    Run again to continue.")
                break

    # Save final progress
    progress['completed_indices'] = list(completed)
    save_progress(progress)
    validator.save_review_log()

    # Consolidate results
    print(f"\n[3] Consolidating results...")
    all_results = []
    for f in os.listdir(OUTPUT_FOLDER):
        if f.startswith('research_v2_batch_') and f.endswith('.xlsx'):
            batch_df = pd.read_excel(os.path.join(OUTPUT_FOLDER, f))
            all_results.append(batch_df)

    if all_results:
        final_df = pd.concat(all_results, ignore_index=True)
        final_df = final_df.drop_duplicates(subset=['company_name'], keep='last')

        output_file = os.path.join(OUTPUT_FOLDER, "COMPANIES_ENRICHED_V2.xlsx")
        final_df.to_excel(output_file, index=False)
        print(f"    ✓ Saved: COMPANIES_ENRICHED_V2.xlsx ({len(final_df)} companies)")

    print("\n" + "=" * 70)
    print("RESEARCH COMPLETE")
    print(f"Processed: {len(completed)}/{total} companies")
    print("=" * 70)

if __name__ == "__main__":
    main()
