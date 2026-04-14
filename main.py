import datetime as dt
import html
import json
import os
import re
from pathlib import Path
from typing import List, Tuple

import feedparser
import requests


BASE_DIR = Path(__file__).resolve().parent
INDEX_PATH = BASE_DIR / "index.html"
ARTICLE_TEMPLATE_PATH = BASE_DIR / "article-template.html"
TARGET_WORD_COUNT = 1000
RETENTION_DAYS = int(os.getenv("BRIEF_RETENTION_DAYS", "60"))
DEFAULT_FEED_URL = "https://feeds.finance.yahoo.com/rss/2.0/headline?s=%5EGSPC,%5EFTSE&region=US&lang=en-US"
SITE_BASE_URL = os.getenv("SITE_BASE_URL", "https://centsbreif.online").rstrip("/")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")


def replace_marker(content: str, marker_name: str, value: str, keep_markers: bool = False) -> str:
    pattern = re.compile(
        rf"(<!--\s*{re.escape(marker_name)}\s*-->)(.*?)(<!--\s*/{re.escape(marker_name)}\s*-->)",
        re.DOTALL,
    )
    if keep_markers:
        return pattern.sub(lambda m: f"{m.group(1)}{value}{m.group(3)}", content)
    else:
        return pattern.sub(lambda m: value, content)


def fetch_top_finance_news(feed_url: str, limit: int = 3) -> List[str]:
    parsed = feedparser.parse(feed_url)
    if parsed.bozo:
        raise RuntimeError(f"RSS feed parsing failed: {parsed.bozo_exception}")
    entries = parsed.entries[:limit]
    if not entries:
        raise RuntimeError("No entries found in RSS feed.")
    return [entry.get("title", "").strip() for entry in entries if entry.get("title")]


def ask_groq_for_brief(titles: List[str]) -> Tuple[str, str, str]:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("Missing GROQ_API_KEY environment variable.")

    titles_block = "\n".join([f"- {t}" for t in titles])
    prompt = f"""
You are a senior financial editor for a US/UK market publication.

Using ONLY these top headlines:
{titles_block}

Create one integrated brief for retail readers.
Requirements:
1) Write approximately {TARGET_WORD_COUNT} words.
2) Professional but accessible language.
3) Focus on "information gain": explain why each development matters for personal money decisions.
4) Structure the brief with clear markdown headings using this pattern:
   - ## What Happened
   - ## Why Markets Reacted
   - ## Impact on US and UK Households
   - ## What This Means for Your Wallet
   - ## Key Takeaways
   - ## Questions Investors Are Asking
5) Avoid financial advice promises, hype, and sensationalism.
6) Under "Key Takeaways", include 4-6 bullet points using markdown '-' lines.
7) Under "Questions Investors Are Asking", include 3-5 lines that end with a question mark.
8) Do not repeat the same sentence or paragraph wording.

Output EXACTLY in this format:
HEADLINE: <single compelling financial-news headline under 110 chars; no numbering, no generic labels>
SUMMARY: <1-2 sentence summary under 220 chars>
BRIEF:
<plain text brief with multiple paragraphs and at least 1 H2 marker written as: ## Subheading>
""".strip()

    base_messages = [
        {"role": "system", "content": "You are a precise financial news editor."},
        {"role": "user", "content": prompt},
    ]

    for attempt in range(1, 4):
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": GROQ_MODEL,
                "messages": base_messages,
                "temperature": 0.4,
            },
            timeout=120,
        )
        if response.status_code >= 400:
            raise RuntimeError(f"Groq API error {response.status_code}: {response.text[:400]}")

        payload = response.json()
        text = (
            payload.get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
            .strip()
        )
        if not text:
            continue

        headline_match = re.search(r"HEADLINE:\s*(.+)", text)
        summary_match = re.search(r"SUMMARY:\s*(.+)", text)
        brief_match = re.search(r"BRIEF:\s*(.*)$", text, re.DOTALL)
        if not headline_match or not summary_match or not brief_match:
            continue

        headline = headline_match.group(1).strip()
        summary = summary_match.group(1).strip()
        brief = brief_match.group(1).strip()
        if len(re.findall(r"\b\w+\b", brief)) >= 950:
            return headline, summary, brief

        base_messages = [
            {"role": "system", "content": "You are a precise financial news editor."},
            {"role": "user", "content": prompt},
            {"role": "assistant", "content": text},
            {
                "role": "user",
                "content": (
                    "The previous brief is too short. Expand each section with more concrete market details, "
                    "household implications, and examples so BRIEF reaches at least 1000 words while keeping "
                    "the exact same HEADLINE/SUMMARY/BRIEF output format."
                ),
            },
        ]

    raise RuntimeError("Generated brief is below minimum required length (1000-word target).")


