"""MGID sitewide integration: head loader, widget slots, lazy load, page patching."""
from __future__ import annotations

import html
import json
import re
from pathlib import Path
from typing import Literal

BASE_DIR = Path(__file__).resolve().parent
MGID_CONFIG_PATH = BASE_DIR / "mgid.config.json"

PageKind = Literal["home", "article", "static"]

STATIC_PAGES = {
    "about.html",
    "calculator.html",
    "contact.html",
    "legal.html",
    "legal-bundle.html",
    "cookie-policy.html",
    "disclaimer.html",
    "privacy-policy.html",
    "terms-of-service.html",
    "editorial-policy.html",
    "404.html",
}

SKIP_FILES = {
    "article-template.html",
    "index.ads-merged.html",
    "monetag.html",
    "amp-mgid.html",
}

MGID_STYLES = '<link rel="stylesheet" href="/assets/mgid.css" />'
MGID_LOADER = '<script src="/assets/mgid-lazy.js" defer></script>'


def load_mgid_config() -> dict:
    defaults = {
        "site_id": "1097226",
        "widget_id": "2017365",
        "amp_website": "1097226",
        "amp_widget": "2017365",
    }
    if not MGID_CONFIG_PATH.exists():
        return defaults
    try:
        data = json.loads(MGID_CONFIG_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return defaults
    return {**defaults, **{k: v for k, v in data.items() if not str(k).startswith("_")}}


def mgid_widget_id(cfg: dict | None = None) -> str:
    cfg = cfg or load_mgid_config()
    return str(cfg.get("widget_id") or cfg.get("in_article_widget_id") or "2017365").strip()


def mgid_site_id(cfg: dict | None = None) -> str:
    cfg = cfg or load_mgid_config()
    return str(cfg.get("site_id") or "1097226").strip()


def mgid_head_snippet(cfg: dict | None = None) -> str:
    sid = html.escape(mgid_site_id(cfg))
    return f'<script src="https://jsc.mgid.com/site/{sid}.js" async></script>'


def mgid_head_bundle(cfg: dict | None = None) -> str:
    return MGID_STYLES + mgid_head_snippet(cfg)


def mgid_slot(
    slot_id: str,
    *,
    eager: bool = False,
    layout: str = "infeed",
    cfg: dict | None = None,
) -> str:
    wid = html.escape(mgid_widget_id(cfg))
    mode = "mgid-slot--eager" if eager else "mgid-slot--lazy"
    return (
        f'<div class="mgid-ad-slot {mode} mgid-layout--{layout}" '
        f'data-mgid-slot="{html.escape(slot_id)}" aria-label="Advertisement">'
        f'<div data-type="_mgwidget" data-widget-id="{wid}"></div></div>'
    )


def home_slots(cfg: dict | None = None) -> dict[str, str]:
    return {
        "top": mgid_slot("home-top", eager=True, layout="banner", cfg=cfg),
        "after_hero": mgid_slot("home-after-hero", layout="infeed", cfg=cfg),
        "sidebar": mgid_slot("home-sidebar", eager=True, layout="sidebar", cfg=cfg),
        "pre_footer": mgid_slot("home-pre-footer", layout="infeed", cfg=cfg),
    }


def article_slots(cfg: dict | None = None) -> dict[str, str]:
    return {
        "top": mgid_slot("article-top", eager=True, layout="banner", cfg=cfg),
        "under_lede": mgid_slot("article-under-lede", eager=True, layout="infeed", cfg=cfg),
        "in_article": mgid_slot("article-in-article", layout="infeed", cfg=cfg),
        "mid": mgid_slot("article-mid", layout="infeed", cfg=cfg),
        "bottom": mgid_slot("article-bottom", layout="infeed", cfg=cfg),
        "sidebar": mgid_slot("article-sidebar", eager=True, layout="sidebar", cfg=cfg),
    }


def static_slots(cfg: dict | None = None) -> dict[str, str]:
    return {
        "top": mgid_slot("static-top", eager=True, layout="banner", cfg=cfg),
        "mid": mgid_slot("static-mid", layout="infeed", cfg=cfg),
    }


def strip_old_mgid_markup(content: str) -> str:
    content = re.sub(
        r"<script>\(function\(w,q\)\{w\[q\]=w\[q\]\|\|\[\];w\[q\]\.push\(\[\"_mgc\.load\"\]\)\}\)\(window,\"_mgq\"\);</script>",
        "",
        content,
    )
    content = re.sub(
        r'<div class="mgid-(?:widget-wrap|ad-slot)[^"]*"[^>]*>.*?data-widget-id="[^"]*".*?</div>',
        "",
        content,
        flags=re.DOTALL,
    )
    content = re.sub(
        r"<!--\s*MGID_[A-Z_]+\s*-->.*?<!--\s*/MGID_[A-Z_]+\s*-->",
        "",
        content,
        flags=re.DOTALL,
    )
    return content


def upsert_head_mgid(content: str, cfg: dict | None = None) -> str:
    content = strip_old_mgid_markup(content)
    content = re.sub(
        r'<script src="https://jsc\.mgid\.com/site/\d+\.js" async></script>',
        "",
        content,
    )
    if MGID_STYLES not in content:
        bundle = mgid_head_bundle(cfg)
        if "</head>" in content:
            content = content.replace("</head>", f"{bundle}</head>", 1)
        elif "<body" in content:
            content = content.replace("<body", f"{bundle}<body", 1)
    else:
        snippet = mgid_head_snippet(cfg)
        if "jsc.mgid.com" not in content and "</head>" in content:
            content = content.replace("</head>", f"{snippet}</head>", 1)
    return content


def ensure_body_loader(content: str) -> str:
    content = re.sub(
        r"<script>\(function\(w,q\)\{w\[q\]=w\[q\]\|\|\[\];w\[q\]\.push\(\[\"_mgc\.load\"\]\)\}\)\(window,\"_mgq\"\);</script>",
        "",
        content,
    )
    if "mgid-lazy.js" in content:
        return content
    if "</body>" in content:
        return content.replace("</body>", f"{MGID_LOADER}</body>", 1)
    return content + MGID_LOADER


def inject_home_layout(content: str, cfg: dict | None = None) -> str:
    s = home_slots(cfg)
    top_strip = (
        f'<div id="mgid-home-top-strip">{s["top"]}</div>'
    )
    if "mgid-home-top-strip" not in content:
        content = content.replace(
            '<div class="pt-32 sm:pt-36"></div>',
            f'<div class="pt-32 sm:pt-36"></div>{top_strip}',
            1,
        )
    if 'data-mgid-slot="home-after-hero"' not in content:
        content = re.sub(
            r'(ezoic-pub-ad-placeholder-101"></div></div>(?:</div>)?\s*</section>\s*)'
            r'(<section class="mt-10 rounded-2xl bg-white p-6 shadow-sm ring-1 ring-slate-200 sm:p-8" '
            r'aria-labelledby="latest-briefs-heading">)',
            rf'\1{s["after_hero"]}    </section>    \2',
            content,
            count=1,
        )
    sidebar_marker = '<aside class="hidden xl:block w-[320px]"><div class="sticky top-24 space-y-6">'
    if sidebar_marker in content and 'data-mgid-slot="home-sidebar"' not in content:
        content = content.replace(
            sidebar_marker,
            f'{sidebar_marker}{s["sidebar"]}',
            1,
        )
    if "</main>" in content and 'data-mgid-slot="home-pre-footer"' not in content:
        content = content.replace("</main>", f'{s["pre_footer"]}</main>', 1)
    return content


def inject_article_layout(content: str, cfg: dict | None = None) -> str:
    s = article_slots(cfg)
    if '<div class="pt-24 sm:pt-28"></div>' in content and 'data-mgid-slot="article-top"' not in content:
        content = content.replace(
            '<div class="pt-24 sm:pt-28"></div>',
            f'<div class="pt-24 sm:pt-28"></div><div id="mgid-article-top-strip">{s["top"]}</div>',
            1,
        )
    lede_end = "<!-- ARTICLE_LEDE -->"
    if lede_end in content:
        pass
    lede_close = "</p>\n        </header>"
    if lede_close in content and 'data-mgid-slot="article-under-lede"' not in content:
        content = content.replace(
            lede_close,
            f"</p>\n        </header>\n\n        {s['under_lede']}",
            1,
        )
    minified_lede = "</p>        </header>"
    if minified_lede in content and 'data-mgid-slot="article-under-lede"' not in content:
        content = content.replace(
            minified_lede,
            f"</p>        </header>        {s['under_lede']}",
            1,
        )
    ezoic_101 = '<div class="ezoic-ad mx-auto my-8 max-w-3xl"><div id="ezoic-pub-ad-placeholder-101"></div></div>'
    if ezoic_101 in content and 'data-mgid-slot="article-in-article"' not in content:
        content = content.replace(
            ezoic_101,
            f"{ezoic_101}        {s['in_article']}",
            1,
        )
    ezoic_106 = '<div class="ezoic-ad mx-auto my-8 max-w-3xl"><div id="ezoic-pub-ad-placeholder-106"></div></div>'
    if ezoic_106 in content and 'data-mgid-slot="article-mid"' not in content:
        content = content.replace(
            ezoic_106,
            f"{ezoic_106}        {s['mid']}",
            1,
        )
    ezoic_107 = '<div class="ezoic-ad mx-auto my-8 max-w-3xl"><div id="ezoic-pub-ad-placeholder-107"></div></div>'
    if ezoic_107 in content and 'data-mgid-slot="article-bottom"' not in content:
        content = content.replace(
            ezoic_107,
            f"{ezoic_107}        {s['bottom']}",
            1,
        )
    aside_marker = '<aside class="hidden xl:block w-[320px]"><div class="sticky top-24 space-y-6">'
    if aside_marker in content and 'data-mgid-slot="article-sidebar"' not in content:
        content = content.replace(aside_marker, f"{aside_marker}          {s['sidebar']}", 1)
    min_aside = '<aside class="hidden xl:block w-[320px]"><div class="sticky top-24 space-y-6"><div class="ezoic-ad">'
    if min_aside in content and 'data-mgid-slot="article-sidebar"' not in content:
        content = content.replace(
            min_aside,
            f'<aside class="hidden xl:block w-[320px]"><div class="sticky top-24 space-y-6">{s["sidebar"]}<div class="ezoic-ad">',
            1,
        )
    return content


def inject_static_layout(content: str, cfg: dict | None = None) -> str:
    s = static_slots(cfg)
    if '<div class="pt-24 sm:pt-28"></div>' in content and 'data-mgid-slot="static-top"' not in content:
        content = content.replace(
            '<div class="pt-24 sm:pt-28"></div>',
            f'<div class="pt-24 sm:pt-28"></div>\n  <div id="mgid-static-top-strip">{s["top"]}</div>',
            1,
        )
    content = re.sub(
        r'<div id="mgid-static-top-strip"></div></div>',
        f'<div id="mgid-static-top-strip">{s["top"]}</div>',
        content,
    )
    main_open = '<main class="mx-auto'
    if main_open in content and 'data-mgid-slot="static-mid"' not in content:
        idx = content.find(main_open)
        article_open = content.find("<article", idx)
        h1_end = content.find("</h1>", article_open if article_open >= 0 else idx)
        if h1_end > 0:
            insert_at = h1_end + len("</h1>")
            content = content[:insert_at] + s["mid"] + content[insert_at:]
    return content


def classify_page(path: Path) -> PageKind | None:
    if path.name == "index.html":
        return "home"
    if path.parent.name == "briefs" and path.name.startswith("brief-"):
        return "article"
    if path.name in STATIC_PAGES:
        return "static"
    return None


def apply_mgid_to_html(content: str, kind: PageKind, cfg: dict | None = None) -> str:
    content = upsert_head_mgid(content, cfg)
    if kind == "home":
        content = inject_home_layout(content, cfg)
    elif kind == "article":
        content = inject_article_layout(content, cfg)
    elif kind == "static":
        content = inject_static_layout(content, cfg)
    content = ensure_body_loader(content)
    return content


def apply_mgid_sitewide(*, include_all_briefs: bool = True, brief_limit: int = 0) -> int:
    cfg = load_mgid_config()
    patched = 0
    targets: list[Path] = []

    for path in sorted(BASE_DIR.glob("*.html")):
        if path.name in SKIP_FILES:
            continue
        if classify_page(path):
            targets.append(path)

    brief_files = sorted((BASE_DIR / "briefs").glob("brief-*.html"), reverse=True)
    if brief_limit > 0:
        targets.extend(brief_files[:brief_limit])
    elif include_all_briefs:
        targets.extend(brief_files)

    for path in targets:
        kind = classify_page(path)
        if not kind:
            continue
        original = path.read_text(encoding="utf-8")
        updated = apply_mgid_to_html(original, kind, cfg)
        if updated != original:
            if kind == "home" or path.parent.name == "briefs":
                updated = updated.replace("\n", "")
            path.write_text(updated, encoding="utf-8")
            patched += 1
    return patched


def article_template_markers_fill(template: str, cfg: dict | None = None) -> str:
    """Fill MGID_* markers in article-template.html for new brief generation."""
    s = article_slots(cfg)
    replacements = {
        "MGID_HEAD": mgid_head_bundle(cfg),
        "MGID_TOP": f'<div id="mgid-article-top-strip">{s["top"]}</div>',
        "MGID_UNDER_LEDE": s["under_lede"],
        "MGID_IN_ARTICLE": s["in_article"],
        "MGID_MID": s["mid"],
        "MGID_BOTTOM": s["bottom"],
        "MGID_SIDEBAR": s["sidebar"],
        "MGID_LOADER": MGID_LOADER,
    }
    for name, value in replacements.items():
        pattern = re.compile(
            rf"(<!--\s*{re.escape(name)}\s*-->)(.*?)(<!--\s*/{re.escape(name)}\s*-->)",
            re.DOTALL,
        )
        template = pattern.sub(lambda m, v=value: v, template)
    if "mgid-lazy.js" not in template:
        template = template.replace("</body>", f"{MGID_LOADER}</body>", 1)
    return template
