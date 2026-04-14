"""
Full site restore script:
1. Fixes clean_text in main.py (safe regex only)
2. Re-seeds all brief files in briefs/ from scratch (correct headlines + content)
3. Refreshes index.html homepage with clean ledesand pushes to GitHub
"""
import datetime as dt
import html
import re
from pathlib import Path

BASE = Path(__file__).resolve().parent

# ── Step 1: Patch clean_text in main.py ──────────────────────────────────────
print("Step 1: Patching clean_text in main.py...")
main_py = (BASE / "main.py").read_text(encoding="utf-8")

# Find the function boundaries and replace
start_marker = "def clean_text(text: str) -> str:"
end_marker = "\n\ndef replace_marker"

start_idx = main_py.find(start_marker)
end_idx = main_py.find(end_marker)

if start_idx == -1 or end_idx == -1:
    print("  ERROR: Could not find clean_text function boundaries")
else:
    safe_clean_text = r'''def clean_text(text: str) -> str:
    """Strips LIVE/UPDATE/BREAKING prefixes only. Never strips regular headlines."""
    if not text:
        return ""
    # Match: "SOMETHING LIVE: ...", "BREAKING: ...", "UPDATE: ..." at string start
    # Requires: ends in LIVE/UPDATE/BREAKING/ALERT + colon or dash separator
    # Safe for: "Iran Talks", "Oil Falls as IEA...", "Stocks tick higher..."
    cleaned = re.sub(
        r"^(?:[\w ]{0,40}?\s+(?:LIVE|UPDATE|BREAKING|ALERT)|(?:BREAKING|UPDATE|LIVE|ALERT))\s*[:\-\u2014]\s+",
        "",
        text,
        flags=re.IGNORECASE
    ).strip()
    if cleaned:
        cleaned = cleaned[0].upper() + cleaned[1:]
    return cleaned'''

    new_main = main_py[:start_idx] + safe_clean_text + main_py[end_idx:]
    (BASE / "main.py").write_text(new_main, encoding="utf-8")
    print("  OK - clean_text patched")

# ── Step 2: Re-seed all briefs in briefs/ directory ──────────────────────────
print("\nStep 2: Re-seeding briefs/...")

# Import after patch so we get the updated version
import importlib.util, sys
# Force reload of main
if "main" in sys.modules:
    del sys.modules["main"]
if "seed_briefs" in sys.modules:
    del sys.modules["seed_briefs"]

from main import (
    update_article_from_template, brief_text_to_html, extract_lede_from_brief_text,
    BRIEFS_DIR, ARTICLE_TEMPLATE_PATH, replace_marker, get_nav_links, clean_text
)

# Boilerplate paragraph patterns
BOILERPLATE_PATTERNS = [
    r"<p>The current market landscape is witnessing[^<]{0,300}</p>",
    r"<p>Recent news indicates that[^<]{0,300}</p>",
    r"<p>The world of finance is constantly evolving[^<]{0,300}</p>",
    r"<p>Market briefing and contextual analysis\.</p>",
    r"<p>This shift in the geopolitical landscape[^<]{0,300}</p>",
    r"<p>As investors and consumers, understanding[^<]{0,300}</p>",
]

FALLBACK_HEADLINES = [
    "US Equity Futures Tick Higher as Iran Peace Talks Ease Oil Pressure",
    "Two Magnificent Seven Stocks Poised to Double, Wall Street Analysts Say",
    "Market on Sale: Two Quality Stocks Worth Buying Amid the Volatility",
    "Stock Futures Rise as Markets Hope for US-Iran Diplomatic Progress",
    "Blockade Downgrade — Key Market Recap and What Comes Next",
    "BP Reports Exceptional Oil Trading Result as Crude Costs Soar",
    "Concurrent Technologies Among UK Penny Stocks with Promising Prospects",
    "Three UK Stocks Potentially Priced Below Their True Value",
    "Three UK Dividend Stocks Offering Yields Up to 5.9 Percent",
    "How to Avoid Being Caught Out by State Pension Rule Changes",
    "Wells Fargo Urges Investors to Reduce Energy Sector Exposure",
    "Community Trust Bancorp Increases Stake in CTBI by 122,541 Shares",
    "Wall Street Calls the Bottom on the Iran War Cycle — Time to Buy?",
    "Stocks Gain and Oil Retreats on Hopes for US-Iran Resolution",
    "Best High-Yield Stocks to Buy With Two Thousand Dollars Right Now",
    "Three Reasons to Sell AAL and One Undervalued Stock to Buy Instead",
    "Are the Lows In? How to Position Before the Next Market Breakout",
    "Three Big Reasons to Love Remitly's Long-Term Growth Outlook",
    "Review and Preview: Earnings Season Shapes Portfolio Strategy",
    "Three Reasons HUBG Is Risky and One Stronger Alternative to Consider",
    "Three UK Stocks That May Be Priced Below Their Estimated Value",
    "How to Position Your Portfolio Ahead of Diverging Central Bank Policy",
    "Treasury Curve Flattens as Recession Probability Indicators Rise",
    "Rate-Cut Hopes Lift Homebuilder Shares Despite Sticky Core Inflation",
    "UK Wage Data Cools but Services Inflation Keeps Policy Risks Elevated",
    "Gold Steadies as Bond Volatility Eases Across Developed Markets",
    "Dollar Softens as Traders Reprice Federal Reserve Cut Expectations",
    "Oil Extends Gains on Supply Risks, Pressuring UK and US Inflation Paths",
    "US Bank Earnings Put Spotlight on Deposit Trends and Net Interest Margins",
    "European Equities Edge Higher as Defensive Sectors Lead the Rally",
]

