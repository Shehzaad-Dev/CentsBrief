import datetime as dt
from pathlib import Path

import feedparser

from main import update_article_from_template, brief_text_to_html, extract_lede_from_brief_text

BASE = Path(__file__).resolve().parent
template = (BASE / "article-template.html").read_text(encoding="utf-8")

base_date = dt.datetime(2026, 4, 13, 8, 0, 0)

FALLBACK_HEADLINES = [
    "S&P 500 Holds Record Range as Treasury Yields Pause Ahead of CPI",
    "FTSE 100 Gains on Energy Rally While Sterling Traders Watch BoE Signals",
    "US 10-Year Yield Pullback Lifts Rate-Sensitive Stocks and REITs",
    "Bank of England Commentary Reframes UK Mortgage Outlook for Summer",
    "Nasdaq Advances as AI Leaders Offset Weakness in Consumer Cyclicals",
    "Dollar Index Softens as Traders Reprice Fed Cut Expectations",
    "Oil Extends Gains on Supply Risks, Pressuring UK and US Inflation Paths",
    "Gold Steadies as Bond Volatility Eases Across Major Developed Markets",
    "US Bank Earnings Spotlight Deposit Trends and Net Interest Margins",
    "European Equities Edge Higher as Defensive Sectors Outperform",
    "Retail Sales Surprise Reshapes Consumer Spending Outlook in the US",
    "UK Wage Data Cools but Services Inflation Keeps Policy Risks Elevated",
    "Treasury Auction Demand Sends Mixed Signals on Long-Term Rate Direction",
    "Mega-Cap Tech Momentum Faces Valuation Test Into Earnings Season",
    "Small Caps Rebound as Funding Cost Pressures Temporarily Ease",
    "Energy and Financials Lead Rotation as Growth Stocks Consolidate",
    "Credit Spreads Remain Calm Despite Rising Geopolitical Risk Premium",
    "Housing Starts and Mortgage Rates Flash Mixed Signals for Homebuyers",
    "GBP/USD Volatility Rises as UK Data Calendar Heats Up",
    "US Labor Market Resilience Complicates Timing of Policy Easing",
    "Dividend Stocks Regain Attention as Bond Yields Trade Sideways",
    "Global Manufacturing Indicators Point to Fragile Reacceleration",
    "Consumer Confidence Rebound Supports Risk Assets in Early Trade",
    "Healthcare and Utilities Attract Flows as Investors Balance Risk",
    "Commodities Strength Rekindles Inflation Hedge Positioning",
    "UK Mid-Caps Outperform as Domestic Demand Expectations Improve",
    "US Corporate Guidance Signals Margin Pressure Into Year-End",
    "Foreign Exchange Markets Brace for Diverging Central Bank Paths",
    "Treasury Curve Flattens as Growth Expectations Moderate",
    "Rate-Cut Hopes Lift Homebuilder Shares Despite Sticky Inflation"
]

RSS_FEEDS = [
    "https://feeds.finance.yahoo.com/rss/2.0/headline?s=%5EGSPC,%5EFTSE&region=US&lang=en-US",
    "https://www.cnbc.com/id/100003114/device/rss/rss.html",
    "https://feeds.a.dj.com/rss/RSSMarketsMain.xml",
]


def get_live_finance_headlines(limit: int = 30) -> list[str]:
    collected: list[str] = []
    seen: set[str] = set()
    for url in RSS_FEEDS:
        parsed = feedparser.parse(url)
        for entry in parsed.entries:
            title = str(entry.get("title", "")).strip()
            if not title:
                continue
            key = title.lower()
            if key in seen:
                continue
            seen.add(key)
            collected.append(title)
            if len(collected) >= limit:
                return collected
    return collected

headlines = get_live_finance_headlines(limit=30)
if len(headlines) < 30:
    for title in FALLBACK_HEADLINES:
        if title.lower() not in {h.lower() for h in headlines}:
            headlines.append(title)
        if len(headlines) >= 30:
            break

