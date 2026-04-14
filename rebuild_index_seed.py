import datetime as dt
import re
from pathlib import Path

from main import update_homepage, clean_text
from seed_briefs import FALLBACK_HEADLINES, get_live_finance_headlines

BASE = Path(__file__).resolve().parent
BRIEFS_DIR = BASE / "briefs"

# Known boilerplate phrases to skip when picking a lede
BOILERPLATE_PHRASES = [
    "the current market landscape is witnessing",
    "recent news indicates that",
    "the world of finance is constantly evolving",
    "a concise top-line briefing",
    "market briefing and contextual analysis",
    "daily market briefing with practical context",
    "markets are repricing rates, inflation",
    "us index futures traded in a tight range",
    "european equities opened cautious",
    "rate-sensitive sectors moved first",
    "currency positioning remained active",
    "energy-linked moves influenced sentiment",
    "pre-market flow showed rotation",
]


def is_boilerplate(text: str) -> bool:
    t = text.lower()
    return any(phrase in t for phrase in BOILERPLATE_PHRASES)


def get_clean_lede_from_brief(brief_path: Path) -> str:
    """Read a brief file and extract the first non-boilerplate sentence from the body."""
    content = brief_path.read_text(encoding="utf-8")
    # Extract all <p> content from article-body section
    body_match = re.search(r'<section id="article-body".*?>(.*?)</section>', content, re.DOTALL)
    if not body_match:
        return ""
    body = body_match.group(1)
    paragraphs = re.findall(r"<p[^>]*>(.*?)</p>", body, re.DOTALL)
    for para in paragraphs:
        text = re.sub(r"<.*?>", "", para).strip()
        if not text or is_boilerplate(text):
            continue
        # Return first sentence
        sentence_match = re.search(r"(.+?[.!?])(?:\s|$)", text)
        if sentence_match:
            return sentence_match.group(1).strip()[:260]
        if len(text) > 30:
            return text[:260]
    return ""


index_path = BASE / "index.html"
index_html = index_path.read_text(encoding="utf-8")

base_date = dt.datetime.now()
headlines = get_live_finance_headlines(limit=30)
if len(headlines) < 30:
    for title in FALLBACK_HEADLINES:
        if title.lower() not in {h.lower() for h in headlines}:
            headlines.append(title)
        if len(headlines) >= 30:
            break

items = []
for i, headline in enumerate(headlines[:30]):
    d = base_date - dt.timedelta(days=i)
    pattern = f"brief-{d.strftime('%Y-%m-%d')}*.html"
    
    match_found = False
    filename = ""
    brief_path = None
    
    for search_dir in [BRIEFS_DIR, BASE]:
        if not search_dir.exists():
            continue
        files = list(search_dir.glob(pattern))
        if files:
            brief_path = files[0]
            filename = str(brief_path.relative_to(BASE)).replace("\\", "/")
            match_found = True
            break
            
    if not match_found:
        filename = f"briefs/brief-{d.strftime('%Y-%m-%d')}.html"
    
    # Default fallback lede
    lede = "Markets are shifting as investors track rate expectations and macro data across US and UK assets."
    if brief_path and brief_path.exists():
        extracted = get_clean_lede_from_brief(brief_path)
        if extracted:
            lede = extracted

    items.append((filename, clean_text(headline), "Daily market briefing with practical context for US and UK readers.", lede, d))

for filename, headline, summary, lede, publish_date in reversed(items):
    index_html = update_homepage(index_html, headline, summary, lede, filename, publish_date)

index_path.write_text(index_html, encoding="utf-8")
print("Rebuilt index with 30 seeded entries.")