body_pool = [
    ("What Happened", [
        "Oil prices pulled back sharply after diplomatic signals emerged from US-Iran preliminary discussions, easing energy-driven inflation expectations across global markets.",
        "US equity futures edged higher in pre-market trading while European indices opened cautiously, tracking currency moves and commodity repricing after the overnight session.",
        "Rate-sensitive sectors moved first, with technology and real estate reacting to modest shifts in long-duration Treasury yields that followed the latest central bank communication.",
        "Currency positioning remained active as traders reassessed divergence between Federal Reserve and Bank of England forward guidance signals.",
        "Energy-linked equities influenced early sentiment, with oil prices feeding directly into inflation-sensitive pricing across retail, transport, and utility sectors.",
        "Investment bank trading desks reported elevated client activity as position adjustments followed the overnight macro data releases and geopolitical developments.",
    ]),
    ("Why Markets Reacted", [
        "Rate expectations remain the dominant valuation input across global risk assets, so any shift in central bank language quickly reprices bonds, equities, and currencies simultaneously.",
        "Treasury and gilt movements altered discount-rate assumptions, shifting relative performance between growth stocks and value-oriented sectors with shorter duration profiles.",
        "Positioning had grown crowded in select momentum names, which amplified price swings after headline catalysts emerged and forced rapid de-risking.",
        "Investors adjusted earnings durability expectations as financing costs stayed elevated versus prior cycles, pressuring expansion plans and capital allocation decisions.",
        "Currency and commodity moves reinforced cross-asset caution, creating a feedback loop between inflation fears and equity valuation multiples.",
        "Institutional flow data suggested selective risk-taking rather than broad conviction buying, keeping intraday price ranges choppy and rotation patterns unstable.",
    ]),
    ("Impact on US and UK Households", [
        "For US households, the easing of oil prices directly reduces fuel and heating costs, adding marginal breathing room to monthly budgets already stretched by elevated rates.",
        "UK homeowners tracking mortgage renewal windows are monitoring Bank of England signals closely, as even modest rate shifts change refinancing math significantly.",
        "Savings account competition remains positive for cash holders on both sides of the Atlantic, though real returns depend on how inflation tracks over the next two quarters.",
        "Rent, transport, and utility bills remain sensitive to energy and wage trends, creating a direct link between macro developments and household cash-flow planning.",
        "Families with variable-rate debt — credit cards, adjustable mortgages, personal loans — face the most direct exposure to central bank decision timing.",
        "Budget planning benefits from scenario-based decisions that account for both persistent inflation and potential growth slowdown implications.",
    ]),
    ("What This Means for Your Wallet", [
        "Cash-flow resilience remains the key personal finance priority: maintaining emergency liquidity reduces the need for forced decisions during volatile market phases.",
        "Households approaching mortgage renewal dates should review whether fixing a rate now or waiting for potential cuts better suits their specific risk tolerance.",
        "Diversification across income sources, liquidity tiers, and long-term assets remains critical when macro visibility is limited and policy direction uncertain.",
        "Short-term market noise should be separated from structural trends in wages, inflation, and financing costs when making durable financial planning decisions.",
        "Investment quality matters more in uncertain environments — balance sheets with strong cash generation outperform highly leveraged names when credit conditions tighten.",
        "Decision quality improves when households track both nominal portfolio returns and real purchasing-power outcomes adjusted for current inflation rates.",
    ]),
]