def brief_text_to_html(brief_text: str) -> str:
    lines = [line.strip() for line in brief_text.splitlines() if line.strip()]
    blocks: List[str] = []
    para_buffer: List[str] = []
    in_list = False

    def close_list() -> None:
        nonlocal in_list
        if in_list:
            blocks.append("</ul>")
            in_list = False

    def flush_paragraph() -> None:
        if para_buffer:
            close_list()
            paragraph = " ".join(para_buffer).strip()
            sentences = re.split(r"(?<=[.!?])\s+", paragraph)
            chunk: List[str] = []
            for sentence in sentences:
                if not sentence:
                    continue
                chunk.append(sentence)
                if len(chunk) >= 2:
                    blocks.append(f"<p>{html.escape(' '.join(chunk).strip())}</p>")
                    chunk = []
            if chunk:
                blocks.append(f"<p>{html.escape(' '.join(chunk).strip())}</p>")
            para_buffer.clear()

    for line in lines:
        if line.startswith("## "):
            flush_paragraph()
            close_list()
            heading_text = line[3:].strip()
            heading_class = "mt-10 border-l-4 border-emerald pl-3 text-xl font-extrabold text-navy sm:text-2xl"
            if heading_text.lower() in {"key takeaways", "questions investors are asking"}:
                heading_class = "mt-10 border-l-4 border-emerald pl-3 text-xl font-extrabold text-emerald sm:text-2xl"
            blocks.append(f'<h2 class="{heading_class}">{html.escape(heading_text)}</h2>')
            continue
        if line.startswith("### "):
            flush_paragraph()
            close_list()
            blocks.append(f"<h3>{html.escape(line[4:].strip())}</h3>")
            continue
        if line.startswith("- "):
            flush_paragraph()
            if not in_list:
                blocks.append('<ul class="list-disc space-y-2 rounded-lg border border-slate-200 bg-slate-50 p-4 pl-8 marker:text-emerald">')
                in_list = True
            blocks.append(f"<li><strong class=\"text-navy\">{html.escape(line[2:].strip())}</strong></li>")
            continue
        if line.endswith("?"):
            flush_paragraph()
            close_list()
            blocks.append(
                f'<p class="rounded-md bg-emerald/10 px-3 py-2"><strong class="text-base font-extrabold text-emerald sm:text-lg">{html.escape(line)}</strong></p>'
            )
            continue
        para_buffer.append(line)

    flush_paragraph()
    close_list()
    return "\n        ".join(blocks)


def extract_lede_from_brief_text(brief_text: str) -> str:
    plain = re.sub(r"^\s*##\s+.*$", "", brief_text, flags=re.MULTILINE)
    plain = re.sub(r"^\s*-\s+", "", plain, flags=re.MULTILINE)
    plain = re.sub(r"\s+", " ", plain).strip()
    if not plain:
        return "Daily market briefing with practical context for US and UK readers."
    sentence_match = re.search(r"(.+?[.!?])(?:\s|$)", plain)
    lede = sentence_match.group(1).strip() if sentence_match else plain[:220].strip()
    return lede[:260]


def minify_html(content: str) -> str:
    # Remove HTML comments BUT preserve the structural markers the script needs for future runs
    # Markers like <!-- RECENT_BRIEFS_START --> or <!-- HERO_HEADLINE -->
    content = re.sub(r"<!--\s*(?!(?:RECENT_BRIEFS|HERO_HEADLINE|HERO_SUMMARY|ARTICLE|CANONICAL|JSON_LD|LAST_UPDATED|RELATED_INSIGHTS|SNAPSHOT|MODIFIED|PUBLISHED)).*?-->", "", content, flags=re.DOTALL)
    # Remove whitespace between tags
    content = re.sub(r">\s+<", "><", content)
    return content.strip()


