# CentsBrief.online - Full Live Setup (PC Can Stay Off)

This guide sets up your site so:
- it stays live 24/7 on your domain,
- AI publishes a new brief daily automatically,
- and your PC can be OFF.

The automation runs on a VPS server, not your local machine.

---

## 1) What your project already does

- Generates a daily AI finance brief from US/UK market headlines (`main.py`)
- Builds structured 1000-word-style articles with headings
- Updates homepage with latest brief first
- Inserts monetization ad containers
- Deletes old brief pages automatically (default retention: 60 days)

---

## 2) Requirements

1. Domain name (e.g. `centsbreif.online`)
2. Linux VPS (Ubuntu 22.04+ recommended)
3. Groq API key
4. Your project files uploaded to server

---

## 3) One-time server setup (after buying VPS)

SSH into VPS:
```bash
ssh root@YOUR_SERVER_IP
```

Install packages:
```bash
apt update
apt install -y python3 python3-pip nginx certbot python3-certbot-nginx
```

Create project folder and upload files:
```bash
mkdir -p /var/www/centsbrief
```

Upload your local project to `/var/www/centsbrief` using SFTP/WinSCP.

Install Python dependencies:
```bash
cd /var/www/centsbrief
pip3 install -r requirements.txt
```

Optional but recommended:
```bash
pip3 install python-dotenv
```

---

## 4) Add secure environment config

Create file:
`/var/www/centsbrief/.env`

Content:
```env
GROQ_API_KEY=YOUR_NEW_ROTATED_KEY
GROQ_MODEL=llama-3.3-70b-versatile
SITE_BASE_URL=https://centsbreif.online
BRIEF_RETENTION_DAYS=60
RSS_FEED_URL=https://feeds.finance.yahoo.com/rss/2.0/headline?s=%5EGSPC,%5EFTSE&region=US&lang=en-US
```

Secure it:
```bash
chmod 600 /var/www/centsbrief/.env
```

---

## 5) Connect your domain to VPS

At your domain registrar DNS:
- `A` record: `@` -> `YOUR_SERVER_IP`
- `A` record: `www` -> `YOUR_SERVER_IP`

Wait for propagation.

---

## 6) Nginx web server config (24/7 live)

Create:
`/etc/nginx/sites-available/centsbrief`

```nginx
server {
    server_name centsbreif.online www.centsbreif.online;
    root /var/www/centsbrief;
    index index.html;

    location / {
        try_files $uri $uri/ =404;
    }
}
```

Enable and restart:
```bash
ln -s /etc/nginx/sites-available/centsbrief /etc/nginx/sites-enabled/centsbrief
nginx -t
systemctl restart nginx
```

Enable HTTPS:
```bash
certbot --nginx -d centsbreif.online -d www.centsbreif.online
```

---

## 7) Fully automatic daily posting (PC OFF)

Set cron on VPS:
```bash
crontab -e
```

Add line:
```cron
0 5 * * * cd /var/www/centsbrief && export $(cat .env | xargs) && /usr/bin/python3 main.py >> /var/log/centsbrief.log 2>&1
```

This means:
- Every day at 05:00 server time
- AI creates today’s brief
- Homepage updates automatically
- Old pages beyond retention are removed
- No manual commands needed daily

---

## 8) Verify automation once

Run once manually on server:
```bash
cd /var/www/centsbrief
export $(cat .env | xargs)
python3 main.py
```

Check output files:
- `brief-YYYY-MM-DD.html` created
- `index.html` updated

Check logs later:
```bash
tail -n 100 /var/log/centsbrief.log
```

---

## 9) Security checklist

- Keep `.env` only on server
- Never paste API key in code files
- Rotate API key if exposed
- Keep file permissions strict (`chmod 600 .env`)
- Keep server updated:
```bash
apt update && apt upgrade -y
```

---

## 10) Quick maintenance (monthly)

1. Check website loads over HTTPS
2. Check latest brief generated
3. Check cron log for failures
4. Rotate API key periodically
5. Verify ad containers still present on article and homepage

---

## 11) If cron fails

Common causes:
- invalid API key or zero Groq quota
- wrong python path
- malformed `.env` file
- DNS/SSL not configured

Debug:
```bash
cd /var/www/centsbrief
export $(cat .env | xargs)
python3 main.py
```

Then fix errors shown in terminal/log.
