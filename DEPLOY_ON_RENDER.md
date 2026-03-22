# 🚀 Deploying Hinata Bot v2.5 - Elite Command Center

Your bot now features a **Premium Web Control Panel** with real-time monitoring, advanced command execution, and comprehensive bot management!

## ✨ What's Included

### 🎛️ Web Dashboard Features

- **Live Statistics**: Real-time user/group counts, broadcast metrics, and uptime tracking
- **Advanced Command Execution**: Ban, unban, kick, and promote users directly from the dashboard
- **Broadcast System**: Send messages to all users, groups, or both with one click
- **Live Logs**: Monitor bot activity in real-time with color-coded log entries
- **System Controls**: Restart bot, toggle public/private access, clear logs
- **Complete Command Reference**: All 30+ bot commands documented with syntax examples
- **Responsive Design**: Optimized for desktop, tablet, and mobile devices
- **Glassmorphism UI**: Modern, premium design with smooth animations

### 🤖 Bot Features

- **AI Engines**: Gemini 3, DeepSeek, ChatGPT with specialized modes (Flirt, Code, Translate, Grammar, Summarize)
- **Social Tools**: Instagram lookup, Telegram user info, Free Fire stats & guild info
- **Media Tools**: Background remover, QR generator/reader, multi-platform downloader
- **Games**: Truth or Dare, AI Riddle, Number Guessing
- **Owner Commands**: Global ban, group management, admin promotion, broadcast deletion

---

## 📋 Prerequisites

