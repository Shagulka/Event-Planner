# WF Events — Server Runbook

## 1. First-Time Setup

```bash
# Clone and enter repo
cd .../Event-Planner

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure secrets
cd WatsonForsbergEvents/
cp .env.example .env
nano .env   # fill in all required keys (see Troubleshooting below)

# Initialize database and static files
python3 manage.py migrate
python3 manage.py collectstatic

# Start app server
gunicorn --bind 127.0.0.1:8000 eventPlanner.wsgi:application
```

---

## 2. Deploy an Update

```bash
cd /root/Event-Planner
source venv/bin/activate
git pull
cd WatsonForsbergEvents/

# Run if static changed:
# python3 manage.py collectstatic

python3 manage.py migrate
gunicorn --bind 127.0.0.1:8000 eventPlanner.wsgi:application
```

---

## 3. Nginx Setup

### Install

```bash
sudo apt install nginx
```

### Create site config

```bash
sudo nano /etc/nginx/sites-available/wfevents
```

```nginx
server {
    listen 80;
    server_name YOUR_DOMAIN YOUR_SERVER_IP;

    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl;
    server_name YOUR_DOMAIN YOUR_SERVER_IP;

    ssl_certificate     /etc/letsencrypt/live/YOUR_DOMAIN/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/YOUR_DOMAIN/privkey.pem;

    # Serve static files directly (faster than going through Django)
    location /static/ {
        alias /root/Event-Planner/WatsonForsbergEvents/staticfiles/;
        expires 30d;
        add_header Cache-Control "public";
    }

    # Proxy everything else to Gunicorn
    location / {
        proxy_pass         http://127.0.0.1:8000;
        proxy_set_header   Host $host;
        proxy_set_header   X-Real-IP $remote_addr;
        proxy_set_header   X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto $scheme;
    }
}
```

### Enable and reload

```bash
sudo ln -s /etc/nginx/sites-available/wfevents /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### SSL — Let's Encrypt

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d YOUR_DOMAIN
# Certbot sets up auto-renewal; verify with:
sudo certbot renew --dry-run
```

### Nginx quick-reference

| Command | Purpose |
|---|---|
| `sudo systemctl status nginx` | Check if nginx is running |
| `sudo nginx -t` | Validate config before reloading |
| `sudo systemctl reload nginx` | Apply config changes (no downtime) |
| `sudo tail -f /var/log/nginx/error.log` | Live error log |

---

## 4. Troubleshooting — API Keys / Tokens

All secrets live in `WatsonForsbergEvents/.env`.

| Symptom | Key(s) to update |
|---|---|
| Google Maps not loading | `GOOGLE_MAPS_API_KEY` |
| Calendar sync broken | `MICROSOFT_CALENDAR_API_CLIENT_ID`, `MICROSOFT_CALENDAR_API_CLIENT_SECRET` |
| Microsoft sign-in broken | `MICROSOFT_SSO_APPLICATION_ID`, `MICROSOFT_SSO_CLIENT_SECRET` |
