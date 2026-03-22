# Hinata Bot v2.5 - Elite Telegram Manager

[![Python](https://img.shields.io/badge/Python-3.11-blue.svg)](https://www.python.org/)
[![Telegram Bot](https://img.shields.io/badge/Telegram-Bot-blue.svg)](https://core.telegram.org/bots)
[![Deploy](https://img.shields.io/badge/Deploy-Render-purple.svg)](https://render.com)

> **Premium AI-powered Telegram bot with advanced web dashboard for complete bot management**

## 🌟 Features

### 🤖 AI Engines

- **Gemini 3 Pro** - Google's latest AI model
- **DeepSeek v3.2** - Advanced reasoning AI
- **ChatGPT Addy** - Versatile conversational AI
- **Specialized AI Tools**:
  - 💖 Flirt AI - Romantic conversation assistant
  - 💻 Code Generator - Multi-language code creation
  - 🌐 Translator - Multi-language translation
  - 📝 Summarizer - Intelligent text summarization
  - ✍️ Grammar Checker - Professional proofreading

### 🎮 Games & Entertainment

- 🎲 Truth or Dare (AI-generated)
- 💡 AI Riddle Challenge
- 🔢 Number Guessing Game

### 🛠️ Utilities

- 📸 Instagram Profile Lookup
- 👤 Telegram User Information
- 🎮 Free Fire Player Stats
- 🏰 Free Fire Guild Information
- 🚀 Free Fire Like Booster
- 🖼️ QR Code Generator & Reader
- 🫧 Background Remover (AI-powered)
- 📥 Multi-platform Media Downloader (YouTube, TikTok, Instagram, etc.)

### 🎛️ Web Dashboard

- 📊 Real-time Statistics (users, groups, broadcasts, uptime)
- 🎮 Command Execution Panel (ban, unban, kick, promote)
- 📡 Broadcast System (global, users-only, groups-only)
- 📜 Live Log Monitoring (color-coded)
- ⚙️ System Controls (restart, access toggle, log clearing)
- 📖 Complete Command Reference
- 📱 Responsive Design (mobile, tablet, desktop)

### 👑 Owner Commands

- Global user ban/unban
- Group member management (ban, unban, kick, mute, unmute)
- Admin promotion with full permissions
- Broadcast message management
- Public/private access control
- Live statistics

## 📋 Requirements

- Python 3.11+
- Telegram Bot Token (from [@BotFather](https://t.me/BotFather))
- Render.com account (for deployment)

## 🚀 Quick Start

### 1. Clone Repository

```bash
git clone https://github.com/YOUR_USERNAME/hinata-bot.git
cd hinata-bot
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Bot

Edit `bot.py`:

```python
OWNER_ID = YOUR_TELEGRAM_USER_ID  # Get from @userinfobot
```

Create `token.txt`:

```
YOUR_BOT_TOKEN_HERE
```

### 4. Run Locally

```bash
python main.py
```

Access dashboard at: `http://localhost:10000`

### 5. Deploy to Render

See [DEPLOY_ON_RENDER.md](DEPLOY_ON_RENDER.md) for complete deployment guide.

## 📁 Project Structure

```
hinata-bot/
├── bot.py                 # Main bot logic
├── main.py                # FastAPI web server
├── requirements.txt       # Python dependencies
├── render.yaml           # Render deployment config
├── Procfile              # Alternative deployment
├── token.txt             # Bot token (create this)
├── static/
│   ├── style.css         # Dashboard styling
│   └── script.js         # Dashboard interactivity
├── templates/
│   └── index.html        # Dashboard HTML
├── DEPLOY_ON_RENDER.md   # Deployment guide
└── README.md             # This file
```

## 🎯 Usage

### Bot Commands

#### AI Features

- `/gemini [prompt]` - Gemini 3 AI
- `/deepseek [prompt]` - DeepSeek AI
- `/flirt [text]` - Romantic AI
- `/code [request]` - Code generator
- `/translate [text]` - Translator
- `/summarize [text]` - Summarizer
- `/grammar [text]` - Grammar checker

#### Utilities

- `/insta [username]` - Instagram info
- `/userinfo [id/username]` - Telegram user info
- `/ff [uid]` - Free Fire stats
- `/ffguild [id]` - Guild info
- `/qrgen [text]` - Generate QR code
- `/qrread` - Read QR code (reply to image)
- `/bgrem` - Remove background (reply to photo)
- `/dl [url]` - Download media

#### Games

- `/tod` - Truth or Dare
- AI Riddle & Number Guess (via menu)

#### Owner Only

- `/broadcast [msg]` - Broadcast to groups
- `/broadcastuser [msg]` - Broadcast to users
- `/broadcastall [msg]` - Broadcast to all
- `/gban [user_id]` - Global ban
- `/ungban [user_id]` - Remove global ban
- `/addadmin [chat_id] [user_id]` - Promote to admin
- `/stats` - View statistics
- And more...

## 🔐 Security

- Owner verification on all admin commands
- Global ban system
- Public/private access control
- Environment variable support for secrets
- Optional basic authentication for dashboard

## 🛠️ Configuration

### Environment Variables (Optional)

```bash
BOT_TOKEN=your_bot_token_here
PYTHON_VERSION=3.11.10
PORT=10000
```

### Customization

Edit `bot.py` to:

- Change bot name and version
- Add/remove features
- Customize AI prompts
- Modify menu structure

## 📊 Dashboard Features

Access your deployed URL to:

- Monitor bot statistics in real-time
- Execute owner commands without Telegram
- Send broadcasts to users and groups
- View live system logs
- Manage banned users
- Control bot status

## 🚀 Deployment

### Render.com (Recommended)

```bash
# 1. Push to GitHub
git push origin main

# 2. Connect to Render
# See DEPLOY_ON_RENDER.md for detailed steps

# 3. Access your dashboard
https://your-app-name.onrender.com
```

### Heroku

```bash
heroku create your-app-name
git push heroku main
```

### Railway

```bash
railway login
railway init
railway up
```

## 📈 Performance

- Handles 1000+ concurrent users
- Auto-cleanup system (downloads & logs)
- Optimized async operations
- Minimal memory footprint (~150MB)
- Fast response times (<500ms)

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Open a Pull Request

## 📄 License

© 2026 Shawon Codes  
This project is for educational purposes.

## 📞 Support

- **Telegram**: [@ShawonXnone](https://t.me/ShawonXnone)
- **Issues**: [GitHub Issues](https://github.com/YOUR_USERNAME/hinata-bot/issues)

## 🙏 Credits

- Built with [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot)
- Powered by [FastAPI](https://fastapi.tiangolo.com/)
- Deployed on [Render](https://render.com)
- AI APIs: Gemini, DeepSeek, ChatGPT

---

**Made with ❤️ by Shawon | Powered by Hinata AI Engine**