- ✅ **GitHub Account** (free)
- ✅ **Render.com Account** (free tier available)
- ✅ **Telegram Bot Token** from [@BotFather](https://t.me/BotFather)
- ✅ **Owner ID** (your Telegram user ID - get it from [@userinfobot](https://t.me/userinfobot))

---

## 🔧 Pre-Deployment Setup

### 1. Configure Bot Token

**Option A: Using `token.txt` (Simple)**

```bash
# Create/edit token.txt and paste your bot token
echo "7123456789:AAHdqTcvCH1vGWJxfSeofSAs0K5PALDsaw" > token.txt
```

**Option B: Using Environment Variables (Recommended for Production)**

- You'll set this directly in Render dashboard (Step 5 below)
- More secure, no sensitive data in repository

### 2. Update Owner ID

Edit `bot.py` line 75:

```python
OWNER_ID = 7333244376  # Replace with YOUR Telegram user ID
```

### 3. Verify Files

Ensure these files exist in your project:

```
📁 Your Project
├── bot.py              # Main bot logic
├── main.py             # FastAPI web server
├── requirements.txt    # Python dependencies
├── token.txt          # Bot token (optional)
├── render.yaml        # Render configuration
├── Procfile           # Alternative start command
├── static/
│   ├── style.css      # Dashboard styling
│   └── script.js      # Dashboard logic
└── templates/
    └── index.html     # Dashboard HTML
```

---

## 🚀 Deployment Steps

### Step 1: Push to GitHub

1. **Create a new repository** on GitHub
2. **Upload all files** (or use Git):

   ```bash
   git init
   git add .
   git commit -m "Initial commit - Hinata Bot v2.5"
   git branch -M main
   git remote add origin https://github.com/YOUR_USERNAME/hinata-bot.git
   git push -u origin main
   ```

3. **Important**: If using `token.txt`, ensure it's included. If using env vars, you can add `token.txt` to `.gitignore` for security.

### Step 2: Connect to Render

1. Log in to [**Render.com**](https://render.com)
2. Click **"New +"** → **"Web Service"**
3. Click **"Connect account"** and authorize GitHub
4. Select your **hinata-bot** repository

### Step 3: Configure Deployment

**Basic Settings:**

- **Name**: `hinata-bot-panel` (or your preferred name)
- **Region**: Choose closest to your users
- **Branch**: `main`
- **Runtime**: `Python 3`

**Build & Deploy:**

- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `python main.py`

### Step 4: Set Python Version (CRITICAL)

In the **Environment Variables** section, add:

```
Key: PYTHON_VERSION
Value: 3.11.10
```

> ⚠️ **Why?** Render sometimes uses experimental Python versions (like 3.14) that break compatibility. This forces a stable version.

### Step 5: Add Bot Token (If using Environment Variables)

If you're NOT using `token.txt`, add:

```
Key: BOT_TOKEN
Value: 7123456789:AAHdqTcvCH1vGWJxfSeofSAs0K5PALDsaw
```

Then modify `bot.py` line 76 to read from environment:

```python
BOT_TOKEN = os.environ.get("BOT_TOKEN") or read_file(BOT_TOKEN_FILE).strip()
```

### Step 6: Deploy!

1. Click **"Create Web Service"**
2. Render will:
   - ✅ Clone your repository
   - ✅ Install dependencies
   - ✅ Start the bot and web server
3. **First deployment takes 5-10 minutes**

### Step 7: Monitor Deployment

Watch the **Logs** tab for:

```
✅ Hinata Initialized
✅ Hinata Live and Polling
✅ Web Dashboard Started
```

If you see errors:

- Check `PYTHON_VERSION` is set to `3.11.10`
- Verify `token.txt` exists or `BOT_TOKEN` env var is set
- Check logs for missing dependencies

---

## 🌐 Accessing Your Dashboard

Once deployed, Render provides a URL like:

```
https://hinata-bot-panel.onrender.com
```

Open this in your browser to access:

- 📊 **Real-time Stats**: Users, groups, broadcasts, uptime
- 🎮 **Control Panel**: Broadcast messages, execute commands
- 📜 **Live Logs**: Monitor bot activity
- 📖 **Command Reference**: All available commands

---

## 🔐 Security Best Practices

### 1. Protect Your Dashboard

The dashboard is currently open to anyone with the URL. To secure it:

**Option A: Add Basic Auth** (Add to `main.py`):

```python
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import secrets

security = HTTPBasic()

def verify_admin(credentials: HTTPBasicCredentials = Depends(security)):
    correct_username = secrets.compare_digest(credentials.username, "admin")
    correct_password = secrets.compare_digest(credentials.password, "your_secure_password")
    if not (correct_username and correct_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    return credentials.username
```

**Option B: Use Render's Authentication** (Paid plans)

### 2. Use Environment Variables for Secrets

Never commit:

- Bot tokens
- API keys
- Passwords

Store them in Render's Environment Variables section.

### 3. Monitor Your Logs

Check the dashboard regularly for:

- Unauthorized access attempts
- Unusual broadcast patterns
- API errors

---

## ⚙️ Advanced Configuration

### Auto-Restart on Crash

Render automatically restarts crashed services, but you can add a health check:

**Add to `render.yaml`:**

```yaml
services:
  - type: web
    name: hinata-bot-panel
    runtime: python
    buildCommand: pip install -r requirements.txt
    startCommand: python main.py
    healthCheckPath: /
    envVars:
      - key: PYTHON_VERSION
        value: 3.11.10
```

### Keep Bot Alive (Free Tier)

Render's free tier sleeps after 15 minutes of inactivity. Solutions:

**Option 1: Use a Ping Service**

- [Uptime Robot](https://uptimerobot.com) (free)
- Ping your dashboard URL every 10 minutes

**Option 2: Upgrade to Paid Plan**

- $7/month for always-on service

**Option 3: Self-Ping** (Add to `bot.py`):

```python
async def keep_alive():
    while True:
        try:
            async with httpx.AsyncClient() as client:
                await client.get("https://your-app.onrender.com")
        except: pass
        await asyncio.sleep(600)  # 10 minutes

# In start_bot():
asyncio.create_task(keep_alive())
```

### Custom Domain

1. In Render Dashboard → **Settings** → **Custom Domain**
2. Add your domain (e.g., `bot.yourdomain.com`)
3. Update DNS records as instructed
4. Render provides free SSL certificate

---

## 📊 Monitoring & Maintenance

### View Logs

- **Render Dashboard**: Logs tab shows all stdout/stderr
- **Bot Dashboard**: `/` shows last 50 log entries
- **Download Logs**: Render allows log export

### Update Bot

```bash
# Make changes to your code
git add .
git commit -m "Update: Added new feature"
git push origin main
```

Render auto-deploys on push! 🚀

### Rollback Deployment

If something breaks:

1. Go to **Deploys** tab
2. Find the last working deployment
3. Click **"Redeploy"**

---

## 🆘 Troubleshooting

### Bot Not Starting

**Error**: `ModuleNotFoundError`

- **Fix**: Ensure all dependencies in `requirements.txt`
- Verify `buildCommand` ran successfully

**Error**: `Unauthorized`

- **Fix**: Check `token.txt` or `BOT_TOKEN` env var
- Regenerate token from @BotFather if needed

**Error**: `Address already in use`

- **Fix**: Use `PORT` environment variable:
  ```python
  port = int(os.environ.get("PORT", 10000))
  ```

### Dashboard Not Loading

- Check if the web service is "Live" in Render
- Verify `startCommand: python main.py`
- Check logs for FastAPI startup messages

### Database Issues

If using persistent data:

1. Go to **Disks** in Render settings
2. Add a disk mounted at `/data`
3. Update file paths in `bot.py`:
   ```python
   DATA_DIR = os.environ.get("DATA_PATH", "./")
   USERS_FILE = os.path.join(DATA_DIR, "users.json")
   ```

---

## 🎯 Performance Optimization

### Use Redis for State Management (Advanced)

For high-traffic bots, consider Redis:

```bash
pip install redis
```

Update `bot.py`:

```python
import redis
redis_client = redis.from_url(os.environ.get("REDIS_URL"))
```

### Enable Caching

Add to `main.py`:

```python
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.gzip import GZipMiddleware

app.add_middleware(GZipMiddleware, minimum_size=1000)
```

---

## 📞 Support

- **Issues**: Open an issue on GitHub
- **Render Docs**: [render.com/docs](https://render.com/docs)
- **Telegram Support**: Contact [@ShaunXnone](https://t.me/ShaunXnone)

---

## 📜 License

© 2026 Shawon Codes | Hinata Bot v2.5  
Built with ❤️ using Python, FastAPI, and python-telegram-bot

---

**🎉 Your bot is now live! Open the dashboard and start managing your Telegram empire!**
