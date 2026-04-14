import datetime as dt
import re
from pathlib import Path

from main import update_homepage
from seed_briefs import FALLBACK_HEADLINES, get_live_finance_headlines

BASE = Path(__file__).resolve().parent
index_path = BASE / "index.html"
index_html = index_path.read_text(encoding="utf-8")

base_date = dt.datetime.now()
headlines = get_live_finance_headlines(limit=30)
BRIEFS_DIR = BASE / "briefs"
if len(headlines) < 30:
    for title in FALLBACK_HEADLINES:
        if title.lower() not in {h.lower() for h in headlines}:
            headlines.append(title)
        if len(headlines) >= 30:
            break

items = []
for i, headline in enumerate(headlines[:30]):
    d = base_date - dt.timedelta(days=i)
    # Search for files starting with brief-YYYY-MM-DD
    pattern = f"brief-{d.strftime('%Y-%m-%d')}*.html"
    
    match_found = False
    filename = ""
    brief_path = None
    
    # Check parent directory and briefs/ directory
    for search_dir in [BASE, BRIEFS_DIR]:
        if not search_dir.exists(): continue
        files = list(search_dir.glob(pattern))
        if files:
            brief_path = files[0]
            filename = str(brief_path.relative_to(BASE)).replace("\\", "/")
            match_found = True
            break
            
    if not match_found:
        filename = f"briefs/brief-{d.strftime('%Y-%m-%d')}.html"
    
    lede = "Markets are repricing rates, inflation, and risk appetite across US and UK assets."
    if brief_path and brief_path.exists():
        content = brief_path.read_text(encoding="utf-8")
        p_match = re.search(r"<section id=\"article-body\".*?<p>(.*?)</p>", content, flags=re.DOTALL)
        if p_match:
            raw = p_match.group(1)
            cleaned = re.sub(r"<.*?>", "", raw).strip()
            if cleaned:
                lede = cleaned
    items.append(
        (
            filename,
            headline,
            "Daily market briefing with practical context for US and UK readers.",
            lede,
            d,
        )
    )

for filename, headline, summary, lede, publish_date in reversed(items):
    index_html = update_homepage(index_html, headline, summary, lede, filename, publish_date)

index_path.write_text(index_html, encoding="utf-8")
print("Rebuilt index with 30 seeded entries.")