def generate_robots_txt() -> None:
    content = (
        "User-agent: *\n"
        "Allow: /\n"
        f"Sitemap: {SITE_BASE_URL}/sitemap.xml\n"
    )
    (BASE_DIR / "robots.txt").write_text(content, encoding="utf-8")


def get_related_insights(today: dt.datetime) -> str:
    briefs = []
    for path in BASE_DIR.glob("brief-????-??-??.html"):
        date_str = path.stem.replace("brief-", "")
        if date_str == today.strftime("%Y-%m-%d"):
            continue
        try:
            brief_date = dt.datetime.strptime(date_str, "%Y-%m-%d")
            briefs.append((brief_date, path.stem))
        except ValueError:
            continue

    briefs.sort(key=lambda x: x[0], reverse=True)
    targets = briefs[:3]

    if not targets:
        return ""

    links = []
    for _, slug in targets:
        headline = slug.replace("-", " ").title()
        try:
            file_content = (BASE_DIR / f"{slug}.html").read_text(encoding="utf-8")
            match = re.search(r"<!-- ARTICLE_HEADLINE -->(.*?)<!-- /ARTICLE_HEADLINE -->", file_content, re.DOTALL)
            if match:
                headline = match.group(1).strip()
        except:
            pass
        links.append(f'<li><a href="{slug}" class="text-emerald font-semibold hover:underline">{headline}</a></li>')

    links_html = "\n          ".join(links)
    return f"""
      <section class="mt-12 border-t border-slate-100 pt-8">
        <h3 class="text-xl font-extrabold text-navy">Related Market Insights</h3>
        <ul class="mt-4 space-y-3 list-disc pl-5">
          {links_html}
        </ul>
      </section>
    """


def generate_json_ld(headline: str, summary: str, brief_text: str, publish_date: dt.datetime, canonical_url: str) -> str:
    published_iso = publish_date.strftime("%Y-%m-%dT%H:%M:%SZ")
    desc = (summary if len(summary) > 40 else brief_text[:200]).strip()
    desc = re.sub(r"<[^>]+>", "", desc)  # strip any html
    desc = re.sub(r"##\s+", "", desc).replace("\n", " ")[:160].strip() + "..."

    schema = {
        "@context": "https://schema.org",
        "@type": "FinancialNewsArticle",
        "mainEntityOfPage": {"@type": "WebPage", "@id": canonical_url},
        "headline": headline,
        "description": desc,
        "image": [f"{SITE_BASE_URL}/assets/og-default.jpg"],
        "datePublished": published_iso,
        "dateModified": published_iso,
        "author": {
            "@id": f"{SITE_BASE_URL}/#insight-team",
            "@type": "Organization",
            "name": "CentsBrief Market Insight Team",
        },
        "publisher": {
            "@type": "Organization",
            "name": "CentsBrief.online",
            "logo": {"@type": "ImageObject", "url": f"{SITE_BASE_URL}/assets/logo-512.png"},
        },
        "articleSection": "Markets",
        "inLanguage": "en-US",
        "isAccessibleForFree": True,
    }
    return f'<script type="application/ld+json">\n{json.dumps(schema, indent=2)}\n</script>'


