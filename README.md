# AETHER — Sovereign Executive OS

<p align="center">
  <img src="src/aether/web/static/aether_logo.png" alt="AETHER" width="120" onerror="this.style.display='none'"/>
</p>

<p align="center">
  <a href="https://github.com/TechByteco/aether-agent/actions"><img src="https://github.com/TechByteco/aether-agent/actions/workflows/ci.yml/badge.svg" alt="CI"/></a>
  <a href="https://aether-sovereign-os.vercel.app"><img src="https://img.shields.io/badge/Vercel-Live%20Production-000000?style=flat&logo=vercel" alt="Vercel Production"/></a>
  <img src="https://img.shields.io/badge/python-3.11%20|%203.12-blue" alt="Python"/>
  <img src="https://img.shields.io/badge/platform-Vercel%20%7C%20Render%20%7C%20Docker-green" alt="Platform"/>
  <img src="https://img.shields.io/badge/license-MIT-lightgrey" alt="License"/>
</p>

> **AETHER** is an autonomous, self-evolving AI executive operating system engineered for 24/7 sovereign decision-making. Orchestrates multi-agent swarms with sub-5ms Fast Cortex routing, automated business pipelines (CRM, email, payments), continuous codebase self-improvement, Obscura engine runtime, and a modern agency-grade web HUD.

---

## 📌 Repository Overview

* **GitHub "About" Description:**  
  `Autonomous, self-evolving AI executive assistant and agent swarm OS. Features sub-5ms Fast Cortex routing, multi-agent debates, autonomous CRM/payment automation, Obscura engine integration, and a modern Linear-grade web HUD.`
* **Topics & Tags:**  
  `autonomous-agent` · `multi-agent-system` · `agent-swarm` · `executive-assistant` · `self-improving-ai` · `fast-cortex` · `obscura-engine` · `edge-ai` · `groq` · `gemini`
