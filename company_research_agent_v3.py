#!/usr/bin/env python3
"""
Company Research Agent V3 - Production Ready
Uses Groq free tier, DuckDuckGo search, rate limiting, and data validation
"""
import pandas as pd
import os
import json
import time
import re
import random
from datetime import datetime
from urllib.parse import urlparse, quote_plus
import warnings
warnings.filterwarnings('ignore')

# ============================================================
# CONFIGURATION
# ============================================================
INPUT_FILE = "/Users/mustafaahmed/Documents/Company_Data_Categorized/MASTER_ALL_COMPANIES_CONSOLIDATED.xlsx"
OUTPUT_FOLDER = "/Users/mustafaahmed/Documents/Company_Data_Categorized"
PROGRESS_FILE = os.path.join(OUTPUT_FOLDER, "research_progress_v3.json")
REVIEW_LOG_FILE = os.path.join(OUTPUT_FOLDER, "research_review_log_v3.json")

# Processing settings
BATCH_SIZE = 20
MIN_DELAY = 1.5
MAX_DELAY = 4.0
BATCH_DELAY = 20
MAX_RETRIES = 2
CONTINUOUS_MODE = True  # Process all batches without stopping
MAX_BATCHES = 0  # 0 = unlimited

# Groq API (free tier: 30 req/min, 14,400 req/day)
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_MODEL = "llama-3.1-8b-instant"
GROQ_RATE_LIMIT = 25

print("=" * 70)
print("COMPANY RESEARCH AGENT V3 - Production")
print("=" * 70)

# ============================================================
# DEPENDENCY CHECKS
# ============================================================
try:
    import requests
    from bs4 import BeautifulSoup
    HAS_WEB = True
except ImportError:
    HAS_WEB = False
    print("! Missing: pip install requests beautifulsoup4")

HAS_GROQ = False
groq_client = None
try:
    from groq import Groq
    if GROQ_API_KEY:
        groq_client = Groq(api_key=GROQ_API_KEY)
        HAS_GROQ = True
        print("✓ Groq AI connected")
    else:
        print("! GROQ_API_KEY not set - using fallback analysis")
        print("  Get free key at: https://console.groq.com/keys")
except ImportError:
    print("! Missing: pip install groq")

# ============================================================
# RATE LIMITER
# ============================================================
class RateLimiter:
    def __init__(self, rpm=30):
        self.rpm = rpm
        self.timestamps = []

    def wait(self):
        now = time.time()
        self.timestamps = [t for t in self.timestamps if now - t < 60]

        if len(self.timestamps) >= self.rpm:
            wait_time = 60 - (now - self.timestamps[0]) + random.uniform(2, 5)
            print(f"    [Rate limit] waiting {wait_time:.0f}s...")
            time.sleep(wait_time)

        time.sleep(random.uniform(MIN_DELAY, MAX_DELAY))
        self.timestamps.append(time.time())

rate_limiter = RateLimiter(GROQ_RATE_LIMIT)

# ============================================================
# WEB SCRAPER
# ============================================================
USER_AGENTS = [
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 Safari/605.1.15',
]

session = requests.Session() if HAS_WEB else None

def get_headers():
    return {
        'User-Agent': random.choice(USER_AGENTS),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
    }

def fetch_url(url, timeout=12):
    """Fetch URL with retries"""
    if not session:
        return None
    for _ in range(MAX_RETRIES):
        try:
            time.sleep(random.uniform(0.3, 1.0))
            resp = session.get(url, headers=get_headers(), timeout=timeout, verify=False, allow_redirects=True)
            if resp.status_code == 200:
                return resp.text
            elif resp.status_code == 429:
                time.sleep(random.uniform(10, 20))
        except:
            time.sleep(random.uniform(1, 3))
    return None

def clean_url(url):
    if pd.isna(url) or not url:
        return None
    url = str(url).strip()
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    return re.sub(r'/+$', '', url)

