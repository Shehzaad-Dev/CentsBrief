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
        
        # 3. Extract Lede
        lede_match = re.search(r"<!-- ARTICLE_LEDE -->(.*?)<!-- /ARTICLE_LEDE -->", content, re.DOTALL)
        if not lede_match:
            lede_match = re.search(r'bg-emerald/5 px-4 py-3 text-sm leading-relaxed text-slate-700 sm:text-base">\s*(.*?)\s*</p>', content, re.DOTALL)

        # 4. Extract Body (Infinite Resilience Mode)
        # We look for START and a flexible END tag (with or without slash)
        body_match = re.search(r"<!-- ARTICLE_CONTENT_START -->(.*?)(?:<!-- /?ARTICLE_CONTENT_END -->|<!-- /ARTICLE_CONTENT_START -->)", content, re.DOTALL)
        if not body_match:
            # Fallback to standard section ID
            body_match = re.search(r'<section id="article-body".*?>(.*?)</section>', content, re.DOTALL)
        
        # 5. Extract Date
        date_match = re.search(r"brief-(\d{4}-\d{2}-\d{2})", path.name)
        
        if not all([headline_match, summary_match, lede_match, body_match, date_match]):
            print(f"  ERROR: Skip {path.name} - Missing data fields.")
            continue
            
        headline = clean_text(headline_match.group(1).strip())
        summary = clean_text(summary_match.group(1).strip())
        lede = clean_text(lede_match.group(1).strip())
        body = body_match.group(1).strip()
            
        # Cleanup
        headline = re.sub(r'<.*?>', '', headline).strip()
        headline = re.sub(r'<!--.*?-->', '', headline).strip()
        body = re.sub(r'<!-- ARTICLE_CONTENT_(START|END) -->', '', body).strip()
        body = re.sub(r'<!-- /ARTICLE_CONTENT_(START|END) -->', '', body).strip()

        # EMERGENCY VALIDATION
        if len(body) < 100 or "Content not found" in body:
            print(f"  CRITICAL: Corruption detected in {path.name}. Content sample: {body[:30]}... SKIPPING.")
            continue

        publish_date = dt.datetime.strptime(date_match.group(1), "%Y-%m-%d")
        print(f"  -> Found body starting with: '{body[:30]}...'")
        
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
        
        # Add cards
        nav_links = get_nav_links(publish_date)
        new_html = replace_marker(new_html, "ARTICLE_NAVIGATION", nav_links)
        
        path.write_text(new_html, encoding="utf-8")
        print(f"  Successfully restored and hardened {path.name}")

if __name__ == "__main__":
    rebuild_all()