* **Live Production URL:** [https://aether-sovereign-os.vercel.app](https://aether-sovereign-os.vercel.app)
* **Telegram Bot Companion:** [@MyAetherAssistantBot](https://t.me/MyAetherAssistantBot)

---

## ✨ Core Capabilities

| Category | Capabilities |
|---|---|
| 🐝 **Multi-Agent Swarm** | Autonomous specialist swarms (System Architect, Autonomous Coder, Security Reviewer, Consensus Debate) collaborating on edge workers with structured consensus generation. |
| ⚡ **Fast Cortex Engine** | Deterministic sub-5ms routing for system vitals, semantic RAM pre-warmed cache (<0.5ms), and speculative cloud races across Groq (800+ tok/s), Gemini, and local models. |
| 🔮 **Obscura Agent Engine** | Sandboxed recursive tool execution, runtime module hot-reloading, cognitive self-reflection, and safe AST-validated dynamic agent synthesis. |
| 💼 **Enterprise CRM & Deals** | Inbound deal qualification, pipeline stages, automated proposal generation, and client meeting scheduling. |
| 💳 **Razorpay & Payments** | Automated payment capture, cryptographic HMAC-SHA256 webhook verification, and digital receipt dispatch. |
| 📧 **Autonomous Email Hub** | 24/7 Gmail IMAP/SMTP triage, multi-intent classification, summary briefing cards, and draft generation. |
| 🔄 **Self-Improvement Loop** | Autonomous engine running every 4h — scans AST unused imports, type annotations, docstring coverage, `pip-audit` security, and `radon` complexity. |
| 🎨 **Modern Web HUD** | High-contrast Linear/Vercel-inspired light theme, structured markdown renderer (Executive Summary, Architecture, Code, Invariants, Next Steps), and hands-free voice companion. |
| 📱 **Omnichannel & Mobile** | Telegram bot, WhatsApp assistant, and Samsung One UI 8 deep links (1-tap Clock Alarms, Calendar events, Modes & Routines webhooks). |

---

## 🏗️ Architecture

```
aether-agent/
├── cloud_web/                          # 🌐 100% Serverless Cloud OS (Vercel Production)
│   ├── index.html                      # Modern Light Theme Web HUD
│   ├── style.css                       # Design System (Linear/Vercel tokens)
│   ├── app.js                          # Client State, Markdown Parser & Voice
│   ├── vercel.json                     # Edge routing & serverless configuration
│   └── api/                            # Serverless Cloud Edge Functions
│       ├── chat.js                     # 5-Part Executive Framework Chat API
│       ├── agency.js                   # Multi-Agent Swarm & Debate Engine
│       ├── code.js                     # Code execution & file inspection
│       ├── crm.js                      # Pipeline deals & revenue tracking
│       ├── email.js                    # Cloud email triage & dispatch
│       ├── evolution.js                # Autonomous self-evolution status
│       ├── huggingface.js              # Hugging Face live model explorer
│       └── leon.js                     # Autonomous operator orchestrator
├── obscura_enchanted_agent_engine/    # 🔮 Obscura Autonomous Execution Runtime
├── src/aether/                         # 🧠 Core Python Sovereign Engine
│   ├── brain/
│   │   ├── engine.py                   # CognitiveEngine — 350+ tools
│   │   ├── fast_cortex.py              # Sub-5ms classifier & semantic cache
│   │   ├── multi_provider_router.py    # Groq → Gemini → OpenRouter → Local
│   │   └── continuous_improvement_engine.py # 🔄 Autonomous self-evolution
│   ├── daemon/
│   │   └── autonomous_operator.py      # APScheduler 15 background jobs
│   ├── channels/
│   │   ├── telegram_assistant.py       # 24/7 Telegram companion
│   │   └── whatsapp_assistant.py       # WhatsApp webhook gateway
│   ├── growth/
│   │   └── crm_pipeline.py             # Enterprise CRM engine
│   └── web/
│       ├── server.py                   # FastAPI local server
│       └── webhooks.py                 # Razorpay HMAC verified webhooks
└── tests/                              # 🧪 Comprehensive Test Suite (64+ tests)
```

---

## 🚀 Quick Start

### 1. Cloud Web Experience (Instant)
Access the live production system immediately in any browser with zero setup:
👉 **[https://aether-sovereign-os.vercel.app](https://aether-sovereign-os.vercel.app)**

### 2. Local Python Environment

```bash
# 1. Clone repository
git clone https://github.com/TechByteco/aether-agent.git
cd aether-agent

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
# Fill in your GROQ_API_KEY, GEMINI_API_KEY, TELEGRAM_BOT_TOKEN, etc.

# 4. Start local executive server
python start_server.py
# → Visit http://localhost:8000
```

### 3. Docker Deployment

```bash
docker build -t aether-sovereign .
docker run -p 8000:8000 --env-file .env aether-sovereign
```

### 4. Deploy to Render (24/7 Free Web Service)
1. Fork this repository to your GitHub account.
2. Connect to [Render.com](https://render.com) → **New Web Service**.
3. Render detects `render.yaml` automatically — click **Deploy**.
4. Configure environment variables in the Render dashboard.

---

## 🔄 Continuous Self-Improvement Engine

AETHER inspects and refines its own codebase autonomously on a 4-hour cycle:

```
✅ unused_imports      — pyflakes / AST dead import elimination
✅ type_hints          — typing coverage & return annotation audit
✅ docstrings          — public API specification verification
✅ test_coverage       — automated test suite gap analysis
✅ fast_cortex_perf    — routing latency micro-benchmarking
✅ security            — pip-audit dependency CVE vulnerability scanner
✅ import_order        — PEP 8 isort ordering
✅ complexity          — radon cyclomatic complexity indexer
✅ memory_cache        — RSS memory, CPU usage, semantic cache hit-rate
```

Cycle audit logs are saved to `data/improvement_log.jsonl` and pushed via instant Telegram notification to the system owner.

To run an ad-hoc cycle:
```bash
PYTHONPATH=src python -m aether.brain.continuous_improvement_engine
```

---

## 🧪 Testing & Quality Assurance

```bash
PYTHONPATH=src python -m pytest tests/ -v
```

All 64+ automated behavioral tests pass. Continuous Integration (CI) executes on every push via GitHub Actions.

---

## 📄 License

Distributed under the **MIT License**. See `LICENSE` for details.

© 2026 **AETHER Sovereign OS** · Built by [TechByteco](https://github.com/TechByteco).