# ============================================================
# DUCKDUCKGO SEARCH (NO API KEY NEEDED)
# ============================================================
def search_duckduckgo(query, max_results=3):
    """Search DuckDuckGo for company info (no API needed)"""
    if not HAS_WEB:
        return []

    try:
        url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
        html = fetch_url(url)
        if not html:
            return []

        soup = BeautifulSoup(html, 'html.parser')
        results = []

        for result in soup.select('.result')[:max_results]:
            title_elem = result.select_one('.result__title')
            snippet_elem = result.select_one('.result__snippet')
            link_elem = result.select_one('.result__url')

            if title_elem:
                results.append({
                    'title': title_elem.get_text(strip=True),
                    'snippet': snippet_elem.get_text(strip=True) if snippet_elem else '',
                    'url': link_elem.get_text(strip=True) if link_elem else ''
                })

        return results
    except:
        return []

# ============================================================
# WEBPAGE DATA EXTRACTION
# ============================================================
def extract_webpage_data(html, company_name):
    """Extract structured data from webpage"""
    if not html:
        return {}

    try:
        soup = BeautifulSoup(html, 'html.parser')

        # Remove noise
        for tag in soup(['script', 'style', 'nav', 'footer', 'header', 'aside']):
            tag.decompose()

        data = {}

        # Title
        title = soup.find('title')
        data['title'] = title.get_text(strip=True)[:200] if title else ''

        # Meta description
        for meta in [
            soup.find('meta', attrs={'name': 'description'}),
            soup.find('meta', attrs={'property': 'og:description'})
        ]:
            if meta and meta.get('content'):
                data['description'] = meta['content'][:500]
                break

        # Main text
        main = soup.find('main') or soup.find('article') or soup.find('body')
        if main:
            data['text'] = ' '.join(main.get_text(separator=' ', strip=True).split())[:2500]

        # Products from headings
        products = []
        for h in soup.find_all(['h1', 'h2', 'h3'])[:20]:
            text = h.get_text(strip=True)
            if 10 < len(text) < 100:
                products.append(text)
        data['headings'] = products[:10]

        # FDA mentions
        fda_pattern = re.compile(r'(FDA|510\(k\)|PMA|Class\s*[I]{1,3}|cleared|approved)', re.I)
        data['fda_mentions'] = list(set(fda_pattern.findall(data.get('text', ''))))[:5]

        # Contact info
        if 'text' in data:
            emails = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', data['text'])
            data['emails'] = list(set(emails))[:3]

            phones = re.findall(r'[\+]?[(]?[0-9]{1,3}[)]?[-\s\.]?[0-9]{1,4}[-\s\.]?[0-9]{1,4}[-\s\.]?[0-9]{1,9}', data['text'])
            data['phones'] = [p for p in phones if len(re.sub(r'\D', '', p)) >= 10][:3]

        return data
    except:
        return {}

# ============================================================
# GROQ AI ANALYSIS
# ============================================================
def analyze_with_groq(company_name, category, web_data, search_results):
    """Use Groq to analyze company data"""
    if not HAS_GROQ:
        return None

    rate_limiter.wait()

    # Build context
    context_parts = [f"Company: {company_name}", f"Category: {category}"]

    if web_data.get('description'):
        context_parts.append(f"Website description: {web_data['description']}")
    if web_data.get('headings'):
        context_parts.append(f"Products/Services: {', '.join(web_data['headings'][:5])}")
    if web_data.get('fda_mentions'):
        context_parts.append(f"FDA mentions: {', '.join(web_data['fda_mentions'])}")

    for i, sr in enumerate(search_results[:2]):
        context_parts.append(f"Search result {i+1}: {sr.get('snippet', '')}")

    context = '\n'.join(context_parts)

    prompt = f"""Analyze this medical device/healthcare company. Be concise and factual.

{context}

Return ONLY valid JSON (no markdown, no explanation):
{{"description": "2-3 sentence company description", "primary_focus": "main business area", "products": "key products comma separated", "fda_status": "FDA Cleared/510(k)/PMA/Pending/Unknown", "relevance": "High/Medium/Low", "priority": "Critical/High/Medium/Low", "uniqueness": "what makes them unique", "market": "Large/Medium/Niche"}}"""

    try:
        response = groq_client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": "Medical device analyst. Return only JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            max_tokens=400
        )

        text = response.choices[0].message.content.strip()
        # Extract JSON
        match = re.search(r'\{[\s\S]*\}', text)
        if match:
            return json.loads(match.group())
    except Exception as e:
        pass

    return None

