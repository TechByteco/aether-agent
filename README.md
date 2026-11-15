# AETHER — Sovereign Executive OS

<p align="center">
  <img src="src/aether/web/static/aether_logo.png" alt="AETHER" width="120" onerror="this.style.display='none'"/>
</p>

<p align="center">
  <a href="https://github.com/TechByteco/aether-agent/actions"><img src="https://github.com/TechByteco/aether-agent/actions/workflows/ci.yml/badge.svg" alt="CI"/></a>
  <img src="https://img.shields.io/badge/python-3.11%20|%203.12-blue" alt="Python"/>
  <img src="https://img.shields.io/badge/platform-Render%20%7C%20Docker-green" alt="Platform"/>
  <img src="https://img.shields.io/badge/license-MIT-lightgrey" alt="License"/>
</p>

> **AETHER** is an autonomous, self-improving AI executive assistant — engineered for 24/7 sovereign operation. It manages CRM pipelines, emails, payments, Telegram/WhatsApp channels, and continuously improves its own codebase.

---

## ✨ Features

| Category | Capabilities |
|---|---|
| 🧠 **Cognitive Engine** | 353 tools, Fast Cortex sub-5ms routing, multi-provider LLM (Groq/Gemini/OpenRouter/local) |
| 📧 **Email** | Gmail IMAP/SMTP triage, summarisation, auto-reply |
| 💼 **CRM** | Deal pipeline, auto meeting booking, proposal auto-reply |
| 💳 **Payments** | Razorpay webhook (HMAC verified), payment event log |
| 📱 **Channels** | Telegram bot (@MyAetherAssistantBot), WhatsApp, Samsung One UI 8 deep links |
| 🤖 **Autonomous Ops** | 15 APScheduler background jobs — health checks, lead discovery, morning briefings |
| 🔄 **Self-Improvement** | Continuous Improvement Engine runs every 4h — scans code, benchmarks, fixes |
| 🌐 **Web UI** | Glassmorphic OLED dark executive dashboard with hands-free voice mode |

## 🚀 Quick Start (Local)

```bash
# 1. Clone
git clone https://github.com/TechByteco/aether-agent.git
cd aether-agent

# 2. Install
pip install -r requirements.txt

# 3. Configure — copy .env.example and fill in your keys
cp .env.example .env

# 4. Run
python start_server.py
# → http://localhost:8000
```

## 🐳 Docker

```bash
docker build -t aether-sovereign .
docker run -p 8000:8000 --env-file .env aether-sovereign
```

## ☁️ Deploy to Render (Free Tier — 24/7)

1. Fork this repo
2. Connect your fork to [render.com](https://render.com) → **New Web Service**
3. Render auto-detects `render.yaml` — click **Deploy**
4. Add secret environment variables in the Render dashboard (see `.env.example`)
5. Your public URL: `https://aether-sovereign-assistant.onrender.com`

## ⚙️ Environment Variables

| Variable | Required | Description |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | ✅ | From @BotFather |
| `TELEGRAM_CHAT_ID` | ✅ | Your Telegram user ID |
| `GROQ_API_KEY` | ✅ | groq.com |
| `GEMINI_API_KEY` | Recommended | Google AI Studio |
| `RAZORPAY_KEY_ID` | Payments | Razorpay dashboard |
| `RAZORPAY_KEY_SECRET` | Payments | Razorpay dashboard |
| `RAZORPAY_WEBHOOK_SECRET` | Payments | Webhook HMAC secret |
| `OWNER_EMAIL` | Email | Your Gmail address |
| `GMAIL_APP_PASSWORD` | Email | Gmail App Password (not regular password) |
| `CALENDAR_ICS_URL` | Optional | .ics calendar URL |

## 🔄 Continuous Improvement Engine

AETHER autonomously improves itself every 4 hours:

```
✅ unused_imports      — pyflakes / AST unused import scan
✅ type_hints          — missing return/param annotations
✅ docstrings          — public API documentation gaps
✅ test_coverage       — untested public functions
✅ fast_cortex_perf    — route latency micro-benchmark
✅ security            — pip-audit dependency vulnerability scan
✅ import_order        — isort auto-fix
✅ complexity          — radon cyclomatic complexity scorer
✅ memory_cache        — RSS, CPU, cache-hit ratio monitor
```

Improvement reports saved to `data/improvement_log.jsonl` and `data/latest_improvement_report.json`.  
Telegram push notification sent after each cycle.

Run manually:
```bash
PYTHONPATH=src python -m aether.brain.continuous_improvement_engine
```

## 🧪 Tests

```bash
PYTHONPATH=src python -m pytest tests/ -v
```

All 64+ tests pass. CI runs on every push via GitHub Actions.

## 🏗️ Architecture

```
src/aether/
├── brain/
│   ├── engine.py                    # CognitiveEngine — 353 tools
│   ├── fast_cortex.py               # Sub-5ms route classifier + semantic cache
│   ├── multi_provider_router.py     # Groq → Gemini → OpenRouter → local
│   └── continuous_improvement_engine.py  # 🔄 Self-improvement loop
├── daemon/
│   └── autonomous_operator.py       # 15 APScheduler background jobs
├── channels/
│   ├── telegram_assistant.py        # 24/7 Telegram bot
│   └── whatsapp_assistant.py
├── growth/
│   └── crm_pipeline.py              # CRM deal engine
├── tools/
│   ├── cloud_email_agent.py         # Gmail IMAP/SMTP
│   └── cloud_calendar_agent.py
└── web/
    ├── server.py                    # FastAPI app
    ├── webhooks.py                  # Razorpay HMAC webhook
    ├── crm_router.py
    └── static/                      # Glassmorphic OLED UI
```

## 📄 License

MIT © 2026 AETHER Sovereign OS