def update_article_from_template(
    template_content: str,
    headline: str,
    summary: str,
    lede: str,
    brief_html: str,
    publish_date: dt.datetime,
    output_filename: str,
) -> str:
    published_iso = publish_date.strftime("%Y-%m-%dT%H:%M:%SZ")
    published_human = publish_date.strftime("%B %d, %Y")
    clean_filename = output_filename.replace(".html", "")
    canonical_url = f"{SITE_BASE_URL}/{clean_filename}"
    read_time = f"{max(4, round(TARGET_WORD_COUNT / 220))} min read"

    json_ld = generate_json_ld(headline, summary, brief_html, publish_date, canonical_url)
    related_html = get_related_insights(publish_date)

    article_html = template_content
    article_html = replace_marker(article_html, "ARTICLE_TITLE", f"{headline} | CentsBrief")
    article_html = replace_marker(article_html, "ARTICLE_DESCRIPTION", summary)
    article_html = replace_marker(article_html, "CANONICAL_URL", canonical_url)
    article_html = replace_marker(article_html, "JSON_LD_SCHEMA", json_ld)
    article_html = replace_marker(article_html, "OG_TITLE", f"{headline} | CentsBrief")
    article_html = replace_marker(article_html, "OG_DESCRIPTION", summary)
    article_html = replace_marker(article_html, "OG_URL", canonical_url)
    article_html = replace_marker(article_html, "TWITTER_TITLE", f"{headline} | CentsBrief")
    article_html = replace_marker(article_html, "TWITTER_DESCRIPTION", summary)
    article_html = replace_marker(article_html, "PUBLISHED_ISO", published_iso)
    article_html = replace_marker(article_html, "MODIFIED_ISO", published_iso)
    article_html = replace_marker(article_html, "ARTICLE_HEADLINE", headline)
    article_html = replace_marker(article_html, "ARTICLE_LEDE", lede)
    article_html = replace_marker(article_html, "ARTICLE_AUTHOR", "CentsBrief Market Insight Team")
    article_html = replace_marker(article_html, "PUBLISHED_HUMAN", published_human)
    article_html = replace_marker(article_html, "LAST_UPDATED", "05:00 UTC")
    article_html = replace_marker(article_html, "READ_TIME", read_time)
    article_html = replace_marker(article_html, "ARTICLE_CONTENT_START", "ARTICLE_CONTENT_START")
    article_html = replace_marker(article_html, "ARTICLE_CONTENT_END", "ARTICLE_CONTENT_END")
    article_html = replace_marker(article_html, "RELATED_INSIGHTS", related_html)

    article_html = re.sub(
        r"(<!--\s*ARTICLE_CONTENT_START\s*-->)(.*?)(<!--\s*ARTICLE_CONTENT_END\s*-->)",
        rf"\1\n        {brief_html}\n        \3",
        article_html,
        flags=re.DOTALL,
    )
    return minify_html(article_html)


def build_brief_card(headline: str, lede: str, output_filename: str, publish_date: dt.datetime) -> str:
    date_label = publish_date.strftime("%b %d, %Y")
    safe_headline = html.escape(headline)
    safe_summary = html.escape(lede)
    return f"""
      <article class="rounded-xl bg-white p-5 shadow-sm ring-1 ring-slate-200 transition hover:shadow-md">
        <p class="text-xs font-semibold uppercase tracking-[0.14em] text-emerald">{date_label}</p>
        <h3 class="mt-2 text-lg font-bold leading-snug">{safe_headline}</h3>
        <p class="mt-3 text-sm leading-relaxed text-slate-600">{safe_summary}</p>
        <a href="{output_filename.replace('.html', '')}" class="mt-4 inline-block text-sm font-semibold text-emerald hover:underline">Read More</a>
      </article>
    """.strip()


def update_homepage(index_html: str, headline: str, summary: str, lede: str, output_filename: str, publish_date: dt.datetime) -> str:
    updated = index_html
    updated = replace_marker(updated, "HERO_HEADLINE", headline, keep_markers=True)
    updated = replace_marker(updated, "HERO_SUMMARY", lede, keep_markers=True)

    updated = re.sub(
        r'(<a href=")[^"]*(" class="mt-6 inline-flex items-center rounded-md bg-emerald)',
        rf'\1{output_filename.replace(".html", "")}\2',
        updated,
        count=1,
    )

    match = re.search(
        r"(<!--\s*RECENT_BRIEFS_START\s*-->)(.*?)(<!--\s*RECENT_BRIEFS_END\s*-->)",
        updated,
        flags=re.DOTALL,
    )
    if not match:
        raise RuntimeError("Could not find RECENT_BRIEFS_START/END markers in index.html.")

    region = match.group(2)
    existing_cards = re.findall(r"<article\b.*?</article>", region, flags=re.DOTALL)
    filtered_cards = []
    for card in existing_cards:
        href_match = re.search(r'href="(brief-\d{4}-\d{2}-\d{2})"|href="(brief-\d{4}-\d{2}-\d{2})\.html"', card)
        if not href_match:
            continue
        href = href_match.group(1) or href_match.group(2)
        if href == output_filename.replace(".html", ""):
            continue
        # Also need to make sure we check for the actual file
        if not (BASE_DIR / f"{href}.html").exists():
            continue
        filtered_cards.append(card)
    existing_cards = filtered_cards

    new_card = build_brief_card(headline, lede, output_filename, publish_date)
    final_cards = [new_card] + existing_cards
    final_cards = final_cards[:30]
    cards_html = "\n        ".join(final_cards)
    new_grid = f'\n      <div class="grid gap-5 md:grid-cols-2 lg:grid-cols-3">\n        {cards_html}\n      </div>\n      '

    return updated[: match.start(2)] + new_grid + updated[match.end(2) :]