for i, headline in enumerate(headlines[:30]):
    d = base_date - dt.timedelta(days=i)
    filename = f"brief-{d.strftime('%Y-%m-%d')}.html"
    summary = "Daily market briefing with practical context for US and UK readers."
    happened_pool = [
        "US index futures traded in a tight range while investors digested mixed macro signals and commodity volatility.",
        "European equities opened cautious as bond markets repriced inflation risk into the next policy window.",
        "Rate-sensitive sectors moved first, with technology and real estate reacting to modest shifts in long-duration yields.",
        "Currency positioning remained active as traders reassessed divergence between Federal Reserve and Bank of England signaling.",
        "Energy-linked moves influenced sentiment early, with oil direction feeding directly into inflation-sensitive pricing.",
        "Pre-market flow showed rotation into quality balance sheets, especially where cash generation remained resilient."
    ]
    reacted_pool = [
        "Markets reacted because rate expectations remain the dominant valuation input across global risk assets.",
        "Treasury and gilt movements altered discount-rate assumptions, shifting relative performance between growth and value.",
        "Positioning looked crowded in select momentum names, which amplified price swings after headline surprises.",
        "Investors adjusted expectations for earnings durability as financing costs stayed elevated versus prior cycles.",
        "FX and commodities reinforced cross-asset caution, creating a feedback loop between inflation fears and equity multiples.",
        "Institutional flow suggested selective risk-taking rather than broad conviction, keeping intraday ranges choppy."
    ]
    household_pool = [
        "For households, persistent rate uncertainty affects mortgage affordability, refinancing opportunities, and monthly debt servicing.",
        "Savings account competition remains positive for cash holders, but real returns depend on inflation-adjusted outcomes.",
        "Credit-card and personal-loan pricing still tracks higher funding benchmarks, pressuring discretionary budgets.",
        "Rent, transport, and utilities remain sensitive to energy and wage trends, linking macro shifts to daily spending.",
        "Families balancing fixed and variable debt should monitor central-bank messaging for potential repricing windows.",
        "Budget planning benefits from scenario-based decisions that consider both sticky inflation and slower growth risks."
    ]
    wallet_pool = [
        "Cash-flow resilience matters: maintaining emergency liquidity can reduce forced decisions during volatile market phases.",
        "Households may benefit from reviewing debt terms, renewal dates, and savings ladders as rate expectations evolve.",
        "Diversification across income, liquidity, and long-term assets remains critical when macro visibility is limited.",
        "Short-term market noise should be separated from structural trends in wages, inflation, and financing costs.",
        "The key practical question is not only where rates are today, but how quickly they can change borrowing math.",
        "Decision quality improves when households track both nominal returns and real purchasing-power outcomes."
    ]
    sections = [
        ("What Happened", happened_pool),
        ("Why Markets Reacted", reacted_pool),
        ("Impact on US and UK Households", household_pool),
        ("What This Means for Your Wallet", wallet_pool),
    ]
    body_parts = []
    for section_idx, (section_name, pool) in enumerate(sections):
        body_parts.append(f"## {section_name}")
        for j in range(12):
            body_parts.append(pool[(i + j + section_idx) % len(pool)])
    body_parts.append("## Key Takeaways")
    body_parts.extend(
        [
            "- Yield direction still sets the tone for valuation-sensitive sectors.",
            "- UK and US policy language can shift mortgage and savings expectations quickly.",
            "- Energy volatility remains a key inflation risk channel.",
            "- Balance-sheet quality is increasingly important in uncertain growth conditions.",
            "- Household cash-flow planning benefits from rate-aware budgeting decisions.",
        ]
    )
    body_parts.append("## Questions Investors Are Asking")
    body_parts.extend(
        [
            "Will central banks prioritize inflation control over growth support this quarter?",
            "Could bond-market calm break if inflation data surprises higher again?",
            "Are current equity valuations pricing in too much policy optimism?",
            "How should households adjust savings and debt strategy if rates stay elevated?",
        ]
    )
    body = "\n\n".join(body_parts)
    lede = extract_lede_from_brief_text(body)
    article_html = update_article_from_template(
        template_content=template,
        headline=headline,
        summary=summary,
        lede=lede,
        brief_html=brief_text_to_html(body),
        publish_date=d,
        output_filename=filename,
    )
    (BASE / filename).write_text(article_html, encoding="utf-8")

print("Generated 30 brief pages.")