# ============================================================
# FALLBACK ANALYSIS (RULE-BASED)
# ============================================================
def fallback_analysis(company_name, category, web_data, search_results):
    """Rule-based analysis when AI unavailable"""
    result = {
        'description': '',
        'primary_focus': category,
        'products': '',
        'fda_status': 'Unknown',
        'relevance': 'Medium',
        'priority': 'Medium',
        'uniqueness': '',
        'market': 'Unknown'
    }

    # Use web description
    if web_data.get('description'):
        result['description'] = web_data['description'][:300]
    elif search_results:
        result['description'] = search_results[0].get('snippet', '')[:300]

    # Products from headings
    if web_data.get('headings'):
        result['products'] = '; '.join(web_data['headings'][:5])

    # FDA from mentions
    fda = web_data.get('fda_mentions', [])
    if fda:
        fda_str = ' '.join(fda).lower()
        if '510(k)' in fda_str:
            result['fda_status'] = '510(k)'
        elif 'pma' in fda_str:
            result['fda_status'] = 'PMA'
        elif 'cleared' in fda_str:
            result['fda_status'] = 'FDA Cleared'
        elif 'approved' in fda_str:
            result['fda_status'] = 'FDA Approved'

    # Relevance based on category
    high_cats = ['Cardiology', 'Surgical', 'Radiology', 'Laboratory']
    if any(c in category for c in high_cats):
        result['relevance'] = 'High'
        result['priority'] = 'High'

    return result

# ============================================================
# DATA VALIDATOR
# ============================================================
review_log = []

def validate_data(company_name, data):
    """Validate and score data quality"""
    issues = []
    score = 100

    if not data.get('company_description') or len(str(data.get('company_description', ''))) < 20:
        issues.append('Missing/short description')
        score -= 25

    if not data.get('key_products_solutions'):
        issues.append('No products found')
        score -= 15

    if data.get('fda_status') == 'Unknown':
        issues.append('FDA unknown')
        score -= 10

    if not data.get('website'):
        issues.append('No website')
        score -= 20

    review_log.append({
        'company': company_name,
        'score': max(0, score),
        'issues': issues,
        'needs_review': score < 60,
        'timestamp': datetime.now().isoformat()
    })

    return score, issues

# ============================================================
# MAIN RESEARCH FUNCTION
# ============================================================
def research_company(row, all_df):
    """Research single company through full pipeline"""
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
    web_data = {}
    if website:
        html = fetch_url(website)
        if html:
            web_data = extract_webpage_data(html, company_name)
            # Fill contact info
            if not result['email'] and web_data.get('emails'):
                result['email'] = web_data['emails'][0]
            if not result['phone'] and web_data.get('phones'):
                result['phone'] = web_data['phones'][0]

    # Step 2: Search for more info
    search_results = []
    if not web_data.get('description'):
        search_query = f"{company_name} medical device company"
        search_results = search_duckduckgo(search_query)

    # Step 3: AI or fallback analysis
    analysis = None
    if HAS_GROQ:
        analysis = analyze_with_groq(company_name, category, web_data, search_results)

    if analysis:
        result['company_description'] = analysis.get('description', '')
        result['primary_focus'] = analysis.get('primary_focus', category)
        result['key_products_solutions'] = analysis.get('products', '')
        result['fda_status'] = analysis.get('fda_status', 'Unknown')
        result['relevance'] = analysis.get('relevance', 'Medium')
        result['priority_level'] = analysis.get('priority', 'Medium')
        result['uniqueness'] = analysis.get('uniqueness', '')
        result['prevalence_of_indication'] = analysis.get('market', 'Unknown')
    else:
        fb = fallback_analysis(company_name, category, web_data, search_results)
        result['company_description'] = fb['description']
        result['primary_focus'] = fb['primary_focus']
        result['key_products_solutions'] = fb['products']
        result['fda_status'] = fb['fda_status']
        result['relevance'] = fb['relevance']
        result['priority_level'] = fb['priority']
        result['uniqueness'] = fb['uniqueness']
        result['prevalence_of_indication'] = fb['market']

    # Step 4: Find competitors
    if category != 'Other / Uncategorized':
        same_cat = all_df[all_df['category'] == category]
        comps = same_cat[same_cat['company_name'] != company_name]['company_name'].head(5).tolist()
        result['competitors'] = ', '.join(comps)
    else:
        result['competitors'] = ''

    # Step 5: Validate
    score, issues = validate_data(company_name, result)
    result['data_quality_score'] = score
    result['notes'] = '; '.join(issues) if issues else 'Complete'

    return result

