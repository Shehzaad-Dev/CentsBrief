# CentsBrief.online - Automated Financial AI Platform

**Live Site:** [https://centsbreif.online/](https://centsbreif.online/)

CentsBrief is a fully automated, AI-powered financial briefing platform designed for US and UK audiences. It transforms highly complex market data into accessible, practical, and highly readable daily updates for retail investors and households without financial jargon.

This repository holds the entire static site frontend, as well as the backend automation script (`main.py`) which orchestrates the autonomous daily publishing. 

---

## 🚀 Key Features

* **Fully Automated Pipeline**: Your PC can stay off. An automation script (`main.py`) running on a scheduler handles the entire workflow autonomously.
* **AI-Generated Information Gain**: Driven by Groq's high-speed API (`llama-3.3-70b-versatile`), it pulls real headline data, processes it, and generates a structured, ~1000-word daily brief explaining *what happened*, *why markets reacted*, and *the impact on local wallets*.
* **Pristine SEO & Clean URLs (April 2026 Update)**: 
    * HTML templates are actively stripped of meta-tag comment markers during generation, providing perfect `<title>`, `<meta>`, and `<link>` rendering for advanced search engine crawlers. 
    * Internal site links use dynamic **clean URLs** (e.g., `href="about"` instead of `href="about.html"`). This simulates a modern Single Page Application (SPA) experience while running purely statically.
* **Zero-CLS Tailwind Frontend**: Built on a highly optimized, fully responsive, and visually lightweight TailwindCSS design system.
* **Rolling Archive Automation**: Automatically manages storage by culling old financial briefs beyond a specified retention period (default 60 days) to keep deployment sizes small. 

---

## 🛠️ The Technical Stack

* **Frontend**: Vanilla HTML5, JavaScript, and Tailwind CSS.
* **Backend Pipeline**: Python 3 orchestrator (`main.py`).
* **Data Ingestion**: `feedparser` pulling real-time RSS market feeds (defaults to Yahoo Finance).
* **AI Engine**: Groq Cloud REST API.
* **Server**: Hosted statically online (e.g., via GitHub Pages or NGINX), seamlessly serving the updated index and dynamically generated `.html` files without the extension.

---

## ⚙️ How `main.py` Works (The Engine)

The magic of CentsBrief happens entirely within `main.py` when it executes. This is what it does during a run:

1. **Information Gathering**: Parses the raw RSS feed via the preset `RSS_FEED_URL` to grab the top US/UK market headlines.
2. **AI Processing**: Compiles a localized prompt requesting exactly ~1,000 words. The script interfaces securely with the Groq API to interpret the data into structured markdown (incorporating headers, bullet points, and Q&A).
3. **HTML Conversion**: Transforms the raw Markdown output into styled HTML using the target Tailwind typography tokens.
4. **Template Generation**: Clones the master `article-template.html` file into a new file named `brief-[TODAY'S DATE].html`.
5. **Live SEO Cleaning**: Scans the template, cleans out all template placeholder comments inside the `<title>` and `<meta>` blocks (to avoid trailing HTML comments breaking SEO cards on social networks), and outputs a completely clean file setup ready for GitHub Pages hosting.
6. **Dynamic Routing Update**: Safely updates `index.html` via regex—sliding the latest headline directly into the "Hero" component, moving the previous brief down into the "Latest Briefs" feed, and updating all references using the clean URL protocol.
7. **Housekeeping:** Sweeps the directory for files older than `BRIEF_RETENTION_DAYS` and permanently deletes them.

---

## 🖥️ Live Server & Automation Setup

Want to host this 24/7 so it runs while you sleep?

### 1) Requirements
1. Linux VPS (Ubuntu 22.04+ recommended)
2. Groq API key
3. Registered Domain (e.g., `centsbreif.online`) connected to the VPS via DNS (`A` Records).

### 2) Environment Configuration
Move your files to `/var/www/centsbrief` and create a `.env` file with restrictive permissions (`chmod 600`):
```env
GROQ_API_KEY=YOUR_GROQ_KEY
GROQ_MODEL=llama-3.3-70b-versatile
SITE_BASE_URL=https://centsbreif.online
BRIEF_RETENTION_DAYS=60
RSS_FEED_URL=https://feeds.finance.yahoo.com/rss/2.0/headline?s=%5EGSPC,%5EFTSE&region=US&lang=en-US
```

### 3) Web Server Binding 
Since we use Clean URLs, configure your `NGINX` instance to treat requests without extensions as HTML files:
```nginx
server {
    server_name centsbreif.online www.centsbreif.online;
    root /var/www/centsbrief;
    index index.html;

    location / {
        # This directive ensures paths like `/about` correctly bind to `/about.html`
        try_files $uri $uri.html $uri/ =404;
    }
}
```

### 4) Unattended Automation 
Set up a daily cron job so the Python script triggers everything automatically:
```bash
crontab -e
```
Add the following line (Runs every morning at 05:00 server time):
```cron
0 5 * * * cd /var/www/centsbrief && export $(cat .env | xargs) && /usr/bin/python3 main.py >> /var/log/centsbrief.log 2>&1
```

By completing this step, your server will automatically pull news, write the 1,000 word brief, rewrite the HTML code on your index page, configure the exact clean URLs and meta SEO tags, and immediately stream the results to the user! No daily oversight required.