def cleanup_old_briefs(today: dt.datetime, retention_days: int) -> list[str]:
    cutoff = today.date() - dt.timedelta(days=retention_days)
    deleted: list[str] = []
    for path in BASE_DIR.glob("brief-????-??-??.html"):
        date_match = re.search(r"brief-(\d{4}-\d{2}-\d{2})\.html$", path.name)
        if not date_match:
            continue
        try:
            page_date = dt.datetime.strptime(date_match.group(1), "%Y-%m-%d").date()
        except ValueError:
            continue
        if page_date < cutoff:
            path.unlink(missing_ok=True)
            deleted.append(path.name)
    return deleted


def generate_sitemap(today: dt.datetime) -> None:
    exclude_files = {
        "404.html", "article-template.html",
        "cookie-policy.html", "disclaimer.html", 
        "legal.html", "legal-bundle.html", 
        "privacy-policy.html", "terms-of-service.html"
    }
    
    lastmod = today.strftime("%Y-%m-%d")
    urls = []
    
    # Ensure stable sorting for reproducibility
    html_files = sorted([f for f in BASE_DIR.glob("*.html") if f.name not in exclude_files])
    
    for path in html_files:
        clean_name = path.name.replace(".html", "")
        if clean_name == "index":
            loc = f"{SITE_BASE_URL}/"
            priority = "1.0"
        else:
            loc = f"{SITE_BASE_URL}/{clean_name}"
            priority = "0.8"
            
        urls.append(
            f"  <url>\n"
            f"    <loc>{loc}</loc>\n"
            f"    <lastmod>{lastmod}</lastmod>\n"
            f"    <priority>{priority}</priority>\n"
            f"  </url>"
        )
        
    sitemap_content = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "\n".join(urls) +
        '\n</urlset>\n'
    )
    
    sitemap_path = BASE_DIR / "sitemap.xml"
    sitemap_path.write_text(sitemap_content, encoding="utf-8")


def main() -> None:
    feed_url = os.getenv("RSS_FEED_URL") or DEFAULT_FEED_URL
    today = dt.datetime.now(dt.UTC).replace(tzinfo=None)
    output_filename = f"brief-{today.strftime('%Y-%m-%d')}.html"
    output_path = BASE_DIR / output_filename

    if not ARTICLE_TEMPLATE_PATH.exists() or not INDEX_PATH.exists():
        raise FileNotFoundError("Missing required files: article-template.html and/or index.html")

    titles = fetch_top_finance_news(feed_url=feed_url, limit=3)
    headline, summary, brief_text = ask_groq_for_brief(titles)
    lede = extract_lede_from_brief_text(brief_text)
    brief_html = brief_text_to_html(brief_text)

    template_content = ARTICLE_TEMPLATE_PATH.read_text(encoding="utf-8")
    article_html = update_article_from_template(
        template_content=template_content,
        headline=headline,
        summary=summary,
        lede=lede,
        brief_html=brief_html,
        publish_date=today,
        output_filename=output_filename,
    )
    output_path.write_text(article_html, encoding="utf-8")

    deleted_files = cleanup_old_briefs(today=today, retention_days=RETENTION_DAYS)

    index_content = INDEX_PATH.read_text(encoding="utf-8")
    updated_index = update_homepage(
        index_html=index_content,
        headline=headline,
        summary=summary,
        lede=lede,
        output_filename=output_filename,
        publish_date=today,
    )
    INDEX_PATH.write_text(minify_html(updated_index), encoding="utf-8")

    generate_sitemap(today)
    generate_robots_txt()

    print(f"Created: {output_filename}")
    print("Updated: index.html")
    print("Generated: sitemap.xml & robots.txt")
    print("Headlines used:")
    for item in titles:
        print(f"- {item}")
    if deleted_files:
        print("Deleted old brief pages:")
        for item in deleted_files:
            print(f"- {item}")


if __name__ == "__main__":
    main()