# ============================================================
# PROGRESS MANAGEMENT
# ============================================================
def load_progress():
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, 'r') as f:
            return json.load(f)
    return {'completed': [], 'batch': 0}

def save_progress(progress):
    with open(PROGRESS_FILE, 'w') as f:
        json.dump(progress, f)

def save_review_log():
    with open(REVIEW_LOG_FILE, 'w') as f:
        json.dump(review_log, f, indent=2)

# ============================================================
# MAIN
# ============================================================
def main():
    global review_log

    print(f"\n[1] Loading data...")
    df = pd.read_excel(INPUT_FILE)
    total = len(df)
    print(f"    Companies: {total}")

    progress = load_progress()
    completed = set(progress.get('completed', []))
    print(f"    Completed: {len(completed)}")

    remaining = [i for i in range(total) if i not in completed]
    print(f"    Remaining: {len(remaining)}")

    if not remaining:
        print("\n    All done!")
        return

    print(f"\n[2] Processing...")
    print(f"    Batch: {BATCH_SIZE}, AI: {'Groq' if HAS_GROQ else 'Fallback'}")
    print(f"    Mode: {'Continuous' if CONTINUOUS_MODE else 'Demo'}")

    results = []
    batch_num = progress.get('batch', 0)

    for i, idx in enumerate(remaining):
        row = df.iloc[idx].to_dict()

        try:
            enriched = research_company(row, df)
            results.append(enriched)
            completed.add(idx)

            if (i + 1) % 5 == 0:
                name = row.get('company_name', '?')[:25]
                print(f"    [{i+1}/{len(remaining)}] {name}")

        except Exception as e:
            results.append({
                'company_name': row.get('company_name', ''),
                'research_status': 'Error',
                'notes': str(e)[:80]
            })

        # Save batch
        if (i + 1) % BATCH_SIZE == 0:
            batch_num += 1
            progress['completed'] = list(completed)
            progress['batch'] = batch_num
            save_progress(progress)

            batch_df = pd.DataFrame(results)
            batch_file = os.path.join(OUTPUT_FOLDER, f"research_v3_batch_{batch_num}.xlsx")
            batch_df.to_excel(batch_file, index=False)

            needs_review = sum(1 for r in review_log[-BATCH_SIZE:] if r.get('needs_review'))
            print(f"\n    ✓ Batch {batch_num}: {BATCH_SIZE} saved, {needs_review} need review")
            save_review_log()

            # Check limits
            if MAX_BATCHES > 0 and batch_num >= MAX_BATCHES:
                print(f"\n    Reached max batches ({MAX_BATCHES})")
                break

            if not CONTINUOUS_MODE:
                print(f"\n    Demo mode - run again to continue")
                break

            # Batch delay
            if len(remaining) - (i + 1) > 0:
                wait = BATCH_DELAY + random.uniform(5, 15)
                print(f"    Waiting {wait:.0f}s...")
                time.sleep(wait)

    # Final save
    progress['completed'] = list(completed)
    save_progress(progress)
    save_review_log()

    # Consolidate
    print(f"\n[3] Consolidating...")
    all_results = []
    for f in sorted(os.listdir(OUTPUT_FOLDER)):
        if f.startswith('research_v3_batch_') and f.endswith('.xlsx'):
            batch_df = pd.read_excel(os.path.join(OUTPUT_FOLDER, f))
            all_results.append(batch_df)

    if all_results:
        final = pd.concat(all_results, ignore_index=True)
        final = final.drop_duplicates(subset=['company_name'], keep='last')

        output = os.path.join(OUTPUT_FOLDER, "COMPANIES_ENRICHED_V3.xlsx")
        final.to_excel(output, index=False)
        print(f"    ✓ COMPANIES_ENRICHED_V3.xlsx ({len(final)} companies)")

    print("\n" + "=" * 70)
    print(f"COMPLETE: {len(completed)}/{total} companies")
    print("=" * 70)

if __name__ == "__main__":
    main()