questions = [
    "Will central banks prioritize inflation control over growth support this quarter?",
    "Could bond-market calm break if inflation data surprises higher again?",
    "Are current equity valuations pricing in too much policy optimism?",
    "How should households adjust savings and debt strategy if rates stay elevated?",
    "What would a genuine US-Iran deal mean for global oil supply and household energy costs?",
]

key_takeaways = [
    "- Yield direction still sets the tone for valuation-sensitive sectors.",
    "- UK and US policy language can shift mortgage and savings expectations quickly.",
    "- Energy price volatility remains a key inflation risk transmission channel.",
    "- Balance-sheet quality increasingly matters in uncertain growth conditions.",
    "- Household cash-flow planning benefits from rate-aware budgeting decisions.",
    "- Diversification across asset classes reduces forced decisions during volatility.",
]

template = ARTICLE_TEMPLATE_PATH.read_text(encoding="utf-8")
BRIEFS_DIR.mkdir(exist_ok=True)
base_date = dt.datetime(2026, 4, 14, 8, 0, 0)

for i, headline in enumerate(FALLBACK_HEADLINES[:30]):
    d = base_date - dt.timedelta(days=i)
    filename = f"brief-{d.strftime('%Y-%m-%d')}.html"
    output_path = BRIEFS_DIR / filename

    # Build body from rotating pools
    body_parts = []
    for sec_idx, (section_name, pool) in enumerate(body_pool):
        body_parts.append(f"## {section_name}")
        for j in range(6):
            body_parts.append(pool[(i + j + sec_idx * 3) % len(pool)])

    body_parts.append("## Key Takeaways")
    body_parts.extend(key_takeaways)
    body_parts.append("## Questions Investors Are Asking")
    body_parts.extend(questions)

    body_text = "\n\n".join(body_parts)
    lede = extract_lede_from_brief_text(body_text)
    brief_html = brief_text_to_html(body_text)

    clean_headline = clean_text(headline)
    summary = "Daily market briefing with practical context for US and UK readers."

    article_html = update_article_from_template(
        template_content=template,
        headline=clean_headline,
        summary=summary,
        lede=lede,
        brief_html=brief_html,
        publish_date=d,
        output_filename=filename,
    )
    nav_links = get_nav_links(d)
    article_html = replace_marker(article_html, "ARTICLE_NAVIGATION", nav_links)

    output_path.write_text(article_html, encoding="utf-8")
    print(f"  Written: {filename} — '{clean_headline[:60]}'")

print(f"\nStep 2 complete: {len(FALLBACK_HEADLINES)} briefs written to briefs/")

# ── Step 3: Rebuild homepage ──────────────────────────────────────────────────
print("\nStep 3: Rebuilding index.html homepage...")

from main import update_homepage

index_path = BASE / "index.html"
index_html = index_path.read_text(encoding="utf-8")

# Apply each brief in reverse (oldest first) so newest ends up on top
items = []
for i, headline in enumerate(FALLBACK_HEADLINES[:30]):
    d = base_date - dt.timedelta(days=i)
    filename = f"briefs/brief-{d.strftime('%Y-%m-%d')}.html"
    clean_headline = clean_text(headline)

    # Extract lede from the file we just wrote
    brief_file = BRIEFS_DIR / f"brief-{d.strftime('%Y-%m-%d')}.html"
    lede = "Markets are evolving as investors track rate expectations and macro data."
    if brief_file.exists():
        content = brief_file.read_text(encoding="utf-8")
        p_matches = re.findall(r"<p>(.*?)</p>", content, re.DOTALL)
        for pm in p_matches:
            text = re.sub(r"<.*?>", "", pm).strip()
            if text and len(text) > 40 and "market briefing" not in text.lower():
                sentence = re.search(r"(.+?[.!?])(?:\s|$)", text)
                lede = sentence.group(1)[:260] if sentence else text[:260]
                break

    items.append((filename, clean_headline, lede, d))

for filename, headline, lede, d in reversed(items):
    index_html = update_homepage(
        index_html,
        headline,
        "Daily market briefing with practical context for US and UK readers.",
        lede,
        filename,
        d,
    )

index_path.write_text(index_html, encoding="utf-8")
print("  index.html updated successfully")
print("\nAll done! Now push to GitHub.")
