import datetime as dt
import re
from pathlib import Path
from main import (
    BRIEFS_DIR, 
    ARTICLE_TEMPLATE_PATH, 
    update_article_from_template, 
    replace_marker, 
    get_nav_links,
    clean_text
)

# Boilerplate <p> patterns to remove from the article body HTML
BOILERPLATE_PARAGRAPHS = [
    r"<p>The current market landscape is witnessing significant developments[^<]*?</p>",
    r"<p>Recent news indicates that[^<]*?</p>",
    r"<p>The world of finance is constantly evolving[^<]*?</p>",
    r"<p>In the latest market developments[^<]*?</p>",
    r"<p>A concise top\-line briefing[^<]*?</p>",
    r"<p>Market briefing and contextual analysis\.</p>",
]

# Boilerplate lede strings to replace
BOILERPLATE_LEDE_PHRASES = [
    "The current market landscape is witnessing significant developments",
    "Recent news indicates that",
    "The world of finance is constantly evolving",
    "A concise top-line briefing explains",
    "Market briefing and contextual analysis.",
    "Daily market briefing with practical context",
    "Markets are repricing rates, inflation, and risk appetite",
]


def is_boilerplate(text: str) -> bool:
    """Returns True if the text is a known boilerplate phrase."""
    for phrase in BOILERPLATE_LEDE_PHRASES:
        if phrase.lower() in text.lower():
            return True
    return False


def clean_body_html(body: str) -> str:
    """Remove known boilerplate <p> paragraphs from the body HTML."""
    for pattern in BOILERPLATE_PARAGRAPHS:
        body = re.sub(pattern, "", body, flags=re.IGNORECASE | re.DOTALL)
    # Update styling for Questions Investors Are Asking heading
    body = body.replace(
        'class="mt-10 border-l-4 border-emerald pl-3 text-xl font-extrabold text-emerald sm:text-2xl">Questions Investors Are Asking',
        'class="mt-10 border-l-4 border-black pl-3 text-xl font-extrabold text-black sm:text-2xl">Questions Investors Are Asking'
    )
    # Update styling for Question blocks
    body = body.replace(
        'class="rounded-md bg-emerald/10 px-3 py-2"><strong class="text-base font-extrabold text-emerald sm:text-lg"',
        'class="rounded-md bg-white border border-black px-3 py-2"><strong class="text-base font-extrabold text-black sm:text-lg"'
    )
    
    # Remove duplicate <!-- BRIEF_BODY --> markers that sometimes appear
    body = re.sub(r"<!-- BRIEF_BODY -->\s*<!-- BRIEF_BODY -->", "<!-- BRIEF_BODY -->", body)
    body = re.sub(r"<!-- /BRIEF_BODY -->\s*<!-- /BRIEF_BODY -->", "<!-- /BRIEF_BODY -->", body)
    return body.strip()


def extract_clean_lede(body_html: str) -> str:
    """Extract the first non-boilerplate sentence from body HTML for use as a lede."""
    # Find all <p> tags
    paragraphs = re.findall(r"<p[^>]*>(.*?)</p>", body_html, re.DOTALL)
    for para in paragraphs:
        # Strip HTML tags
        text = re.sub(r"<.*?>", "", para).strip()
        if not text or is_boilerplate(text):
            continue
        # Return first sentence (up to 260 chars)
        sentence_match = re.search(r"(.+?[.!?])(?:\s|$)", text)
        if sentence_match:
            return sentence_match.group(1).strip()[:260]
        if len(text) > 30:
            return text[:260]
    return "Daily market briefing with practical context for US and UK readers."


def rebuild_all():
    all_briefs = sorted(list(BRIEFS_DIR.glob("*.html")))
    template_content = ARTICLE_TEMPLATE_PATH.read_text(encoding="utf-8")
    
    print(f"Found {len(all_briefs)} briefs to rebuild.")
    
    for path in all_briefs:
        print(f"Processing {path.name}...")
        content = path.read_text(encoding="utf-8")
        
        # 1. Extract Headline
        headline_match = re.search(r"<!-- ARTICLE_HEADLINE -->(.*?)<!-- /ARTICLE_HEADLINE -->", content, re.DOTALL)
        if not headline_match:
            headline_match = re.search(r"<h1.*?>(.*?)</h1>", content, re.DOTALL)
            
        # 2. Extract Summary / Description
        summary_match = re.search(r'<meta name="description" content="(.*?)"', content)
        
        # 3. Extract Body
        body_match = re.search(r'<section id="article-body".*?>(.*?)</section>', content, re.DOTALL)
        
        # 4. Extract Date
        date_match = re.search(r"brief-(\d{4}-\d{2}-\d{2})", path.name)
        
        if not all([headline_match, summary_match, body_match, date_match]):
            print(f"  ERROR: Skip {path.name} - Missing data fields.")
            continue
            
        # Clean headline and summary
        headline = clean_text(re.sub(r'<.*?>', '', headline_match.group(1)).strip())
        headline = re.sub(r'<!--.*?-->', '', headline).strip()
        summary = clean_text(summary_match.group(1).strip())
        
        # Clean body - remove boilerplate paragraphs
        body = body_match.group(1).strip()
        body = clean_body_html(body)
        
        # Extract a clean lede from the cleaned body
        lede = extract_clean_lede(body)

        # EMERGENCY VALIDATION
        if len(body) < 100 or "Content not found" in body:
            print(f"  CRITICAL: Corruption detected in {path.name}. Content sample: {body[:30]}... SKIPPING.")
            continue

        publish_date = dt.datetime.strptime(date_match.group(1), "%Y-%m-%d")
        print(f"  -> Headline: '{headline[:60]}...'")
        
        # Regenerate with new standardized markers
        new_html = update_article_from_template(
            template_content=template_content,
            headline=headline,
            summary=summary,
            lede=lede,
            brief_html=body,
            publish_date=publish_date,
            output_filename=path.name
        )
        
        # Add navigation cards
        nav_links = get_nav_links(publish_date)
        new_html = replace_marker(new_html, "ARTICLE_NAVIGATION", nav_links)
        
        path.write_text(new_html, encoding="utf-8")
        print(f"  Successfully restored and hardened {path.name}")

if __name__ == "__main__":
    rebuild_all()
