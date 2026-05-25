"""MGID: homepage top banner (eager) + lazy units on article pages only."""
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

MGID_STYLES = (
    '<link rel="stylesheet" href="/assets/site-layout.css" />'
    '<link rel="stylesheet" href="/assets/mgid.css" />'
)
MGID_LOADER = (
    '<script data-cfasync="false" src="/assets/mgid-lazy.js" defer></script>'
    '<script data-cfasync="false">'
    "(function(w,q){w[q]=w[q]||[];w[q].push(['_mgc.load'])})(window,'_mgq');"
    "</script>"
)


def load_mgid_config() -> dict:
    defaults = {
        "site_id": "1097226",
        "home_top_widget_id": "2017365",
        "article_infeed_widget_id": "2017365",
        "article_bottom_widget_id": "2017365",
        "enable_amp": False,
    }
    if not MGID_CONFIG_PATH.exists():
        return defaults
    try:
        data = json.loads(MGID_CONFIG_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return defaults
    return {**defaults, **{k: v for k, v in data.items() if not str(k).startswith("_")}}


def widget_for_slot(slot_id: str, cfg: dict | None = None) -> str:
    cfg = cfg or load_mgid_config()
    keys = {
        "home-top": "home_top_widget_id",
        "article-in-article": "article_infeed_widget_id",
        "article-bottom": "article_bottom_widget_id",
    }
    key = keys.get(slot_id)
    if key and cfg.get(key):
        return str(cfg[key]).strip()
    return str(cfg.get("widget_id") or "2017365").strip()


def mgid_site_id(cfg: dict | None = None) -> str:
    cfg = cfg or load_mgid_config()
    return str(cfg.get("site_id") or "1097226").strip()


def mgid_head_snippet(cfg: dict | None = None) -> str:
    sid = html.escape(mgid_site_id(cfg))
    return (
        f'<script data-cfasync="false" src="https://jsc.mgid.com/site/{sid}.js" async></script>'
    )


def mgid_head_bundle(cfg: dict | None = None) -> str:
    return MGID_STYLES + mgid_head_snippet(cfg)


def mgid_slot(
    slot_id: str,
    *,
    eager: bool = False,
    layout: str = "infeed",
    cfg: dict | None = None,
    widget_id: str | None = None,
) -> str:
    wid = html.escape(widget_id or widget_for_slot(slot_id, cfg))
    mode = "mgid-slot--eager" if eager else "mgid-slot--lazy"
    return (
        f'<div class="mgid-ad-slot {mode} mgid-layout--{layout}" '
        f'data-mgid-slot="{html.escape(slot_id)}" aria-label="Advertisement">'
        f'<div data-type="_mgwidget" data-widget-id="{wid}"></div></div>'
    )


def home_top_slot(cfg: dict | None = None) -> str:
    return mgid_slot(
        "home-top",
        eager=True,
        layout="banner",
        cfg=cfg,
        widget_id=widget_for_slot("home-top", cfg),
    )


def article_slots(cfg: dict | None = None) -> dict[str, str]:
    return {
        "in_article": mgid_slot(
            "article-in-article",
            layout="infeed",
            cfg=cfg,
            widget_id=widget_for_slot("article-in-article", cfg),
        ),
        "bottom": mgid_slot(
            "article-bottom",
            layout="infeed",
            cfg=cfg,
            widget_id=widget_for_slot("article-bottom", cfg),
        ),
    }


def strip_all_mgid_slots(content: str) -> str:
    content = re.sub(
        r"<script>\(function\(w,q\)\{w\[q\]=w\[q\]\|\|\[\];w\[q\]\.push\(\[\"_mgc\.load\"\]\)\}\)\(window,\"_mgq\"\);</script>",
        "",
        content,
    )
    content = re.sub(
        r'<div id="mgid-(?:home-top|article-top|static-top)-strip">.*?</div>\s*</div>?',
        "",
        content,
        flags=re.DOTALL,
    )
    content = re.sub(
        r'<div class="mgid-ad-slot[^>]*>.*?</div>\s*</div>',
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
    content = re.sub(
        r'<script src="https://jsc\.mgid\.com/site/\d+\.js" async></script>',
        "",
        content,
    )
    bundle = mgid_head_bundle(cfg)
    if "</head>" in content:
        if MGID_STYLES in content and "jsc.mgid.com" in content:
            content = re.sub(
                r'<script src="https://jsc\.mgid\.com/site/\d+\.js" async></script>',
                mgid_head_snippet(cfg),
                content,
            )
        elif "jsc.mgid.com" not in content:
            content = content.replace("</head>", f"{bundle}</head>", 1)
    return content


def ensure_body_loader(content: str) -> str:
    if "mgid-lazy.js" not in content:
        if "</body>" in content:
            content = content.replace("</body>", f"{MGID_LOADER}</body>", 1)
        else:
            content += MGID_LOADER
    return content


def repair_index_layout(content: str) -> str:
    """Fix extra closing tags that break the homepage 2-column grid."""
    content = content.replace(
        "</div></div>    </section>        </section>    <section class=",
        "</div>    </section>    <section class=",
    )
    content = re.sub(
        r"</div></div>\s*</section>\s*</section>\s*<section class=",
        "</div>    </section>    <section class=",
        content,
        count=1,
    )
    if "home-main-grid" not in content:
        content = content.replace(
            'class="grid gap-10 xl:grid-cols-[1fr_320px]"',
            'class="home-main-grid"',
            1,
        )
    if "home-primary-column" not in content:
        content = content.replace('<div class="space-y-10">', '<div class="home-primary-column">', 1)
    if "brief-feed-grid" not in content:
        content = content.replace(
            '<div class="grid gap-5 md:grid-cols-2 lg:grid-cols-3">',
            '<div id="brief-feed-grid" class="grid gap-5 md:grid-cols-2 lg:grid-cols-3">',
            1,
        )
    return content


def inject_home_layout(content: str, cfg: dict | None = None) -> str:
    content = repair_index_layout(content)
    top = home_top_slot(cfg)
    top_strip = f'<div id="mgid-home-top-strip">{top}</div>'
    content = strip_all_mgid_slots(content)
    content = upsert_head_mgid(content, cfg)
    if "mgid-home-top-strip" not in content:
        content = content.replace(
            '<div class="pt-32 sm:pt-36"></div>',
            f'<div class="pt-32 sm:pt-36"></div>{top_strip}',
            1,
        )
    else:
        content = re.sub(
            r'<div id="mgid-home-top-strip">.*?</div>\s*(?=<main)',
            f"{top_strip}",
            content,
            count=1,
            flags=re.DOTALL,
        )
    return content


def inject_article_layout(content: str, cfg: dict | None = None) -> str:
    s = article_slots(cfg)
    content = strip_all_mgid_slots(content)
    content = upsert_head_mgid(content, cfg)

    ezoic_101 = '<div class="ezoic-ad mx-auto my-8 max-w-3xl"><div id="ezoic-pub-ad-placeholder-101"></div></div>'
    if ezoic_101 in content:
        content = content.replace(f"{ezoic_101}", f"{ezoic_101}{s['in_article']}", 1)

    ezoic_107 = '<div class="ezoic-ad mx-auto my-8 max-w-3xl"><div id="ezoic-pub-ad-placeholder-107"></div></div>'
    if ezoic_107 in content:
        content = content.replace(f"{ezoic_107}", f"{ezoic_107}{s['bottom']}", 1)

    return content


def inject_static_layout(content: str, cfg: dict | None = None) -> str:
    """Static pages: MGID head + lazy script only (no extra widgets)."""
    content = strip_all_mgid_slots(content)
    return upsert_head_mgid(content, cfg)


def classify_page(path: Path) -> PageKind | None:
    if path.name == "index.html":
        return "home"
    if path.parent.name == "briefs" and path.name.startswith("brief-"):
        return "article"
    if path.name in STATIC_PAGES:
        return "static"
    return None


def apply_mgid_to_html(content: str, kind: PageKind, cfg: dict | None = None) -> str:
    if kind == "home":
        content = inject_home_layout(content, cfg)
    elif kind == "article":
        content = inject_article_layout(content, cfg)
    elif kind == "static":
        content = inject_static_layout(content, cfg)
    else:
        content = upsert_head_mgid(content, cfg)
    return ensure_body_loader(content)


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
    s = article_slots(cfg)
    replacements = {
        "MGID_HEAD": mgid_head_bundle(cfg),
        "MGID_TOP": "",
        "MGID_UNDER_LEDE": "",
        "MGID_IN_ARTICLE": s["in_article"],
        "MGID_MID": "",
        "MGID_BOTTOM": s["bottom"],
        "MGID_SIDEBAR": "",
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
